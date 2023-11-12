# Copyright (c) 2023, Navari Limited and Contributors
# See license.txt

import datetime
import random
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase

from ..csf_ke_custom_exceptions import InformationMismatchError

ORIGINATOR_CONVERSATION_ID = str(uuid4())
ORIGINATOR_CONVERSATION_ID_2 = str(uuid4())


def create_b2c_payment_transaction() -> None:
    """Create a valid b2c payment"""
    if frappe.flags.test_events_created:
        return

    frappe.set_user("Administrator")

    doc = frappe.get_doc(
        {
            "doctype": "B2C Payment",
            "originatorconversationid": ORIGINATOR_CONVERSATION_ID,
            "commandid": "SalaryPayment",
            "remarks": "test remarks",
            "status": "Paid",
            "partyb": "254712345678",
            "amount": 10,
            "occassion": "Testing",
        }
    ).insert()

    frappe.get_doc(
        {
            "doctype": "B2C Payment",
            "originatorconversationid": ORIGINATOR_CONVERSATION_ID_2,
            "commandid": "SalaryPayment",
            "remarks": "test remarks",
            "status": random.choice(["Pending", "Not Initiated", "Timed-Out"]),
            "partyb": "254712345678",
            "amount": 10,
            "occassion": "Testing",
        }
    ).insert()

    frappe.get_doc(
        {
            "doctype": "B2C Payments Transactions",
            "b2c_payment_name": doc.name,
            "transaction_id": 951753654,
            "transaction_amount": 10,
            "receiver_public_name": "Jane Doe",
            "recipient_is_registered_customer": "Y",
            "charges_paid_acct_avlbl_funds": 100,
            "working_acct_avlbl_funds": 1000000,
            "utility_acct_avlbl_funds": 10000000,
            "transaction_completed_datetime": datetime.datetime.now(),
        }
    ).insert()

    frappe.flags.test_events_created = True


class TestB2CPaymentsTransactions(FrappeTestCase):
    """B2C Payments Transactions Tests"""

    def setUp(self) -> None:
        create_b2c_payment_transaction()

    def tearDown(self) -> None:
        frappe.set_user("Administrator")

    def test_mismatch_in_amount(self) -> None:
        """Tests a mismatch in the amount paid and the transaction amount"""
        payment = frappe.db.get_value(
            "B2C Payment",
            {"originatorconversationid": ORIGINATOR_CONVERSATION_ID},
            ["name"],
            as_dict=True,
        )
        with self.assertRaises(InformationMismatchError):
            frappe.get_doc(
                {
                    "doctype": "B2C Payments Transactions",
                    "b2c_payment_name": payment.name,
                    "transaction_id": random.randint(1000000, 100000000),
                    "transaction_amount": 9.9999,
                    "receiver_public_name": "Jane Doe",
                    "recipient_is_registered_customer": "Y",
                    "charges_paid_acct_avlbl_funds": 100,
                    "working_acct_avlbl_funds": 1000000,
                    "utility_acct_avlbl_funds": 10000000,
                    "transaction_completed_datetime": datetime.datetime.now(),
                }
            ).insert()

    def test_mismatch_in_payment_status(self) -> None:
        """Tests creating a transaction when payment status is not 'Paid'"""
        payment = frappe.db.get_value(
            "B2C Payment",
            {"originatorconversationid": ORIGINATOR_CONVERSATION_ID_2},
            ["name"],
            as_dict=True,
        )
        with self.assertRaises(InformationMismatchError):
            frappe.get_doc(
                {
                    "doctype": "B2C Payments Transactions",
                    "b2c_payment_name": payment.name,
                    "transaction_id": random.randint(1000000, 100000000),
                    "transaction_amount": 9.9999,
                    "receiver_public_name": "Jane Doe",
                    "recipient_is_registered_customer": "Y",
                    "charges_paid_acct_avlbl_funds": 100,
                    "working_acct_avlbl_funds": 1000000,
                    "utility_acct_avlbl_funds": 10000000,
                    "transaction_completed_datetime": datetime.datetime.now(),
                }
            ).insert()

    def test_creating_transaction_for_non_existent_payment(self) -> None:
        """Tests creating transaction for non-existent payment record"""
        with self.assertRaises(frappe.exceptions.LinkValidationError):
            frappe.get_doc(
                {
                    "doctype": "B2C Payments Transactions",
                    "b2c_payment_name": "MPESA-B2C-0000",
                    "transaction_id": random.randint(1000000, 100000000),
                    "transaction_amount": 9.9999,
                    "receiver_public_name": "Jane Doe",
                    "recipient_is_registered_customer": "Y",
                    "charges_paid_acct_avlbl_funds": 100,
                    "working_acct_avlbl_funds": 1000000,
                    "utility_acct_avlbl_funds": 10000000,
                    "transaction_completed_datetime": datetime.datetime.now(),
                }
            ).insert()
