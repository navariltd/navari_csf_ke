import frappe
from frappe.model.document import Document


def set_employee_bank_details(doc: Document, method: str) -> None:
    if not doc.employee:
        return

    bank_branch_name, iban = frappe.db.get_value(
        "Employee", doc.employee, ["bank_branch_name", "custom_sort_code"]
    ) or (None, None)

    doc.custom_bank_branch = bank_branch_name
    doc.custom_sort_code = iban
