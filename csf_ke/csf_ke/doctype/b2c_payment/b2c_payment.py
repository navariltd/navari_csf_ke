# Copyright (c) 2023, Navari Limited and contributors
# For license information, please see license.txt

import ast
import base64
import datetime
import json

import frappe
import requests
from frappe.model.document import Document
from frappe.utils import logger
from frappe.utils.file_manager import get_file_path
from frappe.utils.password import get_decrypted_password
from typing import Literal

from csf_ke.csf_ke.doctype.b2c_payment.encoding_credentials import (
    openssl_encrypt_encode,
)

logger.set_log_level("DEBUG")
api_logger = frappe.logger("api", allow_site=True, file_count=50)


class B2CPayment(Document):
    """MPesa B2C Payment Class"""


@frappe.whitelist(methods="POST")
def initiate_payment(partial_payload: str) -> None:
    """
    Endpoint that initiates the payment process.
    This endpoint first checks if a valid (meaning un-expired) access token is available.
    If none is found, it fetches one from the authorization url provided in the MPesa B2C Settings and
    proceeds to initiate a payment request to the payment url also specified in the MPesa B2C Settings.
    If a valid token is found, a payment initialization request is placed immediately.
    """
    partial_payload = json.loads(frappe.form_dict.partial_payload)
    b2c_settings = frappe.db.get_singles_dict("MPesa B2C Settings")
    payment_document = frappe.db.get_value(
        "B2C Payment",
        {"name": partial_payload.get("name")},
        ["name", "status"],
        as_dict=True,
    )
    hashed_token = get_hashed_token()

    if not hashed_token:
        consumer_key, consumer_secret, authorization_url = get_b2c_settings(
            b2c_settings
        )
        response, status_code = get_access_tokens(
            consumer_key, consumer_secret, authorization_url
        )

        if status_code == requests.codes.ok:
            # If response code is 200, proceed
            bearer_token = save_access_token_to_database(response)
            make_payment(bearer_token, b2c_settings, partial_payload, payment_document)
    else:
        bearer_token = get_decrypted_password(
            "Daraja Access Tokens", hashed_token, "access_token"
        )

        make_payment(bearer_token, b2c_settings, partial_payload, payment_document)


@frappe.whitelist(allow_guest=True)
def results_callback_url(Result: dict) -> None:
    """
    Handles results response from Safaricom after successful B2C Payment request.
    For a complete description of the response parameters: https://developer.safaricom.co.ke/APIs/BusinessToCustomer
    """
    results = ast.literal_eval(json.dumps(Result))
    (
        originator_conversation_id,
        result_type,
        result_code,
        results_description,
        transaction_id,
    ) = get_result_details(results)

    if result_type == 0:
        if result_code == 0:
            handle_successful_result(
                results, originator_conversation_id, transaction_id
            )
        else:
            handle_unsuccessful_result(
                transaction_id,
                originator_conversation_id,
                result_code,
                results_description,
            )
    else:
        handle_duplicate_request(b2c_payment_document, originator_conversation_id)


@frappe.whitelist(allow_guest=True)
def queue_timeout_url(response):
    """Handles timeout responses from Safaricom"""
    frappe.msgprint(f"{response}")


def get_hashed_token() -> str | list:
    """
    Checks if a valid (read un-expired) token is present in the database,
    fetches and returns it. Otherwise, returns an empty list
    """
    current_time = datetime.datetime.now()
    hashed_token = frappe.db.sql(
        f"""
            SELECT name, access_token
            FROM `tabDaraja Access Tokens`
            WHERE expiry_time > '{current_time.strftime("%Y-%m-%d %H:%M:%S")}'
            ORDER BY creation DESC
            LIMIT 1
        """,
        as_dict=True,
    )

    if hashed_token:
        return hashed_token[0].name

    return hashed_token


def get_b2c_settings(b2c_settings: Document) -> tuple[str, str, str]:
    """Gets the consumer key, secret, and authorization url from the B2C Settings"""
    consumer_key = b2c_settings.get("consumer_key")
    authorization_url = b2c_settings.get("authorization_url")
    consumer_secret = get_decrypted_password(
        "MPesa B2C Settings", "MPesa B2C Settings", "consumer_secret"
    )
    return consumer_key, consumer_secret, authorization_url


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

    try:
        response.raise_for_status()  # Raise HTTPError if status code >= 400

    except requests.HTTPError:
        api_logger.exception("Exception Encountered")
        raise

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

    api_logger.info(
        "Access token fetched and saved successfully at %s expiring at %s",
        token_fetch_time,
        expiry_time,
    )
    return response.get("access_token")


def get_certificate_file() -> str | Literal[-1]:
    """Get the uploaded certificate's file path from/in the server"""
    certificate_path = frappe.get_value("File", {"file_type": "CER"}, ["file_url"])

    if certificate_path:
        certificate: str | None = get_file_path(certificate_path)

        return certificate

    api_logger.error(
        "No valid Authentication Certificate file (*.cer) found in the server."
    )
    return -1


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


def get_result_details(results: dict) -> tuple:
    """
    Takes the results callback's result object and returns the important parameters
    """
    originator_conversation_id = results.get("OriginatorConversationID")
    result_type = int(results.get("ResultType"))
    result_code = int(results.get("ResultCode"))
    results_description = results.get("ResultDesc")
    transaction_id = results.get("TransactionID")

    return (
        originator_conversation_id,
        result_type,
        result_code,
        results_description,
        transaction_id,
    )


