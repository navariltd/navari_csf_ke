import frappe
from frappe.model.document import Document

from .validate_pin import validate_pin


def validate_customer_kra(doc: Document, method: str) -> None:
	if not doc.customer:
		return

	customer = frappe.get_doc("Customer", doc.customer)

	validate_pin(doc, customer)
