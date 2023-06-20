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
		self.registered_suppliers_total_purchases = 0
		self.registered_suppliers_total_vat = 0
		self.unregistered_suppliers_total_purchases = 0
		self.unregistered_suppliers_total_vat = 0

	def run(self):
		columns = self.get_columns()
		data = self.get_data()
		report_summary = self.get_report_summary()

		return columns, data, None, None, report_summary

	def get_columns(self):
		columns =  [
				{
					"label": _("PIN of supplier"),
					"fieldname": "pin_of_supplier",
					"fieldtype": "Data",
					"width": 160
				},
				{
					"label": _("Name of supplier"),
					"fieldname": "name_of_supplier",
					"fieldtype": "Data",
					"width": 240
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
					"label":_("Invoice Date"),
					"fieldname": "invoice_date",
					"fieldtype": "Date",
					"width": 160
				},
				{
					"label": _("Invoice Number"),
					"fieldname": "invoice_name",
					"fieldtype": "Link",
					"options": "Purchase Invoice",
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
					"options": "Purchase Invoice",
					"width": 200
				}
			]
		return columns

	def get_data(self):	
		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("To Date cannot be before From Date. {}").format(self.filters.to_date))

		company = self.filters.company
		from_date = self.filters.from_date
		to_date = self.filters.to_date
		is_return = self.filters.is_return
		tax_template = self.filters.tax_template

		conditions = " AND purchase_invoice.docstatus = 1 "

		if(company):
			conditions += f" AND purchase_invoice.company = '{company}'"
		if(is_return == "Is Return"):
			conditions += f" AND purchase_invoice.is_return = 1"
		if(is_return == "Normal Purchase Invoice"):
			conditions += f" AND purchase_invoice.is_return = 0"

		report_details = []

		purchase_invoices = frappe.db.sql(f"""
			SELECT
				IFNULL(supplier.tax_id, NULL) as pin_of_supplier,
				purchase_invoice.supplier_name as name_of_supplier,
				purchase_invoice.etr_serial_number as etr_serial_number,
				purchase_invoice.etr_invoice_number as etr_invoice_number,
				purchase_invoice.posting_date as invoice_date,
				purchase_invoice.name as invoice_name,
				purchase_invoice.base_grand_total as invoice_total_purchases,
				purchase_invoice.return_against as return_against
			FROM 
    			`tabPurchase Invoice` as `purchase_invoice`
			INNER JOIN 
    			`tabSupplier` as `supplier` 
			ON
    			supplier.name = purchase_invoice.supplier
			WHERE (purchase_invoice.posting_date BETWEEN '{from_date}' AND '{to_date}') {conditions};
		""", as_dict = 1)

		for purchase_invoice in purchase_invoices:
			report_details.append(purchase_invoice)

			condition_tax_template = " AND 1=1 "

			if tax_template:
				condition_tax_template += f"AND purchase_invoice_item.item_tax_template = '{tax_template}'"

			items_or_services = frappe.db.sql(f"""
				SELECT 
					purchase_invoice_item.description as description_of_goods_services,
					purchase_invoice_item.amount as amount,
					purchase_invoice_item.base_net_amount as taxable_value,
					purchase_invoice_item.item_tax_template as item_tax_template
				FROM
    				`tabPurchase Invoice Item` as `purchase_invoice_item`
				WHERE parent = '{purchase_invoice.invoice_name}' {condition_tax_template};
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

			purchase_invoice['taxable_value'] = total_taxable_value
			purchase_invoice['amount_of_vat'] = total_vat

		report_details = list(filter(lambda report_entry: report_entry['taxable_value'], report_details))

		# separate registered_supplier and unregistered supplier invoices.
		registered_suppliers_purchase_invoice_entries = []
		unregistered_suppliers_purchase_invoice_entries = []

		for report_entry in report_details: 
			if 'invoice_name' in report_entry:
				if report_entry['pin_of_supplier']:
					registered_suppliers_purchase_invoice_entries += [report_entry]
				else:
					unregistered_suppliers_purchase_invoice_entries += [report_entry]	

		for entry in registered_suppliers_purchase_invoice_entries:
			self.registered_suppliers_total_purchases += entry['invoice_total_purchases']
			self.registered_suppliers_total_vat += entry['amount_of_vat']

		for entry in unregistered_suppliers_purchase_invoice_entries:
			self.unregistered_suppliers_total_purchases += entry['invoice_total_purchases']
			self.unregistered_suppliers_total_vat += entry['amount_of_vat']

		return report_details

	def get_report_summary(self):
		return [{
			"value": self.registered_suppliers_total_purchases,
			"indicator": "Green",
			"label": _("Registered suppliers total purchases"),
			"datatype": "Currency",
			"currency": "KES"
		}, {
			"value": self.registered_suppliers_total_vat,
			"indicator": "Green",
			"label": _("Registered suppliers total VAT"),
			"datatype": "Currency",
			"currency": "KES"
		}, {
			"value": self.unregistered_suppliers_total_purchases,
			"indicator": "Green",
			"label": _("Unregistered suppliers total purchases"),
			"datatype": "Currency",
			"currency": "KES"
		}, {
			"value": self.unregistered_suppliers_total_vat,
			"indicator": "Green",
			"label": _("Unregistered suppliers total VAT"),
			"datatype": "Currency",
			"currency": "KES"
		}]