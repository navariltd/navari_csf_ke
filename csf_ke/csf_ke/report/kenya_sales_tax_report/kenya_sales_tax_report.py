# Copyright (c) 2022, Navari Limited and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from pypika import functions as fn

def execute(filters=None):
	return KenyaSalesTaxReport(filters).run()

class KenyaSalesTaxReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})

		if not self.filters.to_date:
			self.filters.to_date = "invoice.posting_date <= %(to_date)s"

		if not self.filters.from_date:
			self.filters.from_date = "invoice.posting_date >= %(from_date)s"

		if not self.filters.company:
			self.filters.company = "invoice.company = %(company)s"

		self.query_filters = {'posting_date': ['between', [self.filters.from_date, self.filters.to_date]]}

	def run(self):
		columns = self.get_columns()
		data = self.get_data()

		return columns, data
 
	def get_columns(self):
		return [
				{
					"label": _("Customer"),
					"fieldname": "customer",
					"fieldtype": "Link",
					"options": "Customer",
					"width": 250
				},
				{
					"label":_("Date"),
					"fieldname": "posting_date",
					"fieldtype": "Date",
					"width": 150
				},
				{
					"label": _("Invoice Number"),
					"fieldname": "name",
					"fieldtype": "Link",
					"options": "Sales Invoice",
					"width": 230
				},
				{
					"label": _("Amount"),
					"fieldname": "grand_total",
					"fieldtype": "Currency",
					"width": 150
				},
				{
					"label": _("Total Taxes"),
					"fieldname": "amount",
					"fieldtype": "Currency",
					"width": 150
				},
				{
					"label": _("Tax Template"),
					"fieldname": "tax",
					"fieldtype": "Link",
					"options": "Item Tax Template",
					"width": 250
				}
			]

	def get_data(self):
		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("To Date cannot be before From Date. {}").format(self.filters.to_date))

		invoice = frappe.qb.DocType('Sales Invoice')
		taxesandcharges = frappe.qb.DocType('Sales Taxes and Charges')

		return (
			frappe.qb.from_(invoice)
			.left_join(taxesandcharges)
			.on(invoice.name == taxesandcharges.parent)
			.select(invoice.customer, invoice.posting_date, invoice.name, invoice.grand_total, invoice.company,
				fn.IfNull(taxesandcharges.tax_amount,0).as_('amount'),
				fn.Concat(taxesandcharges.account_head,' - ', taxesandcharges.rate).as_('tax'))
			.where(invoice.docstatus == 1)
			.where(fn.Coalesce(invoice.posting_date)[self.filters.from_date:self.filters.to_date])
			.where(invoice.company == self.filters.company)
			.groupby(invoice.customer,invoice.posting_date,invoice.name,taxesandcharges.account_head)
			.orderby(invoice.customer,invoice.posting_date)
		).run(as_dict=True)