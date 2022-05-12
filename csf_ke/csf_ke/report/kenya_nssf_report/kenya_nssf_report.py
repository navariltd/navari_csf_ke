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
		'label': _('Payroll No'),
		'fieldname': 'employee',
		'fieldtype': 'Link',
		'options': 'Employee',
		'width': 150
		},
		{
		'label': _('Surname'),
		'fieldname': 'last_name',
		'fieldtype': 'Data',
		'width': 140
		},
		{
		'label': _('Other Names'),
		'fieldname': 'other_name',
		'fieldtype': 'Data',
		'width': 200
		},
		{
		'label': _('National ID'),
		'fieldname': 'national_id',
		'fieldtype': 'Data',
		'width': 140
		},
		{
		'label': _('KRA No'),
		'fieldname': 'tax_id',
		'fieldtype': 'Data',
		'width': 140
		},			
		{
		'label': _('NSSF No'),
		'fieldname': 'nssf_no',
		'fieldtype': 'Data',
		'width': 140
		},
		{
		'label': _('Gross Pay'),
		'fieldname': 'gross_pay',
		"fieldtype": "Currency",		
		'width': 200
		}
	]

	return columns

def get_data(filters,company_currency,conditions=""):
	conditions = get_conditions(filters, company_currency)

	if filters.from_date > filters.to_date:
		frappe.throw(_("To Date cannot be before From Date. {}").format(filters.to_date))
	
	data = frappe.db.sql("""
	SELECT	ss.employee, IFNULL(e.last_name,'') AS last_name,
	        CONCAT(IFNULL(e.first_name,''), ' ', IFNULL(e.middle_name,'')) AS other_name,
			e.national_id, e.tax_id, e.nssf_no,	ss.start_date,
			ss.end_date, ss.gross_pay, ss.company, sc.salary_component
	FROM `tabEmployee` e, `tabSalary Slip` ss, `tabSalary Component` sc
	WHERE %s
		and e.name = ss.employee
	""" % conditions, filters, as_dict=1)

	return data

def get_conditions(filters, company_currency):
	conditions = ""
	doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

	if filters.get("docstatus"):
		conditions += "ss.docstatus = {0}".format(doc_status[filters.get("docstatus")])

	if filters.get("from_date"): conditions += " and ss.start_date = %(from_date)s"
	if filters.get("to_date"): conditions += " and ss.end_date = %(to_date)s"
	if filters.get("company"): conditions += " and ss.company = %(company)s"
	if filters.get("salary_component"): conditions += " and sc.salary_component = %(salary_component)s"
	if filters.get("currency") and filters.get("currency") != company_currency:
		conditions += " and ss.currency = %(currency)s"

	return conditions


