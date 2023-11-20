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
		'width': 120
		},
		{
		'label': _('Bank Name'),
		'fieldname': 'bank_name',
		'fieldtype': 'Data',
		'width': 190
		},			
		{
		'label': _('Bank Account No'),
		'fieldname': 'bank_account_no',
		'fieldtype': 'Data',
		'width': 150
		},
		{
		'label': _('Workstation'),
		'fieldname': 'branch',
		'fieldtype': 'Data',
		'width': 150
		},
		{
		'label': _('Net Pay'),
		'fieldname': 'net_pay',
		'fieldtype': 'Currency',
		'width': 150
		}
	]
		
	return columns

def get_data(filters,company_currency):
	if filters.from_date > filters.to_date:
		frappe.throw(_("To Date cannot be before From Date. {}").format(filters.to_date))
  
	employee = frappe.qb.DocType("Employee")
	salary_slip = frappe.qb.DocType("Salary Slip")
	
	query = frappe.qb.from_(salary_slip)\
		.inner_join(employee)\
		.on(salary_slip.employee == employee.name)\
		.select(salary_slip.employee, employee.employee_name, 
				employee.national_id, salary_slip.bank_name, 
				salary_slip.bank_account_no, salary_slip.branch,
				salary_slip.net_pay)
  
	query= get_conditions(query, filters, company_currency, salary_slip)
	results= query.run(as_dict=True) 
	return results

def get_conditions(query, filters, company_currency, salary_slip):
    doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

    for filter_key, filter_value in filters.items():
        if filter_key == "from_date":
            query = query.where(salary_slip.start_date == filter_value)
        elif filter_key == "to_date":
            query = query.where(salary_slip.end_date == filter_value)
        elif filter_key == "company":
            query = query.where(salary_slip.company == filter_value)
        elif filter_key =="bank_name":
            query = query.where(salary_slip.bank_name == filter_value)
        elif filter_key == "currency" and filter_value != company_currency:
            query = query.where(salary_slip.currency == filter_value)
        elif filter_key == "docstatus":
            query = query.where(salary_slip.docstatus == doc_status.get(filter_value, 0))

    return query


