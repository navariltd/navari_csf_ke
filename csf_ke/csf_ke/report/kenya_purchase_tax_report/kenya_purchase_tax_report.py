# Copyright (c) 2022, Navari Limited and contributors
# For license information, please see license.txt


import csv
import os
import re
from datetime import datetime

import frappe
from frappe import _


def execute(filters=None):
	return KenyaPurchaseTaxReport(filters).run()


class KenyaPurchaseTaxReport:
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
		columns = [
			{
				"label": _("PIN of supplier"),
				"fieldname": "pin_of_supplier",
				"fieldtype": "Data",
				"width": 160,
			},
			{
				"label": _("Name of supplier"),
				"fieldname": "name_of_supplier",
				"fieldtype": "Data",
				"width": 240,
			},
			{
				"label": _("ETR Invoice Number"),
				"fieldname": "etr_invoice_number",
				"fieldtype": "Data",
				"width": 200,
			},
			{
				"label": _("Invoice Date"),
				"fieldname": "invoice_date",
				"fieldtype": "Date",
				"width": 160,
			},
			{
				"label": _("Invoice Number"),
				"fieldname": "invoice_name",
				"fieldtype": "Link",
				"options": "Purchase Invoice",
				"width": 200,
			},
			{
				"label": _("Taxable Value(Ksh)"),
				"fieldname": "taxable_value",
				"fieldtype": "Currency",
				"width": 160,
			},
			{
				"label": _("Amount of VAT(Ksh)"),
				"fieldname": "amount_of_vat",
				"fieldtype": "Currency",
				"width": 160,
			},
			{
				"label": _("Return CU Invoice Number"),
				"fieldname": "return_cu_invoice_number",
				"fieldtype": "Data",
				"width": 200,
			},
			{
				"label": _("Return CU Invoice Date"),
				"fieldname": "return_cu_invoice_date",
				"fieldtype": "Date",
				"width": 160,
			},
		]

		if self.filters.is_return == "Is Return":
			columns += [
				{
					"label": _("Return Against"),
					"fieldname": "return_against",
					"fieldtype": "Link",
					"options": "Purchase Invoice",
					"width": 200,
				}
			]
		return columns

	def get_purchase_invoices(self):
		company = self.filters.company
		from_date = self.filters.from_date
		to_date = self.filters.to_date
		is_return = self.filters.is_return

		purchase_invoice_ = frappe.qb.DocType("Purchase Invoice")
		supplier_ = frappe.qb.DocType("Supplier")

		purchase_invoices_query = (
			frappe.qb.from_(purchase_invoice_)
			.inner_join(supplier_)
			.on(purchase_invoice_.supplier == supplier_.name)
			.select(
				(supplier_.tax_id.as_("pin_of_supplier") if supplier_.tax_id else " ".as_("pin_of_supplier")),
				purchase_invoice_.supplier_name.as_("name_of_supplier"),
				purchase_invoice_.etr_invoice_number.as_("etr_invoice_number"),
				purchase_invoice_.posting_date.as_("invoice_date"),
				purchase_invoice_.name.as_("invoice_name"),
				purchase_invoice_.base_grand_total.as_("invoice_total_purchases"),
				purchase_invoice_.return_against.as_("return_against"),
			)
			.where(purchase_invoice_.docstatus == 1)
		)

		if company:
			purchase_invoices_query = purchase_invoices_query.where(purchase_invoice_.company == company)
		if is_return == "Is Return":
			purchase_invoices_query = purchase_invoices_query.where(purchase_invoice_.is_return == 1)
		if is_return == "Normal Purchase Invoice":
			purchase_invoices_query = purchase_invoices_query.where(purchase_invoice_.is_return == 0)
		if from_date is not None:
			purchase_invoices_query = purchase_invoices_query.where(
				purchase_invoice_.posting_date >= from_date
			)
		if to_date:
			purchase_invoices_query = purchase_invoices_query.where(purchase_invoice_.posting_date <= to_date)

		purchase_invoices = purchase_invoices_query.run(as_dict=True)

		for invoice in purchase_invoices:
			if invoice.get("return_against"):
				return_invoice_details = frappe.db.get_value(
					"Purchase Invoice",
					invoice["return_against"],
					["etr_invoice_number", "bill_date"],
					as_dict=True,
				)
				if return_invoice_details:
					invoice["return_cu_invoice_number"] = return_invoice_details.get("etr_invoice_number")
					invoice["return_cu_invoice_date"] = return_invoice_details.get("bill_date")

		return purchase_invoices

	def get_purchase_invoice_items(self, purchase_invoice_name, tax_template=None):
		purchase_invoice_item_ = frappe.qb.DocType("Purchase Invoice Item")
		purchase_invoice_items_query = (
			frappe.qb.from_(purchase_invoice_item_)
			.select(
				purchase_invoice_item_.amount.as_("amount"),
				purchase_invoice_item_.base_net_amount.as_("taxable_value"),
				purchase_invoice_item_.item_tax_template.as_("item_tax_template"),
			)
			.where(purchase_invoice_item_.parent == purchase_invoice_name)
		)

		if tax_template:
			purchase_invoice_items_query = purchase_invoice_items_query.where(
				purchase_invoice_item_.item_tax_template == tax_template
			)

		items_or_services = purchase_invoice_items_query.run(as_dict=True)
		return items_or_services

	def get_data(self):
		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("To Date cannot be before From Date. {}").format(self.filters.to_date))

		report_details = []

		purchase_invoices = self.get_purchase_invoices()

		for purchase_invoice in purchase_invoices:
			report_details.append(purchase_invoice)

			items_or_services = self.get_purchase_invoice_items(
				purchase_invoice.invoice_name, self.filters.tax_template
			)

			total_taxable_value = 0
			total_vat = 0

			for item_or_service in items_or_services:
				tax_rate = frappe.db.get_value(
					"Item Tax Template Detail",
					{"parent": item_or_service["item_tax_template"]},
					["tax_rate"],
				)
				item_or_service["amount_of_vat"] = (
					0 if not tax_rate else item_or_service["taxable_value"] * (tax_rate / 100)
				)

				total_taxable_value += item_or_service["taxable_value"]
				total_vat += item_or_service["amount_of_vat"]
				item_or_service["indent"] = 1

			purchase_invoice["taxable_value"] = total_taxable_value
			purchase_invoice["amount_of_vat"] = total_vat

		report_details = list(filter(lambda report_entry: report_entry["taxable_value"], report_details))

		for report_entry in report_details:
			if report_entry["pin_of_supplier"]:
				self.registered_suppliers_total_purchases += report_entry["invoice_total_purchases"]
				self.registered_suppliers_total_vat += report_entry["amount_of_vat"]
			else:
				self.unregistered_suppliers_total_purchases += report_entry["invoice_total_purchases"]
				self.unregistered_suppliers_total_vat += report_entry["amount_of_vat"]

		return report_details

	def get_report_summary(self):
		return [
			{
				"value": self.registered_suppliers_total_purchases,
				"indicator": "Green",
				"label": _("Registered suppliers total purchases"),
				"datatype": "Currency",
				"currency": "KES",
			},
			{
				"value": self.registered_suppliers_total_vat,
				"indicator": "Green",
				"label": _("Registered suppliers total VAT"),
				"datatype": "Currency",
				"currency": "KES",
			},
			{
				"value": self.unregistered_suppliers_total_purchases,
				"indicator": "Green",
				"label": _("Unregistered suppliers total purchases"),
				"datatype": "Currency",
				"currency": "KES",
			},
			{
				"value": self.unregistered_suppliers_total_vat,
				"indicator": "Green",
				"label": _("Unregistered suppliers total VAT"),
				"datatype": "Currency",
				"currency": "KES",
			},
		]


