# Copyright (c) 2022, Navari Limited and contributors
# For license information, please see license.txt

import csv
import os
import re
from datetime import datetime
from typing import TypedDict

import frappe
from frappe import _

from csf_ke.csf_ke.utils.tax_report import TaxReport


class KenyaPurchaseTaxReportFilters(TypedDict):
	company: str | None
	from_date: str | None
	to_date: str | None
	is_return: int | None
	item_tax_template: str | None
	taxes_and_charges_template: str | None
	accounting_dimension: str | None


def execute(filters: KenyaPurchaseTaxReportFilters | None = None):
	report = KenyaPurchaseTaxReport(filters)
	return report.run()


class KenyaPurchaseTaxReport(TaxReport):
	def __init__(self, filters: KenyaPurchaseTaxReportFilters | None = None):
		super().__init__()
		self.filters = filters or {}
		self.company = self.filters.get("company")
		self.from_date = self.filters.get("from_date")
		self.to_date = self.filters.get("to_date")
		self.item_tax_template = self.filters.get("item_tax_template")
		self.taxes_and_charges_template = self.filters.get("taxes_and_charges_template")

	def run(self):
		columns = self.get_columns()
		data = self.get_data("purchase")

		return columns, data, None, None, self.get_report_summary()

	def get_columns(self):
		columns = [
			{
				"label": _("Supplier PIN"),
				"fieldname": "tax_id",
				"fieldtype": "Data",
				"width": 150,
			},
			{
				"label": _("Supplier Name"),
				"fieldname": "party_name",
				"fieldtype": "Data",
				"width": 200,
			},
			{
				"label": _("Invoice Number"),
				"fieldname": "invoice_number",
				"fieldtype": "Link",
				"options": "Purchase Invoice",
				"width": 200,
			},
			{
				"label": _("Invoice Date"),
				"fieldname": "invoice_date",
				"fieldtype": "Date",
				"width": 200,
			},
			{
				"label": _("ETR Invoice Number"),
				"fieldname": "etr_invoice_number",
				"fieldtype": "Data",
				"width": 200,
			},
			{
				"label": _("Supplier Invoice No"),
				"fieldname": "supplier_invoice_no",
				"fieldtype": "Data",
				"width": 200,
			},
			{
				"label": _("Supplier Invoice Date"),
				"fieldname": "supplier_invoice_date",
				"fieldtype": "Date",
				"width": 200,
			},
			{
				"label": _("Taxable Amount"),
				"fieldname": "taxable_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 200,
			},
			{
				"label": _("VAT Amount"),
				"fieldname": "vat_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 200,
			},
			{
				"label": _("Currency"),
				"fieldname": "currency",
				"fieldtype": "Data",
				"width": 200,
				"hidden": 1,
			},
			{
				"label": _("Original CU Invoice Number"),
				"fieldname": "original_cu_invoice_number",
				"fieldtype": "Data",
				"width": 200,
			},
			{
				"label": _("Original CU Invoice Date"),
				"fieldname": "original_cu_invoice_date",
				"fieldtype": "Date",
				"width": 200,
			},
			{
				"label": _("Return Against"),
				"fieldname": "return_against",
				"fieldtype": "Link",
				"options": "Purchase Invoice",
				"width": 200,
			},
		]

		if self.filters.get("accounting_dimension"):
			dimension = self.filters.get("accounting_dimension")
			columns.insert(
				0,
				{
					"label": _(dimension),
					"fieldname": "accounting_dimension_value",
					"fieldtype": "Link",
					"options": dimension,
					"width": 200,
				},
			)

		return columns

	def get_report_summary(self):
		return [
			{
				"value": self.registered_suppliers_total_purchases,
				"indicator": "Green",
				"label": _("Registered Suppliers Total Purchases"),
				"datatype": "Currency",
				"currency": self.currency,
			},
			{
				"value": self.registered_suppliers_total_vat,
				"indicator": "Green",
				"label": _("Registered Suppliers Total VAT"),
				"datatype": "Currency",
				"currency": self.currency,
			},
			{
				"value": self.unregistered_suppliers_total_purchases,
				"indicator": "Green",
				"label": _("Unregistered Suppliers Total Purchases"),
				"datatype": "Currency",
				"currency": self.currency,
			},
			{
				"value": self.unregistered_suppliers_total_vat,
				"indicator": "Green",
				"label": _("Unregistered Suppliers Total VAT"),
				"datatype": "Currency",
				"currency": self.currency,
			},
		]


