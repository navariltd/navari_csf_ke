# Copyright (c) 2022, Navari Limited and contributors
# For license information, please see license.txt

import csv
import io
import re
from collections import defaultdict
from datetime import datetime
from typing import TypedDict

import frappe
from frappe import _

from csf_ke.csf_ke.utils.tax_report import TaxReport, add_amounts


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


def _group_rows_by_item_tax_template(rows):
	"""Bucket tax rows by their item's Item Tax Template, sorted by template name.

	Rows for items without an Item Tax Template are left out, as they were never exported.
	"""
	buckets = defaultdict(list)
	for row in rows:
		if row.get("item_tax_template"):
			buckets[row.get("item_tax_template")].append(row)

	return dict(sorted(buckets.items()))


def _format_date(value):
	return value.strftime("%d/%m/%Y") if value else ""


def _build_purchase_csv_row(invoice):
	"""Build one KRA purchases CSV row. Suppliers without a PIN are not filed, so they get no row."""
	if not invoice.get("tax_id"):
		return None

	return [
		"Local",
		invoice.get("tax_id", ""),
		invoice.get("party_name", ""),
		_format_date(invoice.get("supplier_invoice_date")),
		f"|{(invoice.get('etr_invoice_number', ''))}",
		invoice.get("supplier_invoice_no", ""),
		"",
		invoice.get("taxable_amount", ""),
		"",
		f"{'|' + invoice.get('original_cu_invoice_number', '') if invoice.get('return_against') else ''}",
		_format_date(invoice.get("original_cu_invoice_date")) if invoice.get("return_against") else "",
	]


def _save_csv_file(company_name, file_name, csv_rows):
	csv_content = io.StringIO()
	csv.writer(csv_content).writerows(csv_rows)

	# Hand the content to File so Frappe writes it once. Pre-writing to disk and passing
	# file_url made File.save_file store a hash-suffixed copy and orphan the original.
	file_record = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": file_name,
			"attached_to_name": company_name,
			"attached_to_doctype": "Purchase Invoice",
			"is_private": 1,
			"file_type": "CSV",
			"content": csv_content.getvalue(),
		}
	)
	file_record.insert()

	return {"name": file_record.name, "file_url": file_record.file_url}


@frappe.whitelist()
def download_custom_csv_format(company: str, from_date: str | None = None, to_date: str | None = None):
	if not from_date:
		frappe.throw(_("From Date is required"))
	if not to_date:
		frappe.throw(_("To Date is required"))

	from_date_str = from_date.strftime("%y-%m-%d") if isinstance(from_date, datetime) else from_date
	to_date_str = to_date.strftime("%y-%m-%d") if isinstance(to_date, datetime) else to_date

	companies = _normalize_companies(company)
	if not companies:
		frappe.throw(_("At least one company is required"))

	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
	templates = []
	skipped_no_pin = {"invoice_count": 0, "taxable_amount": 0.0, "vat_amount": 0.0}
	skipped_invoices = set()
	invoices_without_template = set()

	for company_name in companies:
		report = KenyaPurchaseTaxReport({"company": company_name, "from_date": from_date, "to_date": to_date})
		# One query per company; rows are split per Item Tax Template in Python
		rows = report.get_invoice_data("purchase", include_item_tax_template=True)
		if not rows:
			continue

		invoices_without_template.update(
			(company_name, row.get("invoice_number")) for row in rows if not row.get("item_tax_template")
		)
		company_abbr = frappe.db.get_value("Company", company_name, "abbr") or ""

		for template_name, template_rows in _group_rows_by_item_tax_template(rows).items():
			summary = {
				"company": company_name,
				"item_tax_template": template_name,
				"currency": None,
				"invoice_count": 0,
				"taxable_amount": 0.0,
				"vat_amount": 0.0,
				"file": None,
				"file_url": None,
			}
			csv_rows = []

			for invoice in report.process_invoice_data(template_rows, "purchase"):
				csv_row = _build_purchase_csv_row(invoice)
				if not csv_row:
					skipped_invoices.add((company_name, invoice.get("invoice_number")))
					skipped_no_pin["taxable_amount"] = add_amounts(
						skipped_no_pin["taxable_amount"], invoice.get("taxable_amount")
					)
					skipped_no_pin["vat_amount"] = add_amounts(
						skipped_no_pin["vat_amount"], invoice.get("vat_amount")
					)
					continue

				csv_rows.append(csv_row)
				summary["invoice_count"] += 1
				summary["taxable_amount"] = add_amounts(
					summary["taxable_amount"], invoice.get("taxable_amount")
				)
				summary["vat_amount"] = add_amounts(summary["vat_amount"], invoice.get("vat_amount"))

			summary["currency"] = report.currency

			# A template with no supplier PINs has nothing to file, so no empty CSV is created
			if csv_rows:
				sanitized_template_name = re.sub(r"[^\w]+", "_", template_name).lower()
				csv_file_name = f"purchase_{sanitized_template_name[:20]}_{company_abbr}_{from_date_str}_to_{to_date_str}_{timestamp}.csv".strip(
					"_"
				)
				saved_file = _save_csv_file(company_name, csv_file_name, csv_rows)
				summary["file"] = saved_file["name"]
				summary["file_url"] = saved_file["file_url"]

			templates.append(summary)

	skipped_no_pin["invoice_count"] = len(skipped_invoices)

	totals = {"invoice_count": 0, "taxable_amount": 0.0, "vat_amount": 0.0}
	for summary in templates:
		totals["invoice_count"] += summary["invoice_count"]
		totals["taxable_amount"] = add_amounts(totals["taxable_amount"], summary["taxable_amount"])
		totals["vat_amount"] = add_amounts(totals["vat_amount"], summary["vat_amount"])

	return {
		"from_date": from_date,
		"to_date": to_date,
		"timestamp": timestamp,
		"templates": templates,
		"totals": totals,
		"skipped_no_pin": skipped_no_pin,
		"invoices_without_template": len(invoices_without_template),
	}
