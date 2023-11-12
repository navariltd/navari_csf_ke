# Copyright (c) 2023, Navari Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from .. import api_logger
from ..csf_ke_custom_exceptions import (
    InformationMismatchError,
    UnExistentB2CPaymentRecordError,
)


class B2CPaymentsTransactions(Document):
    """B2C Payments Transactions"""

    def validate(self) -> None:
        """B2C Payments Transactions validations"""

        if self.b2c_payment_name:
            b2c_payment = frappe.db.get_value(
                "B2C Payment",
                {"name": self.b2c_payment_name},
                ["name", "status", "amount"],
                as_dict=True,
            )

            if not b2c_payment:
                api_logger.error(
                    "The B2C payment record with originator conversation ID: %s does not exist",
                    self.b2c_payment_name,
                )
                raise UnExistentB2CPaymentRecordError(
                    f"The B2C payment record with originator conversation ID: {self.b2c_payment_name} does not exist",
                )

            if (
                b2c_payment.status == "Errored"
                or b2c_payment.status == "Not Initiated"
                or b2c_payment.status == "Timed-Out"
                or b2c_payment.status == "Pending"
            ):
                api_logger.error(
                    "Incorrect B2C Payment Status: %s for B2C Payment: %s",
                    b2c_payment.status,
                    self.b2c_payment_name,
                )
                raise InformationMismatchError(
                    f"Incorrect B2C Payment Status: {b2c_payment.status} for B2C Payment: {self.b2c_payment_name}"
                )

            if self.transaction_amount != b2c_payment.amount:
                api_logger.error(
                    "Incorrect Transaction and B2C Payment Amount for B2C payment: %s",
                    self.b2c_payment_name,
                )
                raise InformationMismatchError(
                    f"Incorrect Transaction and B2C Payment Amount for B2C payment: {self.b2c_payment_name}"
                )
