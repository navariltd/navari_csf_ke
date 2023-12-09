# Copyright (c) 2022, Navari Limited and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	return KenyaSalesTaxReport(filters).run()

class KenyaSalesTaxReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.registered_customers_total_sales = 0
		self.registered_customers_total_vat = 0
		self.unregistered_customers_total_sales = 0
		self.unregistered_customers_total_vat = 0

	def run(self):
		columns = self.get_columns()
		data = self.get_data()
		report_summary = self.get_report_summary()

		return columns, data, None, None, report_summary
 
	def get_columns(self):
		columns =  [
				{
					"label": _("PIN of purchaser"),
					"fieldname": "pin_of_purchaser",
					"fieldtype": "Data",
					"width": 160
				},
				{
					"label": _("Name of purchaser"),
					"fieldname": "name_of_purchaser",
					"fieldtype": "Data",
					"width": 240
				},
				{
					"label":_("Invoice Date"),
					"fieldname": "invoice_date",
					"fieldtype": "Date",
					"width": 160
				},
				{
					"label": _("Invoice Number"),
					"fieldname": "invoice_name",
					"fieldtype": "Link",
					"options": "Sales Invoice",
					"width": 200
				},
				{
					"label": _("ETR Serial Number"),
					"fieldname": "etr_serial_number",
					"fieldtype": "Data",
					"width": 200
				},
				{
					"label": _("ETR Invoice Number"),
					"fieldname": "etr_invoice_number",
					"fieldtype": "Data",
					"width": 200
				},
				{
					"fieldname": _("cu_link"),
					"label": "CU Link",
					"fieldtype": "Data",
					"width": 200
				},
				{
					"label": _("CU Invoice Date"),
					"fieldname": "cu_invoice_date",
					"fieldtype": "Date",
					"width": 200
		   		},
				{
					"label": _("Taxable Value(Ksh)"),
					"fieldname": "taxable_value",
					"fieldtype": "Currency",
					"width": 160
				},
				{
					"label": _("Amount of VAT(Ksh)"),
					"fieldname": "amount_of_vat",
					"fieldtype": "Currency",
					"width": 160
				}
		]

		if self.filters.is_return == "Is Return":
			columns += [
				{
					"label": _("Return Against"),
					"fieldname": "return_against",
					"fieldtype": "Link",
					"options": "Sales Invoice",
					"width": 200
				}
			]

		return columns
	
	def get_sales_invoices(self):
		company = self.filters.company
		from_date = self.filters.from_date
		to_date = self.filters.to_date
		is_return = self.filters.is_return

		sale_invoice_doc = frappe.qb.DocType('Sales Invoice')
		customer_doc = frappe.qb.DocType('Customer')

		sales_invoice_query = frappe.qb.from_(sale_invoice_doc) \
			.inner_join(customer_doc) \
			.on(sale_invoice_doc.customer == customer_doc.name) \
			.select(
				sale_invoice_doc.tax_id.as_('pin_of_purchaser') if sale_invoice_doc.tax_id else "".as_('pin_of_purchaser'),
				sale_invoice_doc.customer_name.as_('name_of_purchaser'),
					sale_invoice_doc.etr_serial_number.as_('etr_serial_number'),
					sale_invoice_doc.etr_invoice_number.as_('etr_invoice_number'),
					sale_invoice_doc.cu_link.as_('cu_link'),
					sale_invoice_doc.cu_invoice_date.as_('cu_invoice_date'),
					sale_invoice_doc.posting_date.as_('invoice_date'),
					sale_invoice_doc.name.as_('invoice_name'),
					sale_invoice_doc.base_grand_total.as_('invoice_total_sales'),
					sale_invoice_doc.return_against.as_('return_against'))
			

		if company:
			sales_invoice_query = sales_invoice_query.where(sale_invoice_doc.company == company)
		if is_return == "Is Return":
			sales_invoice_query = sales_invoice_query.where(sale_invoice_doc.is_return == 1)
		if is_return == "Normal Sales Invoice":
			sales_invoice_query = sales_invoice_query.where(sale_invoice_doc.is_return == 0)
		if from_date:
			sales_invoice_query = sales_invoice_query.where(sale_invoice_doc.posting_date >= from_date)
		if to_date:
			sales_invoice_query = sales_invoice_query.where(sale_invoice_doc.posting_date <= to_date)

		sales_invoices = sales_invoice_query.run(as_dict=True)
		return sales_invoices


	def get_sales_invoice_items(self, sales_invoice_name, tax_template=None):
		sales_invoice_item_doc = frappe.qb.DocType('Sales Invoice Item')
		sales_invoice_items_query = frappe.qb.from_(sales_invoice_item_doc) \
			.select(
				sales_invoice_item_doc.amount.as_('amount'),
				sales_invoice_item_doc.base_net_amount.as_('taxable_value'),
				sales_invoice_item_doc.item_tax_template.as_('item_tax_template')
			) \
			.where(sales_invoice_item_doc.parent == sales_invoice_name)

		if tax_template:
			sales_invoice_items_query = sales_invoice_items_query.where(sales_invoice_item_doc.item_tax_template == tax_template)

		items_or_services = sales_invoice_items_query.run(as_dict=True)
		return items_or_services

	def get_data(self):
		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("To Date cannot be before From Date. {}").format(self.filters.to_date))
		report_details = []

		sales_invoices = self.get_sales_invoices()

		for sales_invoice in sales_invoices:
			report_details.append(sales_invoice)

			items_or_services = self.get_sales_invoice_items(sales_invoice.invoice_name, self.filters.tax_template)

			total_taxable_value = 0
			total_vat = 0

			for item_or_service in items_or_services:
				tax_rate = frappe.db.get_value('Item Tax Template Detail',
											{'parent': item_or_service['item_tax_template']},
											['tax_rate'])
				item_or_service['amount_of_vat'] = 0 if not tax_rate else item_or_service['taxable_value'] * (tax_rate / 100)

				total_taxable_value += item_or_service['taxable_value']
				total_vat += item_or_service['amount_of_vat']
				item_or_service['indent'] = 1

			sales_invoice['taxable_value'] = total_taxable_value
			sales_invoice['amount_of_vat'] = total_vat

		report_details = list(filter(lambda report_entry: report_entry['taxable_value'], report_details))

		for report_entry in report_details:
			if report_entry['pin_of_purchaser']:
				self.registered_customers_total_sales += report_entry['invoice_total_sales']
				self.registered_customers_total_vat += report_entry['amount_of_vat']
			else:
				self.unregistered_customers_total_sales += report_entry['invoice_total_sales']
				self.unregistered_customers_total_vat += report_entry['amount_of_vat']

		return report_details


	def get_report_summary(self):
		return [{
			"value": self.registered_customers_total_sales,
			"indicator": "Green",
			"label": _("Registered customers total sales"),
			"datatype": "Currency",
			"currency": "KES"
		}, {
			"value": self.registered_customers_total_vat,
			"indicator": "Green",
			"label": _("Registered customers total VAT"),
			"datatype": "Currency",
			"currency": "KES"
		}, {
			"value": self.unregistered_customers_total_sales,
			"indicator": "Green",
			"label": _("Unregistered customers total sales"),
			"datatype": "Currency",
			"currency": "KES"
		}, {
			"value": self.unregistered_customers_total_vat,
			"indicator": "Green",
			"label": _("Unregistered customers total VAT"),
			"datatype": "Currency",
			"currency": "KES"
		}]
