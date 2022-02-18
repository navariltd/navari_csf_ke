# Copyright (c) 2022, Navari Limited and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from pypika import functions as fn

def execute(filters=None):
	return NssfReport(filters).run()

class NssfReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})

		if not self.filters.to_date:
			self.filters.to_date = "ss.posting_date <= %(to_date)s"

		if not self.filters.from_date:
			self.filters.from_date = " ss.posting_date >= %(from_date)s"

		if not self.filters.company:
			self.filters.company = "ss.company = %(company)s"

		if not self.filters.salary_component:
			self.filters.salary_component = "sc.salary_component = %(salary_component)s"
		
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

	def get_data(self):
		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("To Date cannot be before From Date. {}").format(self.filters.to_date))
		
		e = frappe.qb.DocType('Employee')
		ss = frappe.qb.DocType('Salary Slip')
		sc = frappe.qb.DocType('Salary Detail')

		return (
			frappe.qb.from_(e)
			.inner_join(ss)		
			.on(e.name == ss.employee)
			.left_join(sc)
			.on(sc.parent == ss.name)
			.select(ss.employee,e.national_id, e.tax_id, e.nssf_no, ss.posting_date, ss.gross_pay, ss.company, sc.salary_component, 
				fn.IfNull(e.last_name,'').as_('last_name'),
				fn.Concat(fn.IfNull(e.first_name,''), ' ', fn.IfNull(e.middle_name,'')).as_('other_name'))
			.where(ss.company == self.filters.company)
			.where(fn.Coalesce(ss.posting_date)[self.filters.from_date:self.filters.to_date])
			.where(sc.salary_component == self.filters.salary_component)
			.where(ss.currency == self.filters.currency)
			.where(ss.docstatus == 1 )
			.orderby(ss.posting_date)
		).run(as_dict=True)


