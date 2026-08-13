import frappe
from frappe.model.document import Document


def set_employee_bank_details(doc: Document, method: str) -> None:
	if not doc.employee:
		return

	employee = frappe.db.get_value(
		"Employee",
		doc.employee,
		["bank_branch_name", "custom_bank_code", "custom_branch_code", "custom_sort_code"],
		as_dict=True,
	)
	if not employee:
		return

	doc.custom_bank_branch = employee.bank_branch_name
	doc.custom_bank_code = employee.custom_bank_code
	doc.custom_branch_code = employee.custom_branch_code
	doc.custom_sort_code = employee.custom_sort_code
