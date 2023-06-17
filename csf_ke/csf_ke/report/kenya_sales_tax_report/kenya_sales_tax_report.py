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
				# {
				# 	"label": _("ETR Serial Number"),
				# 	"fieldname": "etr_serial_number",
				# 	"fieldtype": "Data",
				# 	"width": 200
				# },
				# {
				# 	"label": _("ETR Invoice Number"),
				# 	"fieldname": "etr_invoice_number",
				# 	"fieldtype": "Data",
				# 	"width": 200
				# },
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
					"label": _("Description of Goods/Services"),
					"fieldname": "description_of_goods_services",
					"fieldtype": "Data",
					"width": 280
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

		# columns += [
		# 	{
		# 		"label":_("Relevant Invoice Number"),
		# 		"fieldname": "relevant_invoice_number",
		# 		"fieldtype": "Data",
		# 		"width": 200
		# 	},
		# 	{
		# 		"label":_("Relevant Invoice Date"),
		# 		"fieldname": "relevant_invoice_date",
		# 		"fieldtype": "Date",
		# 		"width": 200
		# 	}
		# ]

		return columns
	

	def get_data(self):
		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("To Date cannot be before From Date. {}").format(self.filters.to_date))

		company, from_date, to_date, is_return, tax_template = self.filters.company, self.filters.from_date, self.filters.to_date, self.filters.is_return, self.filters.tax_template

		conditions = " AND sales_invoice.docstatus = 1 "

		if(company):
			conditions += f" AND sales_invoice.company = '{company}'"
		if(is_return == "Is Return"):
			conditions += f" AND sales_invoice.is_return = 1"
		if(is_return == "Normal Sales Invoice"):
			conditions += f" AND sales_invoice.is_return = 0"

		report_details = []

		sales_invoices = frappe.db.sql(f"""
			SELECT
				IFNULL(customer.tax_id, NULL) as pin_of_purchaser,
				sales_invoice.customer_name as name_of_purchaser,
				sales_invoice.etr_serial_number as etr_serial_number,
				sales_invoice.etr_invoice_number as etr_invoice_number,
				sales_invoice.posting_date as invoice_date,
				sales_invoice.name as invoice_name,
				sales_invoice.base_grand_total as invoice_total_sales,
				sales_invoice.return_against as return_against
			FROM 
    			`tabSales Invoice` as `sales_invoice`
			INNER JOIN 
    			`tabCustomer` as `customer` 
			ON
    			customer.name = sales_invoice.customer
			WHERE (sales_invoice.posting_date BETWEEN '{from_date}' AND '{to_date}') {conditions};
		""", as_dict = 1)

		for sales_invoice in sales_invoices:
			report_details.append(sales_invoice)

			condition_tax_template = " AND 1=1 "

			if tax_template:
				condition_tax_template += f"AND sales_invoice_item.item_tax_template = '{tax_template}'"

			items_or_services = frappe.db.sql(f"""
				SELECT 
					sales_invoice_item.description as description_of_goods_services,
					sales_invoice_item.amount as amount,
					sales_invoice_item.base_net_amount as taxable_value,
					sales_invoice_item.item_tax_template as item_tax_template
				FROM
    				`tabSales Invoice Item` as `sales_invoice_item`
				WHERE parent = '{sales_invoice.invoice_name}' {condition_tax_template};
			""", as_dict = 1)

			# total_taxable_value and total_vat for every single invoice
			total_taxable_value = 0
			total_vat = 0

			for item_or_service in items_or_services:
				# get tax rate for each item and calculate VAT
				tax_rate = frappe.db.get_value('Item Tax Template Detail',
					{'parent': item_or_service['item_tax_template']},
					['tax_rate'])
				item_or_service['amount_of_vat'] = 0 if not tax_rate else item_or_service['taxable_value'] * (tax_rate / 100)

				total_taxable_value += item_or_service['taxable_value']
				total_vat += item_or_service['amount_of_vat']
				item_or_service['indent'] = 1
				report_details.append(item_or_service)

			sales_invoice['taxable_value'] = total_taxable_value
			sales_invoice['amount_of_vat'] = total_vat

		report_details = list(filter(lambda report_entry: report_entry['taxable_value'], report_details))

		# separate registered_customer and unregistered customer invoices.
		registered_customers_sales_invoice_entries = []
		unregistered_customers_sales_invoice_entries = []

		for report_entry in report_details: 
			if 'invoice_name' in report_entry:
				if report_entry['pin_of_purchaser']:
					registered_customers_sales_invoice_entries += [report_entry]
				else:
					unregistered_customers_sales_invoice_entries += [report_entry]	

		for entry in registered_customers_sales_invoice_entries:
			self.registered_customers_total_sales += entry['invoice_total_sales']
			self.registered_customers_total_vat += entry['amount_of_vat']

		for entry in unregistered_customers_sales_invoice_entries:
			self.unregistered_customers_total_sales += entry['invoice_total_sales']
			self.unregistered_customers_total_vat += entry['amount_of_vat']

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