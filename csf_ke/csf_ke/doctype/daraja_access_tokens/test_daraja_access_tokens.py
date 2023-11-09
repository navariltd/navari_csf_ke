# Copyright (c) 2023, Navari Limited and Contributors
# See license.txt

import datetime

import frappe
from frappe.utils.password import get_decrypted_password
from frappe.tests.utils import FrappeTestCase
from .daraja_access_tokens_exceptions import InvalidTokenExpiryTime


TOKEN_ACCESS_TIME = datetime.datetime.now()


def create_access_token() -> None:
    """Creates a valid access token record for testing"""
    expiry_time = TOKEN_ACCESS_TIME + datetime.timedelta(hours=1)

    frappe.get_doc(
        {
            "doctype": "Daraja Access Tokens",
            "access_token": "123456789",
            "token_fetch_time": TOKEN_ACCESS_TIME,
            "expiry_time": expiry_time,
        }
    ).insert()


class TestDarajaAccessTokens(FrappeTestCase):
    """Testing the Daraja Access Tokens doctype"""

    def setUp(self) -> None:
        create_access_token()

    def tearDown(self) -> None:
        frappe.set_user("Administrator")

    def test_valid_access_token(self) -> None:
        """Attempt to access an existing token"""
        token = frappe.db.get_value(
            "Daraja Access Tokens",
            {"token_fetch_time": TOKEN_ACCESS_TIME},
            ["name", "token_fetch_time", "expiry_time"],
            as_dict=True,
        )
        access_token = get_decrypted_password(
            "Daraja Access Tokens", token.name, "access_token"
        )

        self.assertEqual(access_token, "123456789")
        self.assertEqual(token.token_fetch_time, TOKEN_ACCESS_TIME)
        self.assertEqual(
            token.expiry_time, TOKEN_ACCESS_TIME + datetime.timedelta(hours=1)
        )

    def test_create_incomplete_access_token(self) -> None:
        """Attemp to create a record from incomplete data"""
        with self.assertRaises(frappe.exceptions.MandatoryError):
            frappe.get_doc(
                {
                    "doctype": "Daraja Access Tokens",
                    "access_token": "123456789",
                    "token_fetch_time": TOKEN_ACCESS_TIME,
                }
            ).insert()

    def test_incorrect_datetime_type(self) -> None:
        """Test passing strings to datetime fields"""
        with self.assertRaises(TypeError):
            frappe.get_doc(
                {
                    "doctype": "Daraja Access Tokens",
                    "access_token": TOKEN_ACCESS_TIME + datetime.timedelta(hours=1),
                    "token_fetch_time": TOKEN_ACCESS_TIME,
                    "expiry_time": "123456789",
                }
            ).insert()

    def test_expiry_time_earlier_than_fetch_time(self) -> None:
        """Test expiry time being early than fetch time"""
        with self.assertRaises(InvalidTokenExpiryTime):
            frappe.get_doc(
                {
                    "doctype": "Daraja Access Tokens",
                    "access_token": "123456789",
                    "token_fetch_time": TOKEN_ACCESS_TIME,
                    "expiry_time": TOKEN_ACCESS_TIME - datetime.timedelta(hours=1),
                }
            ).insert()
