# Copyright (c) 2023, Navari Limited and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from ..csf_ke_custom_exceptions import InvalidURLError

from ..csf_ke_custom_exceptions import (
    InvalidAuthenticationCertificateFileError,
)


def create_b2c_settings():
    """Setup context for tests"""
    if frappe.flags.test_events_created:
        return

    frappe.set_user("Administrator")

    # Create a valid singles record during setUp context
    frappe.get_doc(
        {
            "doctype": "MPesa B2C Settings",
            "consumer_key": "1234567890",
            "initiator_name": "tester",
            "results_url": "https://example.com/api/method/handler",
            "authorization_url": "https://example.com/api/method/handler",
            "organisation_shortcode": "951753",
            "consumer_secret": "secret",
            "initiator_password": "password",
            "queue_timeout_url": "https://example.com/api/method/handler",
            "payment_url": "https://example.com/api/method/handler",
        }
    ).insert(ignore_mandatory=True)

    frappe.flags.test_events_created = True


class TestMPesaB2CSettings(FrappeTestCase):
    """MPesa B2C Settings Tests"""

    def setUp(self) -> None:
        create_b2c_settings()

    def tearDown(self) -> None:
        frappe.set_user("Administrator")

    def test_invalid_urls_in_b2c_settings(self) -> None:
        """Tests for cases when an invalid url is supplied"""
        with self.assertRaises(InvalidURLError):
            frappe.get_doc(
                {
                    "doctype": "MPesa B2C Settings",
                    "consumer_key": "1234567890",
                    "initiator_name": "tester",
                    "results_url": "https://example.com/api/method/handler",
                    "authorization_url": "https://example.com/api/method/handler",
                    "organisation_shortcode": "951753",
                    "consumer_secret": "secret",
                    "initiator_password": "password",
                    "queue_timeout_url": "https://example.com/api/method/handler",
                    "payment_url": "jkl",
                }
            ).insert(ignore_mandatory=True)

    def test_override_b2c_settings(self) -> None:
        """Test instances where the B2C Settings have been overridden"""
        frappe.get_doc(
            {
                "doctype": "MPesa B2C Settings",
                "consumer_key": "987654321",
                "initiator_name": "tester2",
                "results_url": "https://example2.com/api/method/handler",
                "authorization_url": "https://example2.com/api/method/handler",
                "organisation_shortcode": "951753",
                "consumer_secret": "secret",
                "initiator_password": "password",
                "queue_timeout_url": "https://example2.com/api/method/handler",
                "payment_url": "https://example2.com/api/method/handler",
            }
        ).insert(ignore_mandatory=True)

        new_doc = frappe.db.get_singles_dict("MPesa B2C Settings")

        self.assertEqual(new_doc.initiator_name, "tester2")
        self.assertEqual(new_doc.payment_url, "https://example2.com/api/method/handler")
        self.assertEqual(new_doc.consumer_key, "987654321")

    def test_invalid_certificate_file(self) -> None:
        """Tests when a user uploads an invalid certificate file"""
        with self.assertRaises(InvalidAuthenticationCertificateFileError):
            frappe.get_doc(
                {
                    "doctype": "MPesa B2C Settings",
                    "consumer_key": "987654321",
                    "initiator_name": "tester2",
                    "results_url": "https://example2.com/api/method/handler",
                    "authorization_url": "https://example2.com/api/method/handler",
                    "organisation_shortcode": "951753",
                    "consumer_secret": "secret",
                    "initiator_password": "password",
                    "queue_timeout_url": "https://example2.com/api/method/handler",
                    "payment_url": "https://example2.com/api/method/handler",
                    "certificate_file": "/files/AuthorizationCertificate",
                }
            ).insert()
