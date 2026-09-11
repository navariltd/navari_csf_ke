# Copyright (c) 2026, Navari Limited and contributors
# For license information, please see license.txt

import os
from datetime import date
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from csf_ke.csf_ke.report.kenya_sales_tax_report import kenya_sales_tax_report as sales_report
from csf_ke.csf_ke.report.kenya_sales_tax_report.kenya_sales_tax_report import (
	KenyaSalesTaxReport,
	_build_sales_csv_row,
	_get_invoices_by_item_tax_template,
	_save_csv_file,
	download_custom_csv_format,
)

FILTERS = {"company": "_Test Company", "from_date": "2026-06-01", "to_date": "2026-06-30"}


def make_invoice(invoice_name, **overrides):
	invoice = {
		"pin_of_purchaser": "P051234567X",
		"name_of_purchaser": "Customer A",
		"invoice_date": date(2026, 6, 15),
		"invoice_name": invoice_name,
		"invoice_total_sales": 116.0,
		"return_against": None,
		"etims_id": None,
		"etr_serial_number": "KRACU0100000001",
		"etr_invoice_number": "0110000000000001",
		"cu_link": None,
		"cu_invoice_date": None,
	}
	invoice.update(overrides)
	return frappe._dict(invoice)


class TestSalesCsvRow(UnitTestCase):
	def test_row_keeps_the_existing_sales_columns(self):
		row = _build_sales_csv_row(make_invoice("SINV-1", taxable_value=100.0))

		self.assertEqual(
			row,
			[
				"P051234567X",
				"Customer A",
				"KRACU0100000001",
				"15/06/2026",
				"|0110000000000001",
				"SINV-1",
				100.0,
				"",
				"",
				"",
			],
		)

	def test_customer_without_pin_gets_no_row(self):
		self.assertIsNone(
			_build_sales_csv_row(make_invoice("SINV-1", pin_of_purchaser="", taxable_value=10.0))
		)

	def test_return_row_carries_original_cu_invoice(self):
		row = _build_sales_csv_row(
			make_invoice(
				"SINV-RET-1",
				taxable_value=-100.0,
				return_against="SINV-1",
				return_cu_invoice_number="0110000000000001",
				return_cu_invoice_date=date(2026, 6, 15),
			)
		)

		self.assertEqual(row[8:], ["|0110000000000001", "15/06/2026"])


class TestInvoicesByItemTaxTemplate(UnitTestCase):
	def test_invoices_split_per_template_with_their_own_amounts(self):
		report = KenyaSalesTaxReport(FILTERS)
		invoices = [make_invoice("SINV-1"), make_invoice("SINV-2")]
		items_by_invoice = {
			"SINV-1": [
				frappe._dict(taxable_value=100.0, item_tax_template="VAT 16% - TC"),
				frappe._dict(taxable_value=50.0, item_tax_template="Fuel 8% - TC"),
				frappe._dict(taxable_value=25.0, item_tax_template=None),
			],
			"SINV-2": [frappe._dict(taxable_value=0.0, item_tax_template="VAT 16% - TC")],
		}
		tax_rates = {"VAT 16% - TC": 16.0, "Fuel 8% - TC": 8.0}

		with (
			patch.object(report, "get_sales_invoices", return_value=invoices),
			patch.object(sales_report, "_get_items_by_invoice", return_value=items_by_invoice),
			patch.object(sales_report, "_get_item_tax_rate", side_effect=tax_rates.get) as get_item_tax_rate,
		):
			buckets, invoices_without_template = _get_invoices_by_item_tax_template(report)

		self.assertEqual(list(buckets), ["Fuel 8% - TC", "VAT 16% - TC"])
		(vat_invoice,) = buckets["VAT 16% - TC"]  # SINV-2 has no taxable value under this template
		(fuel_invoice,) = buckets["Fuel 8% - TC"]
		self.assertEqual(
			(vat_invoice["invoice_name"], vat_invoice["taxable_value"], vat_invoice["amount_of_vat"]),
			("SINV-1", 100.0, 16.0),
		)
		self.assertEqual((fuel_invoice["taxable_value"], fuel_invoice["amount_of_vat"]), (50.0, 4.0))
		self.assertEqual(invoices_without_template, {"SINV-1"})
		self.assertEqual(get_item_tax_rate.call_count, 2)  # once per template, not per item


