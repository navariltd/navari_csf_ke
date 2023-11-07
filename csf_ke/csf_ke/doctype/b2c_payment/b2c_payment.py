# Copyright (c) 2023, Navari Limited and contributors
# For license information, please see license.txt

import ast
import base64
import datetime
import json

import frappe
import requests
from frappe.model.document import Document
from frappe.utils.file_manager import get_file_path
from frappe.utils.password import get_decrypted_password

from csf_ke.csf_ke.doctype.b2c_payment.encoding_credentials import (
    openssl_encrypt_encode,
)


class B2CPayment(Document):
    """MPesa B2C Payment Class"""


@frappe.whitelist(methods="POST")
def initiate_payment(partial_payload: str) -> dict[str, str] | None:
    """Endpoint that initiates the payment process"""
    partial_payload = json.loads(frappe.form_dict.partial_payload)
    b2c_settings = frappe.db.get_singles_dict("MPesa B2C Settings")
    payment_document = frappe.db.get_value(
        "B2C Payment",
        {"name": partial_payload.get("name")},
        ["name", "status"],
        as_dict=True,
    )
    now = datetime.datetime.now()
    hashed_token = frappe.db.sql(
        f"""
            SELECT name, access_token
            FROM `tabDaraja Access Tokens`
            WHERE expiry_time > '{now.strftime("%Y-%m-%d %H:%M:%S")}'
            ORDER BY creation DESC
            LIMIT 1
        """,
        as_dict=True,
    )

    if not hashed_token:
        if b2c_settings:
            consumer_key = b2c_settings.get("consumer_key")
            authorization_url = b2c_settings.get("authorization_url")
            consumer_secret = get_decrypted_password(
                "MPesa B2C Settings", "MPesa B2C Settings", "consumer_secret"
            )

            response, status_code = get_access_tokens(
                consumer_key, consumer_secret, authorization_url
            )

            if status_code == requests.codes.ok:
                # If response code is 200, proceed
                bearer_token = save_access_token_to_database(response)
                make_payment(
                    bearer_token, b2c_settings, partial_payload, payment_document
                )

    else:
        bearer_token = get_decrypted_password(
            "Daraja Access Tokens", hashed_token[0].name, "access_token"
        )

        make_payment(bearer_token, b2c_settings, partial_payload, payment_document)


@frappe.whitelist(allow_guest=True)
def results_callback_url(Result: dict):
    """
    Handles results response from Safaricom after successful B2C Payment request.
    For a complete description of the response parameters: https://developer.safaricom.co.ke/APIs/BusinessToCustomer
    """
    results = ast.literal_eval(json.dumps(Result))
    originator_conversation_id = results.get("OriginatorConversationID")
    b2c_payment_document = frappe.db.get_value(
        "B2C Payment",
        {"originatorconversationid": originator_conversation_id},
        as_dict=True,
    )
    result_type = int(results.get("ResultType"))
    result_code = int(results.get("ResultCode"))
    results_description = results.get("ResultDesc")
    transaction_id = results.get("TransactionID")

    if result_type == 0:
        if result_code == 0:
            # Success result code. Mark the b2c payment record as paid in the database
            result_parameters = results.get("ResultParameters").get("ResultParameter")
            transaction_values = {}

            for item in result_parameters:
                if item["Key"] == "TransactionAmount":
                    transaction_values["transaction_amount"] = item["Value"]

                elif (
                    item["Key"] == "TransactionReceipt"
                    and item["Value"] == transaction_id
                ):
                    transaction_values["transaction_id"] = item["Value"]

                elif item["Key"] == "B2CRecipientIsRegisteredCustomer":
                    transaction_values["recipient_is_registered_customer"] = item[
                        "Value"
                    ]

                elif item["Key"] == "B2CChargesPaidAccountAvailableFunds":
                    transaction_values["charges_paid_acct_avlbl_funds"] = item["Value"]

                elif item["Key"] == "ReceiverPartyPublicName":
                    transaction_values["receiver_public_name"] = item["Value"]

                elif item["Key"] == "TransactionCompletedDateTime":
                    transaction_datetime = datetime.datetime.strptime(
                        item["Value"], "%d.%m.%Y %H:%M:%S"
                    ).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    transaction_values[
                        "transaction_completed_datetime"
                    ] = transaction_datetime

                elif item["Key"] == "B2CUtilityAccountAvailableFunds":
                    transaction_values["utility_acct_avlbl_funds"] = item["Value"]

                elif item["Key"] == "B2CWorkingAccountAvailableFunds":
                    transaction_values["working_acct_avlbl_funds"] = item["Value"]

            # Add originator conversation id that will act as a link to the originator B2C Payment record
            transaction_values.update(
                {"originatorcoversationid": originator_conversation_id}
            )
            # Update doctype values
            update_doctype_single_values(
                "B2C Payment", b2c_payment_document, "status", "Paid"
            )
            transaction = save_transaction_to_database(
                "B2C Payments Transactions", transaction_values
            )

            return transaction

        else:
            # Unsuccessful result code. Update the b2c payment record
            print(f"Transaction {transaction_id} Errored with: {results_description}")

            # Update error related fields in B2C Payment doctype record
            update_doctype_single_values(
                "B2C Payment", b2c_payment_document, "status", "Errored"
            )
            update_doctype_single_values(
                "B2C Payment", b2c_payment_document, "error_code", result_code
            )
            update_doctype_single_values(
                "B2C Payment",
                b2c_payment_document,
                "error_description",
                results_description,
            )

    else:
        print(f"Duplicate Request Encountered for {b2c_payment_document.name}")


