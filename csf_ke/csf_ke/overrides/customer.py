import frappe
from frappe.model.document import Document

from .validate_pin import validate_pin


@frappe.whitelist()
def validate_customer_kra(doc: Document, method: str) -> None:
	validate_pin(doc, doc)