def _normalize_companies(company):
	if not company:
		return frappe.get_all("Company", pluck="name")

	if isinstance(company, str):
		company = company.strip()
		if not company:
			return frappe.get_all("Company", pluck="name")

		if company.startswith("["):
			try:
				parsed_companies = frappe.parse_json(company)
			except Exception:
				parsed_companies = None

			if isinstance(parsed_companies, list):
				return [item for item in parsed_companies if item]

		if "," in company:
			return [item.strip() for item in company.split(",") if item.strip()]

		return [company]

	if isinstance(company, (list, tuple, set)):
		return [item for item in company if item]

	return [company]


def _get_tax_templates_from_report_data(company, from_date=None, to_date=None):
	purchase_invoice_ = frappe.qb.DocType("Purchase Invoice")
	purchase_invoice_item_ = frappe.qb.DocType("Purchase Invoice Item")

	tax_templates_query = (
		frappe.qb.from_(purchase_invoice_item_)
		.inner_join(purchase_invoice_)
		.on(purchase_invoice_item_.parent == purchase_invoice_.name)
		.select(purchase_invoice_item_.item_tax_template)
		.distinct()
		.where(purchase_invoice_.docstatus == 1)
		.where(purchase_invoice_.company == company)
	)

	if from_date:
		tax_templates_query = tax_templates_query.where(purchase_invoice_.posting_date >= from_date)
	if to_date:
		tax_templates_query = tax_templates_query.where(purchase_invoice_.posting_date <= to_date)

	tax_template_rows = tax_templates_query.run(as_dict=True)
	return sorted({row.get("item_tax_template") for row in tax_template_rows if row.get("item_tax_template")})


@frappe.whitelist()
def download_custom_csv_format(company: str, from_date: str | None = None, to_date: str | None = None):
	if not from_date:
		frappe.throw(_("From Date is required"))
	if not to_date:
		frappe.throw(_("To Date is required"))

	from_date_str = from_date.strftime("%y-%m-%d") if isinstance(from_date, datetime) else from_date
	to_date_str = to_date.strftime("%y-%m-%d") if isinstance(to_date, datetime) else to_date

	private_path = frappe.utils.get_site_path("private", "files")
	os.makedirs(private_path, exist_ok=True)

	companies = _normalize_companies(company)
	if not companies:
		frappe.throw(_("At least one company is required"))

	csv_files = {}

	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

	for company_name in companies:
		tax_templates = _get_tax_templates_from_report_data(company_name, from_date, to_date)
		if not tax_templates:
			continue

		company_abbr = frappe.db.get_value("Company", company_name, "abbr") or ""

		for template_name in tax_templates:
			sanitized_template_name = re.sub(r"[^\w]+", "_", template_name).lower()

			csv_file_name = f"purchase_{sanitized_template_name[:20]}_{company_abbr}_{from_date_str}_to_{to_date_str}_{timestamp}.csv".strip(
				"_"
			)

			full_file_path = os.path.join(private_path, csv_file_name)
			file_url = f"/private/files/{csv_file_name}"

			purchase_invoices = KenyaPurchaseTaxReport(
				{
					"company": company_name,
					"from_date": from_date,
					"to_date": to_date,
					"item_tax_template": template_name,
				}
			).get_data("purchase")

			if not purchase_invoices:
				continue

			with open(full_file_path, "w", newline="") as csvfile:
				writer = csv.writer(csvfile)

				for invoice in purchase_invoices:
					if invoice.get("tax_id"):
						writer.writerow(
							[
								"Local",
								invoice.get("tax_id", ""),
								invoice.get("party_name", ""),
								(
									invoice.get("invoice_date").strftime("%d/%m/%Y")
									if invoice.get("invoice_date")
									else ""
								),
								f"|{(invoice.get('etr_invoice_number', ''))}",
								invoice.get("invoice_number", ""),
								"",
								invoice.get("taxable_amount", ""),
								"",
								f"{'|' + invoice.get('original_cu_invoice_number', '') if invoice.get('return_against') else ''}",
								(
									invoice.get("original_cu_invoice_date").strftime("%d/%m/%Y")
									if invoice.get("return_against")
									and invoice.get("original_cu_invoice_date")
									else ""
								),
							]
						)

			file_record = frappe.get_doc(
				{
					"doctype": "File",
					"file_name": csv_file_name,
					"file_url": file_url,
					"attached_to_name": company_name,
					"attached_to_doctype": "Purchase Invoice",
					"file_size": os.path.getsize(full_file_path),
					"is_private": 1,
					"file_type": "CSV",
				}
			)
			file_record.insert()

			display_key = f"{company_name} - {template_name}" if len(companies) > 1 else template_name
			csv_files[display_key] = file_url

	return csv_files
