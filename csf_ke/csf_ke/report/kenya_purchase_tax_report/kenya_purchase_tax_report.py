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
			conditions += " AND purchase_invoice.is_return = 1"
		if(is_return == "Normal Purchase Invoice"):
			conditions += " AND purchase_invoice.is_return = 0"

		report_details = []
		
		purchase_invoice_= frappe.qb.DocType("Purchase Invoice")
		supplier_= frappe.qb.DocType("Supplier")
  
		purchase_invoices_query=frappe.qb.from_(purchase_invoice_)\
			 	.inner_join(supplier_)\
				.on(purchase_invoice_.supplier == supplier_.name)\
				.select(
					supplier_.tax_id.as_("pin_of_supplier") if supplier_.tax_id else " ".as_("pin_of_supplier"),
					purchase_invoice_.supplier_name.as_("name_of_supplier"),
					purchase_invoice_.etr_invoice_number.as_("etr_invoice_number"),
					purchase_invoice_.posting_date.as_("invoice_date"),
					purchase_invoice_.name.as_("invoice_name"),
					purchase_invoice_.base_grand_total.as_("invoice_total_purchases"),
					purchase_invoice_.return_against.as_("return_against"))\
         
		if (company):
			purchase_invoices_query=purchase_invoices_query.where(purchase_invoice_.company == company)
		if (is_return =="Is Return"):
			purchase_invoices_query=purchase_invoices_query.where(purchase_invoice_.is_return == 1)
		if (is_return =="Normal Purchase Invoice"):
			purchase_invoices_query=purchase_invoices_query.where(purchase_invoice_.is_return == 0)
		if from_date is not None:
			frappe.msgprint(str(from_date))
			purchase_invoices_query=purchase_invoices_query.where(purchase_invoice_.posting_date >= from_date)
		if (to_date):
			purchase_invoices_query=purchase_invoices_query.where(purchase_invoice_.posting_date <= to_date)
	
		purchase_invoices=purchase_invoices_query.run(as_dict=True)
		
		for purchase_invoice in purchase_invoices:
			report_details.append(purchase_invoice)

			condition_tax_template = " AND 1=1 "

			if tax_template:
				condition_tax_template += f"AND purchase_invoice_item.item_tax_template = '{tax_template}'"
	
			#Customizations for Kenya Purchase Tax Report Item
			purchase_invoice_item_=frappe.qb.DocType("Purchase Invoice Item")
			purchase_invoice_items_query=frappe.qb.from_(purchase_invoice_item_).select(	
											purchase_invoice_item_.amount.as_("amount"),
											purchase_invoice_item_.base_net_amount.as_("taxable_value"),
											purchase_invoice_item_.item_tax_template.as_("item_tax_template"))\
											.where(purchase_invoice_item_.parent == purchase_invoice.invoice_name)
			if (tax_template):
				purchase_invoice_items_query=purchase_invoice_items_query.where(purchase_invoice_item_.item_tax_template == tax_template)
			item_or_services=purchase_invoice_items_query.run(as_dict=True)
			
			total_taxable_value = 0
			total_vat = 0

			for item_or_service in item_or_services:
				# get tax rate for each item and calculate VAT
				tax_rate = frappe.db.get_value('Item Tax Template Detail',
					{'parent': item_or_service['item_tax_template']},
					['tax_rate'])
				item_or_service['amount_of_vat'] = 0 if not tax_rate else item_or_service['taxable_value'] * (tax_rate / 100)

				total_taxable_value += item_or_service['taxable_value']
				total_vat += item_or_service['amount_of_vat']
				item_or_service['indent'] = 1

			purchase_invoice['taxable_value'] = total_taxable_value
			purchase_invoice['amount_of_vat'] = total_vat

		report_details = list(filter(lambda report_entry: report_entry['taxable_value'], report_details))

		for report_entry in report_details: 
			if report_entry['pin_of_supplier']:
				self.registered_suppliers_total_purchases += report_entry['invoice_total_purchases']
				self.registered_suppliers_total_vat += report_entry['amount_of_vat']
			else:
				self.unregistered_suppliers_total_purchases += report_entry['invoice_total_purchases']	
				self.unregistered_suppliers_total_vat += report_entry['amount_of_vat']

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
  