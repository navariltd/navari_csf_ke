# Copyright (c) 2026, Navari Limited and contributors
# For license information, please see license.txt

import os
from datetime import date
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from csf_ke.csf_ke.report.kenya_purchase_tax_report import kenya_purchase_tax_report as purchase_report
from csf_ke.csf_ke.report.kenya_purchase_tax_report.kenya_purchase_tax_report import (
	KenyaPurchaseTaxReport,
	_build_purchase_csv_row,
	_group_rows_by_item_tax_template,
	_save_csv_file,
	download_custom_csv_format,
)

FILTERS = {"company": "_Test Company", "from_date": "2026-06-01", "to_date": "2026-06-30"}


def make_row(invoice_number, item_row, taxable_amount, amount, **overrides):
	row = {
		"supplier": "Supplier A",
		"supplier_name": "Supplier A",
		"tax_id": "P051234567X",
		"invoice_number": invoice_number,
		"invoice_date": date(2026, 6, 1),
		"return_against": None,
		"etr_invoice_number": "0110164930000181256",
		"item_row": item_row,
		"amount": amount,
		"rate": 16,
		"taxable_amount": taxable_amount,
		"supplier_invoice_no": "BILL-001",
		"supplier_invoice_date": date(2026, 6, 5),
		"item_tax_template": "VAT 16% - TC",
	}
	row.update(overrides)
	return frappe._dict(row)


class TestPurchaseQueryDateField(UnitTestCase):
	def test_purchase_query_filters_on_bill_date(self):
		sql = KenyaPurchaseTaxReport(FILTERS).build_invoice_query("purchase").get_sql()

		self.assertRegex(sql, r"bill_date`?>='2026-06-01'")
		self.assertRegex(sql, r"bill_date`?<='2026-06-30'")
		self.assertNotRegex(sql, r"posting_date`?[<>]=")

	def test_sales_branch_still_filters_on_posting_date(self):
		sql = KenyaPurchaseTaxReport(FILTERS).build_invoice_query("sales").get_sql()

		self.assertRegex(sql, r"posting_date`?>='2026-06-01'")
		self.assertNotRegex(sql, r"bill_date")

	def test_item_tax_template_is_selected_only_on_request(self):
		report = KenyaPurchaseTaxReport(FILTERS)

		self.assertNotIn("item_tax_template", report.build_invoice_query("purchase").get_sql())
		self.assertIn(
			"item_tax_template",
			report.build_invoice_query("purchase", include_item_tax_template=True).get_sql(),
		)


class TestPurchaseAmounts(UnitTestCase):
	def test_amounts_add_up_without_float_drift(self):
		taxable_amounts = [1034.48, 862.07, 215.52, 431.03, 86.21, 1293.1]
		rows = [make_row("PI-1", f"row-{i}", value, 0) for i, value in enumerate(taxable_amounts)]

		(invoice,) = KenyaPurchaseTaxReport(FILTERS).process_invoice_data(rows, "purchase")

		self.assertEqual(repr(invoice["taxable_amount"]), "3922.41")


class TestPurchaseCsvRow(UnitTestCase):
	def test_row_uses_supplier_invoice_date_and_number(self):
		row = _build_purchase_csv_row(
			{
				"tax_id": "P051234567X",
				"party_name": "Supplier A",
				"invoice_number": "CL-PI-01796",
				"invoice_date": date(2026, 6, 1),
				"supplier_invoice_no": "69763",
				"supplier_invoice_date": date(2026, 6, 5),
				"etr_invoice_number": "0110391230000005114",
				"taxable_amount": 1500.0,
			}
		)

		self.assertEqual(row[3], "05/06/2026")  # column D
		self.assertEqual(row[4], "|0110391230000005114")  # column E
		self.assertEqual(row[5], "69763")  # column F
		self.assertEqual(row[7], 1500.0)  # column H

	def test_supplier_without_pin_gets_no_row(self):
		self.assertIsNone(_build_purchase_csv_row({"tax_id": None, "taxable_amount": 10.0}))

	def test_return_row_carries_original_cu_invoice(self):
		row = _build_purchase_csv_row(
			{
				"tax_id": "P051234567X",
				"supplier_invoice_no": "70506304",
				"supplier_invoice_date": date(2026, 9, 10),
				"etr_invoice_number": "0110164930000181256",
				"taxable_amount": -100.0,
				"return_against": "CL-PI-01667",
				"original_cu_invoice_number": "0110164930000170000",
				"original_cu_invoice_date": date(2026, 8, 20),
			}
		)

		self.assertEqual(row[9], "|0110164930000170000")
		self.assertEqual(row[10], "20/08/2026")


