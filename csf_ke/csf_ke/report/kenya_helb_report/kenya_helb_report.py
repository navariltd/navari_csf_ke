# Copyright (c) 2022, Navari Limited and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _

def execute(filters=None):
	company_currency = erpnext.get_company_currency(filters.get("company"))
	columns = get_columns()
	data = get_data(filters,company_currency)

	return columns, data

def get_columns():
	columns = [			
		{
		'label': _('Employee ID'),
		'fieldname': 'employee',
		'options': 'Employee',
		'width': 180
		},
		{
		'label': _('Employee Names'),
		'fieldname': 'employee_name',
		'fieldtype': 'Read Only',
		'width': 260
		},
		{
		'label': _('National ID'),
		'fieldname': 'national_id',
		'fieldtype': 'Data',
		'width': 180
		},
		{
		'label': _('Amount'),
		'fieldname': 'amount',
		'fieldtype': 'Currency',		
		'width': 200
		}
	]
		
	return columns

def apply_filters(query, filters, company_currency, salary_slip, salary_detail):
	doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

	for filter_key, filter_value in filters.items():
		if filter_key == "from_date":
			query = query.where(salary_slip.start_date == filter_value)
		elif filter_key == "to_date":
			query = query.where(salary_slip.end_date == filter_value)
		elif filter_key == "company":
			query = query.where(salary_slip.company == filter_value)
		elif filter_key == "salary_component":
			query = query.where(salary_detail.salary_component == filter_value)
		elif filter_key == "currency" and filter_value != company_currency:
			query = query.where(salary_slip.currency == filter_value)
		elif filter_key == "docstatus":
			query = query.where(salary_slip.docstatus == doc_status.get(filter_value, 0))

	return query


def get_data(filters, company_currency):
	if filters.from_date > filters.to_date:
		frappe.throw(_("To Date cannot be before From Date. {}").format(filters.to_date))
  
	employee = frappe.qb.DocType("Employee")
	salary_slip = frappe.qb.DocType("Salary Slip")
	salary_detail = frappe.qb.DocType("Salary Detail")

	query = frappe.qb.from_(employee) \
		.inner_join(salary_slip) \
		.on(employee.name == salary_slip.employee) \
		.inner_join(salary_detail) \
		.on(salary_detail.parent == salary_slip.name) \
		.select(
			employee.name,
			employee.employee_name,
			employee.national_id,
			salary_detail.amount
		).where(salary_detail.amount != 0)

	query = apply_filters(query, filters, company_currency, salary_slip, salary_detail)
	data = query.run(as_dict=True)
	
	return data
