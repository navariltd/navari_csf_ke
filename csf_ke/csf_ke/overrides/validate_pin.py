import frappe
import re
from frappe.model.document import Document


def validate_pin(doctype: Document, customer: Document) -> None:
    is_kra_mandatory = frappe.get_value(
        "Customer Group", customer.customer_group, "custom_is_kra_pin_mandatory_in"
    )
    if not is_kra_mandatory:
        return

    applicable_doctypes = {
        "Customer": ["Customer", "All"],
        "Sales Order": ["Sales Order", "All", "Sales Order and Invoice"],
        "Sales Invoice": ["Sales Invoice", "All", "Sales Order and Invoice"],
    }

    doctype_name = doctype.doctype
    if (
        doctype_name not in applicable_doctypes
        or not any(option.lower() == is_kra_mandatory.lower() for option in applicable_doctypes[doctype_name])
    ):
        return

    if not customer.tax_id:
        frappe.throw("Customer KRA PIN is mandatory but not provided.")

    pattern = r"^[A-Z]\d{9}[A-Z]$"
    if not re.match(pattern, customer.tax_id):
        frappe.throw(
            "Invalid Customer KRA PIN format. Expected P123456789H or A123456789B."
        )

    company = frappe.defaults.get_defaults().get("company")
    if not company:
        companies = frappe.get_all("Company", {}, ["name"], limit=1)
        company = companies[0].name if companies else None

    if company:
        company_tax_id = frappe.get_value("Company", company, "tax_id")
        if company_tax_id and company_tax_id == customer.tax_id:
            frappe.throw("Customer KRA PIN cannot match Company Tax ID.")