def handle_successful_result(
    results: dict, originator_conversation_id: str, transaction_id: str
) -> None:
    """
    Handles the result callback's responses with a successful ResutlCode, i.e. ResultCode of 0
    """
    b2c_payment_document = frappe.db.get_value(
        "B2C Payment",
        {"originatorconversationid": originator_conversation_id},
        as_dict=True,
    )

    result_parameters = results.get("ResultParameters").get("ResultParameter")
    transaction_values = extract_transaction_values(
        result_parameters, transaction_id, originator_conversation_id
    )
    update_doctype_single_values("B2C Payment", b2c_payment_document, "status", "Paid")
    transaction = save_transaction_to_database(
        "B2C Payments Transactions", transaction_values
    )
    frappe.response["transaction"] = transaction
    return


def handle_unsuccessful_result(
    transaction_id: str,
    originator_conversation_id: str,
    result_code: int,
    results_description: str,
) -> None:
    """
    Handles the result callback's responses with an unsuccessful ResutlCode, i.e. ResultCode of 1
    """
    b2c_payment_document = frappe.db.get_value(
        "B2C Payment",
        {"originatorconversationid": originator_conversation_id},
        as_dict=True,
    )

    api_logger.info(
        "Transaction %s with originator conversation id %s Errored with code: %s, description: %s",
        transaction_id,
        originator_conversation_id,
        result_code,
        results_description,
    )
    update_doctype_single_values(
        "B2C Payment", b2c_payment_document, "status", "Errored"
    )
    update_doctype_single_values(
        "B2C Payment", b2c_payment_document, "error_code", result_code
    )
    update_doctype_single_values(
        "B2C Payment", b2c_payment_document, "error_description", results_description
    )


def handle_duplicate_request(
    b2c_payment_document: Document, originator_conversation_id: str
) -> None:
    """
    Logs instances where multiple requests from same B2C payment record are initiated.
    """
    api_logger.info(
        "Duplicate Request Encountered for: %s and originator conversation id: %s",
        b2c_payment_document.name,
        originator_conversation_id,
    )

    return


def extract_transaction_values(
    result_parameters: dict, transaction_id: str, originator_conversation_id: str
) -> dict[str, str | int]:
    """
    Parses the ResultsParameter of successful responses to the results callback endpoint
    """
    transaction_values = {}

    for item in result_parameters:
        if item["Key"] == "TransactionAmount":
            transaction_values["transaction_amount"] = item["Value"]

        elif item["Key"] == "TransactionReceipt" and item["Value"] == transaction_id:
            transaction_values["transaction_id"] = item["Value"]

        elif item["Key"] == "B2CRecipientIsRegisteredCustomer":
            transaction_values["recipient_is_registered_customer"] = item["Value"]

        elif item["Key"] == "B2CChargesPaidAccountAvailableFunds":
            transaction_values["charges_paid_acct_avlbl_funds"] = item["Value"]

        elif item["Key"] == "ReceiverPartyPublicName":
            transaction_values["receiver_public_name"] = item["Value"]

        elif item["Key"] == "TransactionCompletedDateTime":
            transaction_datetime = datetime.datetime.strptime(
                item["Value"], "%d.%m.%Y %H:%M:%S"
            ).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            transaction_values["transaction_completed_datetime"] = transaction_datetime

        elif item["Key"] == "B2CUtilityAccountAvailableFunds":
            transaction_values["utility_acct_avlbl_funds"] = item["Value"]

        elif item["Key"] == "B2CWorkingAccountAvailableFunds":
            transaction_values["working_acct_avlbl_funds"] = item["Value"]

    transaction_values.update({"originatorcoversationid": originator_conversation_id})
    return transaction_values


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

    try:
        response.raise_for_status()  # Raise HTTPError if status code >= 400

    except requests.HTTPError:
        api_logger.exception("Exception encountered")
        raise

    frappe.msgprint("Payment Request Successful", title="Successful", indicator="green")
    return response.text, response.status_code


def make_payment(
    bearer_token: str,
    b2c_settings: Document,
    partial_payload: dict[str, str | int],
    payment_document: Document,
) -> None:
    """Handle Making the payment"""
    initiator_password = get_decrypted_password(
        "MPesa B2C Settings", "MPesa B2C Settings", "initiator_password"
    )
    payment_url = b2c_settings.get("payment_url")

    certificate = get_certificate_file()

    if isinstance(certificate, str):
        security_credentials = openssl_encrypt_encode(
            initiator_password.encode(), certificate
        )[8:].decode()

        payload = generate_payload(b2c_settings, partial_payload, security_credentials)

        response, status_code = send_payload(payload, bearer_token, payment_url)

        update_doctype_single_values(
            "B2C Payment", payment_document, "status", "Pending"
        )

        api_logger.info(
            "Successful payment initiation for originator conversation id: %s with status code: %s",
            partial_payload["OriginatorConversationID"],
            status_code,
        )
        frappe.response["message"] = "successful"
        frappe.response["info"] = {"response": response, "status_code": status_code}

        # This return is important since without it, execution will continue
        # to below and overwrite the "message" key in the response causing
        # the front-end to enter an incorrect state
        return

    frappe.response["message"] = "No certificate file found in server"
    return


def update_doctype_single_values(
    doctype: str, document_to_update: Document, field: str, new_value: str
) -> None:
    """
    Updates the specified doctype's field with the specified values.
    Note: Only one field is updated at a time
    """
    api_logger.info(
        "%s's %s's %s updated to %s",
        doctype,
        document_to_update.name,
        field,
        new_value,
    )
    frappe.db.set_value(
        doctype, document_to_update.name, field, new_value, update_modified=True
    )

    return


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

    api_logger.info(
        "Transaction ID: %s, originator conversation id: %s, amount: %s, transaction time: %s saved.",
        update_values["transaction_id"],
        update_values["originatorcoversationid"],
        update_values["transaction_amount"],
        update_values["transaction_completed_datetime"],
    )

    return transaction
