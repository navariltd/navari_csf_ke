# Copyright (c) 2023, Navari Limited and contributors
# For license information, please see license.txt

import base64
import datetime
import json

import frappe
import requests
from frappe.model.document import Document
from frappe.utils.password import get_decrypted_password

AUTHORISATION_URL = (
    "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
)


class B2CPayment(Document):
    """MPesa B2C Payment Class"""


@frappe.whitelist(methods="POST")
def initiate_payment() -> dict[str, str] | None:
    """Endpoint that initiates the payment process"""
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
        b2c_settings = frappe.db.get_singles_dict("MPesa B2C Settings")

        if b2c_settings:
            consumer_key = b2c_settings.get("consumer_key")
            consumer_secret = get_decrypted_password(
                "MPesa B2C Settings", "MPesa B2C Settings", "consumer_secret"
            )

            response, status_code = get_access_tokens(consumer_key, consumer_secret)

            if status_code == 200:
                if save_access_token_to_database(response):
                    return {"message": "Created"}

            if status_code == 400:
                frappe.msgprint("Bad Request Encountered")

            elif status_code == 403:
                frappe.msgprint("Not authorised to access this resource")

            elif status_code >= 500:
                frappe.msgprint("Internal Server Error from Safaricom")

            else:
                pass

    else:
        bearer_token = get_decrypted_password(
            "Daraja Access Tokens", hashed_token[0].name, "access_token"
        )


def get_access_tokens(
    consumer_key: str, consumer_secret: str, url: str = AUTHORISATION_URL
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

    return response.text, response.status_code


def save_access_token_to_database(response: str) -> bool:
    """Deserialises the response object and saves the access token to the database"""
    response = json.loads(response)

    expiry_time = datetime.datetime.now() + datetime.timedelta(
        seconds=int(response.get("expires_in"))
    )

    new_token = frappe.new_doc("Daraja Access Tokens")
    new_token.access_token = response.get("access_token")
    new_token.expiry_time = expiry_time
    new_token.save()

    return True