@frappe.whitelist(allow_guest=True)
def queue_timeout_url(response):
    """Handles timeout responses from Safaricom"""
    frappe.msgprint(f"{response}")


def get_access_tokens(
    consumer_key: str, consumer_secret: str, url: str
) -> tuple[str, int]:
    """
    Get the access token from the authorization url.
    This is the first function called when initiating the B2C payment process
    """
    keys = f"{consumer_key}:{consumer_secret}"
    encoded_credentials = base64.b64encode(keys.encode("utf-8")).decode("utf-8")

    response = requests.get(
        url,
        headers={
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json",
        },
        timeout=60,
    )

    response.raise_for_status()  # Raise HTTPError if status code >= 400

    return response.text, response.status_code


def save_access_token_to_database(response: str) -> str:
    """
    Deserialises the response object and saves the access token to the database,
    returning the access token
    """
    token_fetch_time = datetime.datetime.now()
    response = json.loads(response)

    expiry_time = datetime.datetime.now() + datetime.timedelta(
        seconds=int(response.get("expires_in"))
    )

    new_token = frappe.new_doc("Daraja Access Tokens")
    new_token.access_token = response.get("access_token")
    new_token.expiry_time = expiry_time
    new_token.token_fetch_time = token_fetch_time
    new_token.save()

    return response.get("access_token")


def get_certificate_file() -> str:
    """Get the uploaded certificate's file path from the server"""
    certificate_path = frappe.get_value("File", {"file_type": "CER"}, ["file_url"])

    if certificate_path:
        certificate: str = get_file_path(certificate_path)

        return certificate

    return "No certificate File found in the server"


def generate_payload(
    b2c_settings: Document,
    partial_payload: dict[str, str | int],
    security_credentials: str,
) -> str:
    """Generates an MPesa B2C API conforming payload to send in order to initiate payment"""
    partial_payload_from_settings = {
        "PartyA": b2c_settings.organisation_shortcode,
        "InitiatorName": b2c_settings.initiator_name,
        "SecurityCredential": security_credentials,
        "QueueTimeOutURL": b2c_settings.queue_timeout_url,
        "ResultURL": b2c_settings.results_url,
    }

    partial_payload.update(partial_payload_from_settings)

    return json.dumps(partial_payload)


def send_payload(payload: str, access_token: str, url) -> tuple[str, int]:
    """Sends request to payment processing url with payload"""
    response = requests.post(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        timeout=60,
    )

    response.raise_for_status()  # Raise HTTPError if status code >= 400

    frappe.msgprint("Success", "Success", indicator="green")

    return response.text, response.status_code


def make_payment(
    bearer_token: str,
    b2c_settings: Document,
    partial_payload: dict[str, str | int],
    payment_document: Document,
) -> tuple[str, int]:
    """Handle Making the payment"""
    initiator_password = get_decrypted_password(
        "MPesa B2C Settings", "MPesa B2C Settings", "initiator_password"
    )
    payment_url = b2c_settings.get("payment_url")

    certificate = get_certificate_file()

    if certificate:
        security_credentials = openssl_encrypt_encode(
            initiator_password.encode(), certificate
        )[8:].decode()

        payload = generate_payload(b2c_settings, partial_payload, security_credentials)

        response, status_code = send_payload(payload, bearer_token, payment_url)

        update_doctype_single_values(
            "B2C Payment", payment_document, "status", "Pending"
        )

        return response, status_code

    frappe.msgprint(
        "No valid certificate file found. Did you get the certificate from Safaricom?"
    )


def update_doctype_single_values(
    doctype: str, document_to_update: Document, field: str, new_value: str
) -> None:
    """
    Updates the specified doctype's field with the specified values.
    Note: Only one field is updated at a time
    """
    frappe.db.set_value(
        doctype, document_to_update.name, field, new_value, update_modified=True
    )


def save_transaction_to_database(
    doctype: str,
    update_values: dict[str, str | int | float],
) -> Document:
    """
    Saves Transaction details to database after successful B2C Payment
    """
    update_values.update({"doctype": doctype})

    transaction = frappe.get_doc(update_values)
    transaction.insert(ignore_permissions=True)

    return transaction
