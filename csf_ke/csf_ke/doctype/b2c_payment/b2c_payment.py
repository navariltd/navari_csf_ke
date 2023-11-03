# Copyright (c) 2023, Navari Limited and contributors
# For license information, please see license.txt

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
                make_payment(bearer_token, b2c_settings, partial_payload)

            if status_code == requests.codes.bad_request:
                # response code 400
                frappe.msgprint("Bad Request Encountered")

            elif status_code == requests.codes.forbidden:
                # response code 403
                frappe.msgprint("Not authorised to access this resource")

            elif status_code >= requests.codes.server_error:
                # response codes >= 500
                frappe.msgprint("Internal Server Error from Safaricom Encountered.")

            else:
                pass

    else:
        bearer_token = get_decrypted_password(
            "Daraja Access Tokens", hashed_token[0].name, "access_token"
        )

        make_payment(bearer_token, b2c_settings, partial_payload)


def get_access_tokens(
    consumer_key: str, consumer_secret: str, url: str
) -> tuple[str, int]:
    """
    Get the access token. This is the first function called when initiating the B2C payment process
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

    response.raise_for_status()

    return response.text, response.status_code


def save_access_token_to_database(response: str) -> str:
    """
    Deserialises the response object and saves the access token to the database, returning the access token
    """
    response = json.loads(response)

    expiry_time = datetime.datetime.now() + datetime.timedelta(
        seconds=int(response.get("expires_in"))
    )

    new_token = frappe.new_doc("Daraja Access Tokens")
    new_token.access_token = response.get("access_token")
    new_token.expiry_time = expiry_time
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

    response.raise_for_status()

    return response.text, response.status_code


def handle_status_codes(response: str, status_code: int) -> str:
    """Handle the various status codes"""
    if status_code == requests.codes.ok:
        frappe.msgprint(f"Response from Safaricom: {response}")
        return "Success"

    elif status_code == requests.codes.not_found:
        frappe.msgprint("Resource Not Found")
        return "Not Found"

    elif status_code == requests.codes.bad_request:
        frappe.msgprint("Bad Request Initiated")
        return "Bad Request"

    elif status_code == requests.codes.unauthorized:
        frappe.msgprint("You are not authorised to make the request")
        return "Unauthorized"

    elif status_code >= requests.codes.server_error:
        frappe.msgprint("Internal Server Error Encountered")
        return "Internal Server Error"

    else:
        return "Unknown Status Code"


def make_payment(
    bearer_token: str, b2c_settings: Document, partial_payload: dict[str, str | int]
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

        handle_status_codes(response, status_code)

        return response, status_code

    frappe.msgprint(
        "No valid certificate file found. Did you get the certificate from Safaricom?"
    )
