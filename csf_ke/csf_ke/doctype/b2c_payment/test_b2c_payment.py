# Copyright (c) 2023, Navari Limited and Contributors
# See license.txt

import frappe
import pymysql
from frappe.tests.utils import FrappeTestCase

from ..csf_ke_exceptions import (
    InsufficientPaymentAmountError,
    InvalidReceiverMobileNumberError,
)

from ..csf_ke_exceptions import (
    IncorrectStatusError,
)


def create_b2c_payment() -> None:
    """Create a valid b2c payment"""
    if frappe.flags.test_events_created:
        return

    frappe.set_user("Administrator")

    frappe.get_doc(
        {
            "doctype": "B2C Payment",
            "commandid": "SalaryPayment",
            "remarks": "test remarks",
            "status": "Not Initiated",
            "partyb": "254708993268",
            "amount": 10,
            "occassion": "Testing",
        }
    ).insert()

    frappe.flags.test_events_created = True


class TestB2CPayment(FrappeTestCase):
    """B2C Payment Tests"""

    def setUp(self) -> None:
        create_b2c_payment()

    def tearDown(self) -> None:
        frappe.set_user("Administrator")

    def test_invalid_receiver_number(self) -> None:
        """Tests invalid receivers"""
        with self.assertRaises(InvalidReceiverMobileNumberError):
            frappe.get_doc(
                {
                    "doctype": "B2C Payment",
                    "commandid": "SalaryPayment",
                    "remarks": "test remarks",
                    "status": "Not Initiated",
                    "partyb": "2547089932680",
                    "amount": 10,
                    "occassion": "Testing",
                }
            ).insert()

            frappe.get_doc(
                {
                    "doctype": "B2C Payment",
                    "commandid": "SalaryPayment",
                    "remarks": "test remarks",
                    "status": "Not Initiated",
                    "partyb": "25470899326",
                    "amount": 10,
                    "occassion": "Testing",
                }
            ).insert()

            frappe.get_doc(
                {
                    "doctype": "B2C Payment",
                    "commandid": "SalaryPayment",
                    "remarks": "test remarks",
                    "status": "Not Initiated",
                    "partyb": 254103456789,
                    "amount": 10,
                    "occassion": "Testing",
                }
            ).insert()

            frappe.get_doc(
                {
                    "doctype": "B2C Payment",
                    "commandid": "SalaryPayment",
                    "remarks": "test remarks",
                    "status": "Not Initiated",
                    "partyb": 254113456789,
                    "amount": 10,
                    "occassion": "Testing",
                }
            ).insert()

    def test_empty_mandatory_fields(self) -> None:
        """Tests when a mandatory field is not field"""
        with self.assertRaises(frappe.exceptions.MandatoryError):
            frappe.get_doc(
                {
                    "doctype": "B2C Payment",
                    "commandid": "SalaryPayment",
                    "status": "Not Initiated",
                    "partyb": "254708993268",
                    "amount": 10,
                    "occassion": "Testing",
                }
            ).insert()

            frappe.get_doc(
                {
                    "doctype": "B2C Payment",
                    "remarks": "testing remarks",
                    "status": "Not Initiated",
                    "partyb": "254708993268",
                    "amount": 10,
                    "occassion": "Testing",
                }
            ).insert()

    def test_insufficient_amount(self) -> None:
        """Tests when an insufficient payment amount has been supplied"""
        with self.assertRaises(InsufficientPaymentAmountError):
            frappe.get_doc(
                {
                    "doctype": "B2C Payment",
                    "commandid": "SalaryPayment",
                    "remarks": "test remarks",
                    "status": "Not Initiated",
                    "partyb": "254708993268",
                    "amount": 9.9999999,
                    "occassion": "Testing",
                }
            ).insert()

    def test_incredibly_large_amount(self) -> None:
        """Tests when an incredibly large number has been supplied"""
        large_number = 9999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999
        with self.assertRaises(pymysql.err.DataError):
            frappe.get_doc(
                {
                    "doctype": "B2C Payment",
                    "commandid": "SalaryPayment",
                    "remarks": "test remarks",
                    "status": "Not Initiated",
                    "partyb": "254708993268",
                    "amount": large_number,
                    "occassion": "Testing",
                }
            ).insert()

    def test_valid_originator_conversation_id_length(self) -> None:
        """Test that the created b2c settings have valid length uuids"""
        new_b2c_payment = frappe.get_doc(
            {
                "doctype": "B2C Payment",
                "commandid": "SalaryPayment",
                "remarks": "test remarks",
                "status": "Not Initiated",
                "partyb": "254708993268",
                "amount": 10,
                "occassion": "Testing",
            }
        ).insert()

        self.assertEqual(len(new_b2c_payment.originatorconversationid), 36)

    def test_invalid_errored_status_no_code_or_error_description(self) -> None:
        """Tests when status is set to errored without a description or error code"""
        with self.assertRaises(IncorrectStatusError):
            frappe.get_doc(
                {
                    "doctype": "B2C Payment",
                    "commandid": "SalaryPayment",
                    "remarks": "test remarks",
                    "status": "Errored",
                    "partyb": "254708993268",
                    "amount": 10,
                    "occassion": "Testing",
                }
            ).insert()

    def test_status_set_to_not_initiated_when_not_supplied(self) -> None:
        """
        Tests when status is not given on creation of a record.
        Should be set to 'Not Initiated'
        """
        new_doc = frappe.get_doc(
            {
                "doctype": "B2C Payment",
                "commandid": "SalaryPayment",
                "remarks": "test remarks",
                "partyb": "254708993268",
                "amount": 10,
                "occassion": "Testing",
            }
        ).insert()

        self.assertEqual(new_doc.status, "Not Initiated")