class TestDownloadCustomCsvFormat(UnitTestCase):
	def test_templates_without_pin_rows_get_no_file_but_appear_in_summary(self):
		invoices_by_template = {
			"Exempt - TC": [
				make_invoice("SINV-2", pin_of_purchaser="", taxable_value=40.0, amount_of_vat=0.0)
			],
			"VAT 16% - TC": [make_invoice("SINV-1", taxable_value=100.0, amount_of_vat=16.0)],
		}
		saved_file = {"name": "file-1", "file_url": "/private/files/sales_vat.csv"}

		with (
			patch.object(
				sales_report,
				"_get_invoices_by_item_tax_template",
				return_value=(invoices_by_template, {"SINV-3"}),
			) as get_invoices,
			patch.object(sales_report, "_save_csv_file", return_value=saved_file) as save_csv_file,
		):
			result = download_custom_csv_format("_Test Company", "2026-06-01", "2026-06-30")

		get_invoices.assert_called_once()
		save_csv_file.assert_called_once()
		self.assertEqual([row[5] for row in save_csv_file.call_args.args[2]], ["SINV-1"])

		by_template = {row["item_tax_template"]: row for row in result["templates"]}
		self.assertEqual(by_template["VAT 16% - TC"]["file"], "file-1")
		self.assertEqual(by_template["VAT 16% - TC"]["invoice_count"], 1)
		self.assertIsNone(by_template["Exempt - TC"]["file_url"])
		self.assertEqual(result["totals"], {"invoice_count": 1, "taxable_amount": 100.0, "vat_amount": 16.0})
		self.assertEqual(
			result["skipped_no_pin"], {"invoice_count": 1, "taxable_amount": 40.0, "vat_amount": 0.0}
		)
		self.assertEqual(result["invoices_without_template"], 1)


class TestSaveCsvFile(UnitTestCase):
	def test_writes_one_private_csv_without_orphan_copies(self):
		prefix = f"sales_test_{frappe.generate_hash(length=8)}"
		private_path = frappe.utils.get_site_path("private", "files")

		saved = _save_csv_file("_Test Company", f"{prefix}.csv", [["P051234567X", "Customer, A"]])

		file_doc = frappe.get_doc("File", saved["name"])
		try:
			self.assertTrue(file_doc.is_private)
			self.assertEqual(file_doc.attached_to_doctype, "Sales Invoice")
			self.assertEqual(file_doc.get_content().strip(), 'P051234567X,"Customer, A"')
			self.assertEqual(
				[name for name in os.listdir(private_path) if name.startswith(prefix)],
				[os.path.basename(saved["file_url"])],
			)
		finally:
			file_doc.delete(ignore_permissions=True)
			for name in os.listdir(private_path):
				if name.startswith(prefix):
					os.remove(os.path.join(private_path, name))


class TestExportMatchesReportPerTemplate(UnitTestCase):
	"""The single-pass export must give the same rows the report gives when run once per template."""

	def test_single_pass_matches_report_run_per_template(self):
		busiest = frappe.db.sql(
			"""select company, min(posting_date), max(posting_date) from `tabSales Invoice`
			where docstatus = 1 group by company order by count(*) desc limit 1"""
		)
		if not busiest:
			self.skipTest("No submitted Sales Invoices on this site")

		company, from_date, to_date = busiest[0]
		filters = {"company": company, "from_date": str(from_date), "to_date": str(to_date)}
		buckets, _ = _get_invoices_by_item_tax_template(KenyaSalesTaxReport(filters))

		SI = frappe.qb.DocType("Sales Invoice")
		SII = frappe.qb.DocType("Sales Invoice Item")
		templates = (
			frappe.qb.from_(SII)
			.inner_join(SI)
			.on(SII.parent == SI.name)
			.select(SII.item_tax_template)
			.distinct()
			.where(SI.docstatus == 1)
			.where(SI.company == company)
			.where(SI.posting_date[from_date:to_date])
			.where(SII.item_tax_template.isnotnull())
			.run(pluck=True)
		)

		def comparable(invoices):
			return [
				(
					invoice["invoice_name"],
					round(invoice["taxable_value"], 6),
					round(invoice["amount_of_vat"], 6),
					_build_sales_csv_row({**invoice, "taxable_value": round(invoice["taxable_value"], 6)}),
				)
				for invoice in invoices
			]

		expected = {}
		for template in templates:
			rows = KenyaSalesTaxReport({**filters, "tax_template": template}).get_data()
			if rows:
				expected[template] = comparable(rows)

		self.assertEqual({template: comparable(rows) for template, rows in buckets.items()}, expected)
