# Copyright (c) 2022, Navari Limited and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from pypika import functions as fn


def execute(filters=None):
	return KenyaPurchaseTaxReport(filters).run()

class KenyaPurchaseTaxReport(object):
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
					"label": _("Supplier"),
					"fieldname": "supplier",
					"fieldtype": "Link",
					"options": "Supplier",
					"width": 200
				},
				{
					"label":_("Tax Id"),
					"fieldname": "tax_id",
					"fieldtype": "Data",
					"width": 120
				},
				{
					"label": _("Invoice Number"),
					"fieldname": "name",
					"fieldtype": "Link",
					"options": "Purchase Invoice",
					"width": 180
				},
				{
					"label": _("Supplier Invoice Number"),
					"fieldname": "bill_no",
					"fieldtype": "Data",
					"width": 130
				},
				{
					"label": _("Supplier Invoice Date"),
					"fieldname": "bill_date",
					"fieldtype": "Date",
					"width": 130
				},
				{
					"label": _("Amount"),
					"fieldname": "grand_total",
					"fieldtype": "Currency",
					"width": 120
				},
				{
					"label": _("Total Taxes"),
					"fieldname": "amount",
					"fieldtype": "Currency",
					"width": 120
				},
				{
					"label": _("Tax Template"),
					"fieldname": "tax",
					"fieldtype": "Link",
					"options": "Item Tax Template",
					"width": 200
				}
			]

	def get_data(self):	
		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("To Date cannot be before From Date. {}").format(self.filters.to_date))

		invoice = frappe.qb.DocType('Purchase Invoice')
		supplier = frappe.qb.DocType('Supplier')
		taxesandcharges = frappe.qb.DocType('Purchase Taxes and Charges')
		
		return (
			frappe.qb.from_(invoice)
			.inner_join(supplier)
			.on(supplier.name == invoice.supplier)
			.left_join(taxesandcharges)
			.on(invoice.name == taxesandcharges.parent)
			.select(invoice.supplier, supplier.tax_id, invoice.name, invoice.bill_no, 
				invoice.posting_date, invoice.bill_date, invoice.grand_total, invoice.company,
				fn.IfNull(taxesandcharges.tax_amount,0).as_('amount'),
				fn.Concat(taxesandcharges.account_head,' - ', taxesandcharges.rate).as_('tax'))
			.where(invoice.docstatus == 1)
			.where(fn.Coalesce(invoice.posting_date)[self.filters.from_date:self.filters.to_date])
			.where(invoice.company == self.filters.company)
			.groupby(invoice.supplier,invoice.posting_date,invoice.name,taxesandcharges.account_head)
			.orderby(invoice.supplier,invoice.posting_date)
		).run(as_dict=True)