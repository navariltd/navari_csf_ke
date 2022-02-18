# Copyright (c) 2022, Navari Limited and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from pypika import functions as fn

def execute(filters=None):
	return BankPayrollAdvice(filters).run()

class BankPayrollAdvice(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})

		if not self.filters.to_date:
			self.filters.to_date = "ss.posting_date <= %(to_date)s"

		if not self.filters.from_date:
			self.filters.from_date = "ss.posting_date >= %(from_date)s"

		if not self.filters.company:
			self.filters.company = "ss.company = %(company)s"
	
		if not self.filters.currency:
			self.filters.currency =  "ss.currency = %(currency)s"


		self.query_filters = {'posting_date': ['between', [self.filters.from_date, self.filters.to_date]]}


	def run(self):
		columns = self.get_columns()
		data = self.get_data()

		return columns, data

	def get_columns(self):
		return [			
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

	def get_data(self):
		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("To Date cannot be before From Date. {}").format(self.filters.to_date))

		e = frappe.qb.DocType('Employee')
		ss = frappe.qb.DocType('Salary Slip')

		return (
			frappe.qb.from_(e)
			.inner_join(ss)
			.on(e.name == ss.employee)
			.select(ss.employee, ss.employee_name,ss.posting_date,ss.currency, 
				ss.bank_name, ss.bank_account_no,ss.branch, ss.net_pay, e.national_id )
			.where(ss.company == self.filters.company)
			.where(fn.Coalesce(ss.posting_date)[self.filters.from_date:self.filters.to_date])
			.where(ss.currency == self.filters.currency)
			.where(ss.docstatus == 1)
			.orderby(ss.posting_date)
		).run(as_dict=True)
