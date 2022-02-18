# Copyright (c) 2022, Navari Limited and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from pypika import functions as fn

def execute(filters=None):
	return NhifReport(filters).run()

class NhifReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})

		if not self.filters.to_date:
			self.filters.to_date = "ss.posting_date <= %(to_date)s"

		if not self.filters.from_date:
			self.filters.from_date = "ss.posting_date >= %(from_date)s"

		if not self.filters.company:
			self.filters.company = "ss.company = %(company)s"

		if not self.filters.salary_component:
			self.filters.salary_component = "sd.salary_component = %(salary_component)s"
		
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
			'label': _('Payroll Entry'),
			'fieldname': 'employee',
			'fieldtype': 'Link',
			'options': 'Employee',
			'width': 200
			},
			{
			'label': _('Surname'),
			'fieldname': 'last_name',
			'fieldtype': 'Data',
			'width': 150
			},
			{
			'label': _('Other Names'),
			'fieldname': 'other_name',
			'fieldtype': 'Data',
			'width': 250
			},
			{
			'label': _('National ID'),
			'fieldname': 'national_id',
			'fieldtype': 'Data',
			'width': 150
			},			
			{
			'label': _('NHIF No'),
			'fieldname': 'nhif_no',
			'fieldtype': 'Data',
			'width': 150
			},
			{
			'label': _('Amount'),
			'fieldname': 'amount',
			'fieldtype': 'Currency',		
			'width': 200
			}
		]

	def get_data(self):
		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("To Date cannot be before From Date. {}").format(self.filters.to_date))

		e = frappe.qb.DocType('Employee')
		ss = frappe.qb.DocType('Salary Slip')
		sd = frappe.qb.DocType('Salary Detail')

		return(
			frappe.qb.from_(e)
			.inner_join(ss)		
			.on(e.name == ss.employee)
			.left_join(sd)
			.on(sd.parent == ss.name)
			.select(ss.employee, ss.posting_date,ss.currency,
				e.national_id, e.nhif_no, sd.amount,sd.salary_component, 
				fn.IfNull(e.last_name,'').as_('last_name'),
				fn.Concat(fn.IfNull(e.first_name,''), ' ', fn.IfNull(e.middle_name,'')).as_('other_name')
			)
			.where(ss.company == self.filters.company)
			.where(fn.Coalesce(ss.posting_date)[self.filters.from_date:self.filters.to_date])
			.where(sd.salary_component == self.filters.salary_component)
			.where(ss.currency == self.filters.currency)
			.where(ss.docstatus == 1 )
			.where(sd.amount != 0)			
			.orderby(ss.posting_date)
		).run(as_dict=True)	

