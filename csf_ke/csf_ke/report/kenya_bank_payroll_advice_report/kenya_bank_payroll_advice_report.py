# Copyright (c) 2022, Navari Limited and contributors
# For license information, please see license.txt

import erpnext
import frappe
from frappe import _


def execute(filters=None):
	company_currency = erpnext.get_company_currency(filters.get("company"))
	columns = get_columns()
	data = get_data(filters, company_currency)
	report_summary = get_report_summary(data, filters, company_currency)

	return columns, data, None, None, report_summary


def get_columns():
	columns = [
		{"label": _("Employee ID"), "fieldname": "employee", "options": "Employee", "width": 180},
		{"label": _("Employee Names"), "fieldname": "employee_name", "fieldtype": "Read Only", "width": 260},
		{"label": _("National ID"), "fieldname": "national_id", "fieldtype": "Data", "width": 120},
		{"label": _("Bank Name"), "fieldname": "bank_name", "fieldtype": "Data", "width": 190},
		{"label": _("Bank Code"), "fieldname": "bank_code", "fieldtype": "Data", "width": 120},
		{"label": _("Bank Branch"), "fieldname": "bank_branch", "fieldtype": "Data", "width": 150},
		{"label": _("Branch Code"), "fieldname": "branch_code", "fieldtype": "Data", "width": 120},
		{"label": _("Sort Code"), "fieldname": "sort_code", "fieldtype": "Data", "width": 120},
		{"label": _("Bank Account No"), "fieldname": "bank_account_no", "fieldtype": "Data", "width": 150},
		{"label": _("Paying Bank Name"), "fieldname": "paying_bank", "fieldtype": "Data", "width": 190},
		{"label": _("Workstation"), "fieldname": "branch", "fieldtype": "Data", "width": 150},
		{"label": _("Net Pay"), "fieldname": "net_pay", "fieldtype": "Currency", "width": 150},
	]

	return columns


def get_data(filters, company_currency):
	if filters.from_date > filters.to_date:
		frappe.throw(_("To Date cannot be before From Date. {}").format(filters.to_date))

	employee_doc = frappe.qb.DocType("Employee")
	salary_slip_doc = frappe.qb.DocType("Salary Slip")
	payroll_entry_doc = frappe.qb.DocType("Payroll Entry")
	bank_account_doc = frappe.qb.DocType("Bank Account")

	query = (
		frappe.qb.from_(salary_slip_doc)
		.inner_join(employee_doc)
		.on(salary_slip_doc.employee == employee_doc.name)
		.left_join(payroll_entry_doc)
		.on(salary_slip_doc.payroll_entry == payroll_entry_doc.name)
		.left_join(bank_account_doc)
		.on(payroll_entry_doc.bank_account == bank_account_doc.name)
		.select(
			salary_slip_doc.employee,
			employee_doc.employee_name,
			employee_doc.national_id,
			salary_slip_doc.bank_name,
			salary_slip_doc.custom_bank_code.as_("bank_code"),
			salary_slip_doc.custom_bank_branch.as_("bank_branch"),
			salary_slip_doc.custom_branch_code.as_("branch_code"),
			salary_slip_doc.custom_sort_code.as_("sort_code"),
			salary_slip_doc.bank_account_no,
			bank_account_doc.bank.as_("paying_bank"),
			salary_slip_doc.branch,
			salary_slip_doc.net_pay,
		)
	)

	query = get_conditions(query, filters, company_currency, salary_slip_doc, payroll_entry_doc)
	data = query.run(as_dict=True)
	return data


def get_conditions(query, filters, company_currency, salary_slip_doc, payroll_entry_doc):
	doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

	for filter_key, filter_value in filters.items():
		if filter_key == "from_date":
			query = query.where(salary_slip_doc.start_date >= filter_value)
		elif filter_key == "to_date":
			query = query.where(salary_slip_doc.end_date <= filter_value)
		elif filter_key == "company":
			query = query.where(salary_slip_doc.company == filter_value)
		elif filter_key == "bank_name":
			query = query.where(salary_slip_doc.bank_name == filter_value)
		elif filter_key == "paying_bank" and filter_value:
			query = query.where(payroll_entry_doc.bank_account == filter_value)
		elif filter_key == "currency" and filter_value != company_currency:
			query = query.where(salary_slip_doc.currency == filter_value)
		elif filter_key == "docstatus":
			query = query.where(salary_slip_doc.docstatus == doc_status.get(filter_value, 0))
	return query


def get_report_summary(data, filters, company_currency):
	"""One summary card per bank (label shows the staff count, value is the total
	to be paid to that bank) plus a grand-total card across all banks."""
	if not data:
		return []

	currency = filters.get("currency") or company_currency

	summary = {}
	grand_total = 0
	for row in data:
		bank = row.get("bank_name") or _("(No Bank)")
		net_pay = row.get("net_pay") or 0
		entry = summary.setdefault(bank, {"count": 0, "total": 0})
		entry["count"] += 1
		entry["total"] += net_pay
		grand_total += net_pay

	report_summary = []
	for bank in sorted(summary):
		report_summary.append(
			{
				"label": _("{0} ({1} staff)").format(bank, summary[bank]["count"]),
				"value": summary[bank]["total"],
				"datatype": "Currency",
				"currency": currency,
				"indicator": "Blue",
			}
		)

	report_summary.append(
		{
			"label": _("Total ({0} staff)").format(len(data)),
			"value": grand_total,
			"datatype": "Currency",
			"currency": currency,
			"indicator": "Green",
		}
	)

	return report_summary
