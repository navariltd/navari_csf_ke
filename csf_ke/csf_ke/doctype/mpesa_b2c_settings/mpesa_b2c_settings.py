# Copyright (c) 2023, Navari Limited and contributors
# For license information, please see license.txt

import re

from frappe.model.document import Document

from .. import api_logger
from .mpesa_b2c_settings_exceptions import InvalidURLError


class MPesaB2CSettings(Document):
    """MPesa B2C Settings Doctype"""

    def validate(self) -> None:
        """Validate upon creating a record of the B2C Settings"""
        if (
            self.results_url
            and self.queue_timeout_url
            and self.authorization_url
            and self.payment_url
        ):
            if not (
                validate_url(self.results_url)
                and validate_url(self.queue_timeout_url)
                and validate_url(self.authorization_url)
                and validate_url(self.payment_url)
            ):
                api_logger.error(
                    "The URLs Registered are not valid. Please review them"
                )
                raise InvalidURLError(
                    "The URLs Registered are not valid. Please review them"
                )


def validate_url(url: str) -> bool:
    """
    Validates the input parameter to a valid URL.
    """
    pattern = re.compile(
        r"^((https?|ftp|file):\/\/)?"
        + r"((([a-zA-Z\d]([a-zA-Z\d-]*[a-zA-Z\d])*)\.)+[a-zA-Z]{2,}|"
        + r"((\d{1,3}\.){3}\d{1,3}))"
        + r"(:\d+)?(\/[-a-zA-Z\d%_.~+]*)*"
        + r"(\?[;&a-z\d%_.~+=-]*)?"
        + r"(\#[-a-z\d_]*)?$",
        re.IGNORECASE,
    )
    return bool(pattern.match(url))