@frappe.whitelist()
def download_custom_csv_format(company, from_date=None, to_date=None):
	if not company:
		frappe.throw(_("Company is required"))
	if not from_date:
		frappe.throw(_("From Date is required"))
	if not to_date:
		frappe.throw(_("To Date is required"))

	from_date_str = from_date.strftime("%y-%m-%d") if isinstance(from_date, datetime) else from_date
	to_date_str = to_date.strftime("%y-%m-%d") if isinstance(to_date, datetime) else to_date

	private_path = frappe.utils.get_site_path("private", "files")
	os.makedirs(private_path, exist_ok=True)

	tax_templates = ["VAT 16%", "Exempt", "Zero-Rated"]

	csv_files = {}

	for template_name in tax_templates:
		pattern = re.compile(rf"{re.escape(template_name)}[\s\-_]*[\d\%]*", re.IGNORECASE)

		all_tax_templates = frappe.get_all("Item Tax Template", fields=["name"])

		for template in all_tax_templates:
			match = pattern.match(template["name"])
			if match:
				# Sanitize the company and template names for the file name
				company_abbr = frappe.db.get_value("Company", company, "abbr") or ""
				sanitized_template_name = re.sub(r"[^\w]+", "_", template_name).lower()

				# Generate a valid file name
				csv_file_name = f"purchase_{sanitized_template_name[:5]}_{company_abbr}_{from_date_str}_to_{to_date_str}.csv".strip(
					"_"
				)

				full_file_path = os.path.join(private_path, csv_file_name)
				file_url = f"/private/files/{csv_file_name}"

				purchase_invoices = KenyaPurchaseTaxReport(
					{
						"company": company,
						"from_date": from_date,
						"to_date": to_date,
						"tax_template": template["name"],
					}
				).get_data()

				if purchase_invoices:
					with open(full_file_path, "w", newline="") as csvfile:
						writer = csv.writer(csvfile)

						for invoice in purchase_invoices:
							if invoice.get("pin_of_supplier"):
								writer.writerow(
									[
										"Local",
										invoice.get("pin_of_supplier", ""),
										invoice.get("name_of_supplier", ""),
										invoice.get("invoice_date", "").strftime("%d/%m/%Y"),
										f"|{(invoice.get('etr_invoice_number', ''))}",
										invoice.get("invoice_name", ""),
										"",
										invoice.get("taxable_value", ""),
										"",
										f"{'|' + invoice.get('return_cu_invoice_number', '') if invoice.return_against else ''}",
										invoice.get("return_cu_invoice_date").strftime("%d/%m/%Y")
										if invoice.return_against and invoice.get("return_cu_invoice_date")
										else "",
									]
								)

					file_record = frappe.get_doc(
						{
							"doctype": "File",
							"file_name": csv_file_name,
							"file_url": file_url,
							"attached_to_name": company,
							"attached_to_doctype": "Purchase Invoice",
							"file_size": os.path.getsize(full_file_path),
							"is_private": 1,
							"file_type": "CSV",
						}
					)
					file_record.insert()

					csv_files[company_abbr] = file_url

	return csv_files