class TestGroupRowsByItemTaxTemplate(UnitTestCase):
	def test_items_split_into_their_own_template_buckets(self):
		rows = [
			make_row("PI-1", "r1", 100.0, 16.0, item_tax_template="VAT 16% - TC"),
			make_row("PI-1", "r2", 50.0, 4.0, item_tax_template="Fuel 8% - TC"),
			make_row("PI-2", "r3", 10.0, 0.0, item_tax_template=None),
		]

		buckets = _group_rows_by_item_tax_template(rows)

		self.assertEqual(list(buckets), ["Fuel 8% - TC", "VAT 16% - TC"])
		report = KenyaPurchaseTaxReport(FILTERS)
		(vat_invoice,) = report.process_invoice_data(buckets["VAT 16% - TC"], "purchase")
		(fuel_invoice,) = report.process_invoice_data(buckets["Fuel 8% - TC"], "purchase")
		self.assertEqual((vat_invoice["taxable_amount"], vat_invoice["vat_amount"]), (100.0, 16.0))
		self.assertEqual((fuel_invoice["taxable_amount"], fuel_invoice["vat_amount"]), (50.0, 4.0))


class TestDownloadCustomCsvFormat(UnitTestCase):
	def test_templates_without_pin_rows_get_no_file_but_appear_in_summary(self):
		rows = [
			make_row("PI-1", "r1", 100.0, 16.0, item_tax_template="VAT 16% - TC"),
			make_row("PI-2", "r2", 40.0, 3.2, item_tax_template="Fuel 8% - TC", tax_id=None),
			make_row("PI-3", "r3", 25.0, 4.0, item_tax_template=None),
		]
		saved_file = {"name": "file-1", "file_url": "/private/files/purchase_vat.csv"}

		with (
			patch.object(KenyaPurchaseTaxReport, "get_invoice_data", return_value=rows) as get_invoice_data,
			patch.object(purchase_report, "_save_csv_file", return_value=saved_file) as save_csv_file,
		):
			result = download_custom_csv_format("_Test Company", "2026-06-01", "2026-06-30")

		get_invoice_data.assert_called_once_with("purchase", include_item_tax_template=True)
		save_csv_file.assert_called_once()
		saved_rows = save_csv_file.call_args.args[2]
		self.assertEqual([row[5] for row in saved_rows], ["BILL-001"])

		by_template = {row["item_tax_template"]: row for row in result["templates"]}
		self.assertEqual(by_template["VAT 16% - TC"]["file"], "file-1")
		self.assertEqual(by_template["VAT 16% - TC"]["invoice_count"], 1)
		self.assertEqual(by_template["VAT 16% - TC"]["taxable_amount"], 100.0)
		self.assertIsNone(by_template["Fuel 8% - TC"]["file_url"])
		self.assertEqual(by_template["Fuel 8% - TC"]["invoice_count"], 0)
		self.assertEqual(
			result["skipped_no_pin"], {"invoice_count": 1, "taxable_amount": 40.0, "vat_amount": 3.2}
		)
		self.assertEqual(result["invoices_without_template"], 1)
		self.assertEqual(result["totals"], {"invoice_count": 1, "taxable_amount": 100.0, "vat_amount": 16.0})


class TestSaveCsvFile(UnitTestCase):
	def test_writes_one_private_csv_without_orphan_copies(self):
		prefix = f"purchase_test_{frappe.generate_hash(length=8)}"
		private_path = frappe.utils.get_site_path("private", "files")

		saved = _save_csv_file("_Test Company", f"{prefix}.csv", [["Local", "P051234567X", "Supplier, A"]])

		file_doc = frappe.get_doc("File", saved["name"])
		try:
			self.assertTrue(file_doc.is_private)
			self.assertTrue(saved["file_url"].startswith(f"/private/files/{prefix}"))
			self.assertEqual(file_doc.get_content().strip(), 'Local,P051234567X,"Supplier, A"')
			self.assertEqual(
				[name for name in os.listdir(private_path) if name.startswith(prefix)],
				[os.path.basename(saved["file_url"])],
			)
		finally:
			file_doc.delete(ignore_permissions=True)
			for name in os.listdir(private_path):
				if name.startswith(prefix):
					os.remove(os.path.join(private_path, name))
