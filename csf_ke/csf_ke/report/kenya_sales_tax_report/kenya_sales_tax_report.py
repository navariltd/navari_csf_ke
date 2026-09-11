# Copyright (c) 2022, Navari Limited and contributors
# For license information, please see license.txt

import csv
import io
import re
from collections import defaultdict
from datetime import datetime

import frappe
from frappe import _
from frappe.utils import flt

from csf_ke.csf_ke.utils.tax_report import add_amounts


def execute(filters=None):
	return KenyaSalesTaxReport(filters).run()


class KenyaSalesTaxReport:
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
		columns = []

		if self.filters.get("accounting_dimension"):
			dimension_label = self.filters.get("accounting_dimension")
			columns.append(
				{
					"label": _(dimension_label),
					"fieldname": "accounting_dimension_value",
					"fieldtype": "Link",
					"options": dimension_label,
					"width": 180,
				}
			)

		columns += [
			{
				"label": _("PIN of purchaser"),
				"fieldname": "pin_of_purchaser",
				"fieldtype": "Data",
				"width": 160,
			},
			{
				"label": _("Name of purchaser"),
				"fieldname": "name_of_purchaser",
				"fieldtype": "Data",
				"width": 240,
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
				"options": "Sales Invoice",
				"width": 200,
			},
			{
				"label": _("SCU Serial Number"),
				"fieldname": "etr_serial_number",
				"fieldtype": "Data",
				"width": 200,
			},
			{
				"label": _("SCU Invoice Number"),
				"fieldname": "etr_invoice_number",
				"fieldtype": "Data",
				"width": 200,
			},
			{
				"fieldname": "cu_link",
				"label": _("SCU Link"),
				"fieldtype": "Data",
				"width": 200,
			},
			{
				"label": _("SCU Invoice Date"),
				"fieldname": "cu_invoice_date",
				"fieldtype": "Date",
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
				"label": _("Return Against SCU Number"),
				"fieldname": "return_cu_invoice_number",
				"fieldtype": "Data",
				"width": 250,
			},
			{
				"label": _("Return Against SCU Invoice Date"),
				"fieldname": "return_cu_invoice_date",
				"fieldtype": "Date",
				"width": 250,
			},
		]

		if self.filters.is_return == "Is Return":
			columns += [
				{
					"label": _("Return Against"),
					"fieldname": "return_against",
					"fieldtype": "Link",
					"options": "Sales Invoice",
					"width": 200,
				}
			]

		return columns

	def get_sales_invoices(self):
		company = self.filters.company
		from_date = self.filters.from_date
		to_date = self.filters.to_date
		is_return = self.filters.is_return

		sale_invoice_doc = frappe.qb.DocType("Sales Invoice")
		customer_doc = frappe.qb.DocType("Customer")

		select_fields = [
			sale_invoice_doc.tax_id.as_("pin_of_purchaser"),
			sale_invoice_doc.customer_name.as_("name_of_purchaser"),
			sale_invoice_doc.posting_date.as_("invoice_date"),
			sale_invoice_doc.name.as_("invoice_name"),
			sale_invoice_doc.base_grand_total.as_("invoice_total_sales"),
			sale_invoice_doc.return_against.as_("return_against"),
			sale_invoice_doc.etims_id.as_("etims_id"),
			sale_invoice_doc.etr_serial_number.as_("etr_serial_number"),
			sale_invoice_doc.etr_invoice_number.as_("etr_invoice_number"),
			sale_invoice_doc.cu_link.as_("cu_link"),
			sale_invoice_doc.cu_invoice_date.as_("cu_invoice_date"),
		]

		accounting_dimension = self.filters.get("accounting_dimension")
		if accounting_dimension:
			dimension_field_map = {"Cost Center": "cost_center", "Project": "project"}
			dimension_field = dimension_field_map.get(accounting_dimension)
			if dimension_field:
				select_fields.append(
					getattr(sale_invoice_doc, dimension_field).as_("accounting_dimension_value")
				)

		sales_invoice_query = (
			frappe.qb.from_(sale_invoice_doc)
			.inner_join(customer_doc)
			.on(sale_invoice_doc.customer == customer_doc.name)
			.select(*select_fields)
			.where(sale_invoice_doc.docstatus == 1)
		)

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

		for invoice in sales_invoices:
			if invoice.get("etims_id"):
				ledger = frappe.db.get_value(
					"eTIMS Sales Ledger Entry",
					{"etims_id": invoice.etims_id},
					[
						"scu_id",
						"scu_invoice_number",
						"scu_mrc_number",
						"scu_receipt_number",
						"etims_qr_code_url",
						"invoice_date",
					],
					as_dict=True,
				)
				if ledger:
					invoice["etr_serial_number"] = ledger.get("scu_id")
					invoice["etr_invoice_number"] = ledger.get("scu_invoice_number")
					invoice["cu_link"] = ledger.get("etims_qr_code_url")
					invoice["cu_invoice_date"] = ledger.get("invoice_date")

			if invoice.get("return_against"):
				return_invoice = frappe.db.get_value(
					"Sales Invoice",
					invoice["return_against"],
					["etims_id", "etr_invoice_number", "cu_invoice_date"],
					as_dict=True,
				)
				if return_invoice:
					if return_invoice.get("etims_id"):
						return_ledger = frappe.db.get_value(
							"eTIMS Sales Ledger Entry",
							{"etims_id": return_invoice.etims_id},
							["scu_invoice_number", "invoice_date"],
							as_dict=True,
						)
						if return_ledger:
							invoice["return_cu_invoice_number"] = return_ledger.get("scu_invoice_number")
							invoice["return_cu_invoice_date"] = return_ledger.get("invoice_date")
					elif return_invoice.get("etr_invoice_number"):
						invoice["return_cu_invoice_number"] = return_invoice.get("etr_invoice_number")
						invoice["return_cu_invoice_date"] = return_invoice.get("cu_invoice_date")

		return sales_invoices

	def get_sales_invoice_items(self, sales_invoice_name, tax_template=None):
		sales_invoice_item_doc = frappe.qb.DocType("Sales Invoice Item")
		sales_invoice_items_query = (
			frappe.qb.from_(sales_invoice_item_doc)
			.select(
				sales_invoice_item_doc.amount.as_("amount"),
				sales_invoice_item_doc.base_net_amount.as_("taxable_value"),
				sales_invoice_item_doc.item_tax_template.as_("item_tax_template"),
			)
			.where(sales_invoice_item_doc.parent == sales_invoice_name)
		)

		if tax_template:
			sales_invoice_items_query = sales_invoice_items_query.where(
				sales_invoice_item_doc.item_tax_template == tax_template
			)

		items_or_services = sales_invoice_items_query.run(as_dict=True)
		return items_or_services

	def get_data(self):
		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("To Date cannot be before From Date. {}").format(self.filters.to_date))
		report_details = []

		sales_invoices = self.get_sales_invoices()

		for sales_invoice in sales_invoices:
			items_or_services = self.get_sales_invoice_items(
				sales_invoice.invoice_name, self.filters.tax_template
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

			sales_invoice["taxable_value"] = total_taxable_value
			sales_invoice["amount_of_vat"] = total_vat

			if total_taxable_value:
				report_details.append(sales_invoice)

		for report_entry in report_details:
			if report_entry["pin_of_purchaser"]:
				self.registered_customers_total_sales += report_entry["invoice_total_sales"]
				self.registered_customers_total_vat += report_entry["amount_of_vat"]
			else:
				self.unregistered_customers_total_sales += report_entry["invoice_total_sales"]
				self.unregistered_customers_total_vat += report_entry["amount_of_vat"]

		if self.filters.get("accounting_dimension") and report_details:
			report_details = self.group_by_dimension(report_details)

		return report_details

	def group_by_dimension(self, data):
		grouped_data = defaultdict(list)
		for row in data:
			dimension_value = row.get("accounting_dimension_value") or _("No Dimension")
			grouped_data[dimension_value].append(row)

		final_data = []
		for dimension_value in sorted(grouped_data.keys()):
			group_rows = grouped_data[dimension_value]

			group_taxable_value = sum(row.get("taxable_value", 0) for row in group_rows)
			group_amount_of_vat = sum(row.get("amount_of_vat", 0) for row in group_rows)

			group_header = {
				"accounting_dimension_value": dimension_value,
				"taxable_value": group_taxable_value,
				"amount_of_vat": group_amount_of_vat,
				"is_group_header": True,
			}
			final_data.append(group_header)

			for row in group_rows:
				row["indent"] = 1
				final_data.append(row)

		return final_data

	def get_report_summary(self):
		return [
			{
				"value": self.registered_customers_total_sales,
				"indicator": "Green",
				"label": _("Registered customers total sales"),
				"datatype": "Currency",
				"currency": "KES",
			},
			{
				"value": self.registered_customers_total_vat,
				"indicator": "Green",
				"label": _("Registered customers total VAT"),
				"datatype": "Currency",
				"currency": "KES",
			},
			{
				"value": self.unregistered_customers_total_sales,
				"indicator": "Green",
				"label": _("Unregistered customers total sales"),
				"datatype": "Currency",
				"currency": "KES",
			},
			{
				"value": self.unregistered_customers_total_vat,
				"indicator": "Green",
				"label": _("Unregistered customers total VAT"),
				"datatype": "Currency",
				"currency": "KES",
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


def _get_items_by_invoice(invoice_names):
	sales_invoice_item = frappe.qb.DocType("Sales Invoice Item")
	items = (
		frappe.qb.from_(sales_invoice_item)
		.select(
			sales_invoice_item.parent,
			sales_invoice_item.base_net_amount.as_("taxable_value"),
			sales_invoice_item.item_tax_template,
		)
		.where(sales_invoice_item.parent.isin(invoice_names))
		.run(as_dict=True)
	)

	items_by_invoice = defaultdict(list)
	for item in items:
		items_by_invoice[item.parent].append(item)

	return items_by_invoice


def _get_item_tax_rate(item_tax_template):
	# Same lookup get_data does for every item
	return frappe.db.get_value("Item Tax Template Detail", {"parent": item_tax_template}, ["tax_rate"])


def _get_invoices_by_item_tax_template(report):
	"""Split the report's invoices per Item Tax Template in one pass.

	Gives the same invoices and amounts as running the report once per template (get_data with
	tax_template), without re-querying every invoice, item and tax rate for each template.
	"""
	invoices = report.get_sales_invoices()
	if not invoices:
		return {}, set()

	items_by_invoice = _get_items_by_invoice([invoice.invoice_name for invoice in invoices])
	tax_rates = {}
	invoices_by_template = defaultdict(list)
	invoices_without_template = set()

	for invoice in invoices:
		amounts_by_template = {}
		for item in items_by_invoice.get(invoice.invoice_name, []):
			template = item.get("item_tax_template")
			if not template:
				invoices_without_template.add(invoice.invoice_name)
				continue

			if template not in tax_rates:
				tax_rates[template] = _get_item_tax_rate(template)
			tax_rate = tax_rates[template]
			item_vat = flt(item.get("taxable_value")) * (tax_rate / 100) if tax_rate else 0

			taxable_value, amount_of_vat = amounts_by_template.get(template, (0.0, 0.0))
			amounts_by_template[template] = (
				add_amounts(taxable_value, item.get("taxable_value")),
				add_amounts(amount_of_vat, item_vat),
			)

		for template, (taxable_value, amount_of_vat) in amounts_by_template.items():
			# get_data leaves out invoices with no taxable value under the template
			if taxable_value:
				invoices_by_template[template].append(
					frappe._dict(invoice, taxable_value=taxable_value, amount_of_vat=amount_of_vat)
				)

	return dict(sorted(invoices_by_template.items())), invoices_without_template


def _format_date(value):
	return value.strftime("%d/%m/%Y") if value else ""


def _build_sales_csv_row(invoice):
	"""Build one KRA sales CSV row. Customers without a PIN are not filed, so they get no row."""
	if not invoice.get("pin_of_purchaser"):
		return None

	return [
		invoice.get("pin_of_purchaser", ""),
		invoice.get("name_of_purchaser", ""),
		invoice.get("etr_serial_number", ""),
		_format_date(invoice.get("invoice_date")),
		f"|{(invoice.get('etr_invoice_number', ''))}",
		invoice.get("invoice_name", ""),
		invoice.get("taxable_value", ""),
		"",
		f"|{invoice.get('return_cu_invoice_number', '')}" if invoice.get("return_against") else "",
		_format_date(invoice.get("return_cu_invoice_date")) if invoice.get("return_against") else "",
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
			"attached_to_doctype": "Sales Invoice",
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
		report = KenyaSalesTaxReport({"company": company_name, "from_date": from_date, "to_date": to_date})
		invoices_by_template, company_invoices_without_template = _get_invoices_by_item_tax_template(report)
		invoices_without_template.update((company_name, name) for name in company_invoices_without_template)
		if not invoices_by_template:
			continue

		company_abbr, currency = frappe.db.get_value(
			"Company", company_name, ["abbr", "default_currency"]
		) or ("", None)

		for template_name, invoices in invoices_by_template.items():
			summary = {
				"company": company_name,
				"item_tax_template": template_name,
				"currency": currency,
				"invoice_count": 0,
				"taxable_amount": 0.0,
				"vat_amount": 0.0,
				"file": None,
				"file_url": None,
			}
			csv_rows = []

			for invoice in invoices:
				csv_row = _build_sales_csv_row(invoice)
				if not csv_row:
					skipped_invoices.add((company_name, invoice.get("invoice_name")))
					skipped_no_pin["taxable_amount"] = add_amounts(
						skipped_no_pin["taxable_amount"], invoice.get("taxable_value")
					)
					skipped_no_pin["vat_amount"] = add_amounts(
						skipped_no_pin["vat_amount"], invoice.get("amount_of_vat")
					)
					continue

				csv_rows.append(csv_row)
				summary["invoice_count"] += 1
				summary["taxable_amount"] = add_amounts(
					summary["taxable_amount"], invoice.get("taxable_value")
				)
				summary["vat_amount"] = add_amounts(summary["vat_amount"], invoice.get("amount_of_vat"))

			# A template with no customer PINs has nothing to file, so no empty CSV is created
			if csv_rows:
				sanitized_template_name = re.sub(r"[^\w]+", "_", template_name).lower()
				csv_file_name = f"sales_{sanitized_template_name[:20]}_{company_abbr}_{from_date_str}_to_{to_date_str}_{timestamp}.csv".strip(
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
