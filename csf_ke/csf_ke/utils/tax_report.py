from abc import ABC, abstractmethod

import frappe
from frappe import _
from frappe.utils import flt


class TaxReport(ABC):
	def __init__(self):
		self.registered_suppliers_total_purchases = 0.0
		self.registered_suppliers_total_vat = 0.0
		self.unregistered_suppliers_total_purchases = 0.0
		self.unregistered_suppliers_total_vat = 0.0
		self.currency = None

	@abstractmethod
	def get_columns(self):
		"""Return the report column definitions (names, labels, types)"""

	@abstractmethod
	def get_report_summary(self):
		"""Return the report summary"""

	def get_data(self, invoice_type):
		data = []
		invoice_data = self.get_invoice_data(invoice_type)
		if invoice_data:
			data = self.process_invoice_data(invoice_data, invoice_type)
		return data

	def get_invoice_data(self, invoice_type):
		INV = (
			frappe.qb.DocType("Sales Invoice")
			if invoice_type == "sales"
			else frappe.qb.DocType("Purchase Invoice")
		)
		INVI = (
			frappe.qb.DocType("Sales Invoice Item")
			if invoice_type == "sales"
			else frappe.qb.DocType("Purchase Invoice Item")
		)
		TD = frappe.qb.DocType("Item Wise Tax Detail")

		query = (
			frappe.qb.from_(TD)
			.inner_join(INV)
			.on(TD.parent == INV.name)
			.inner_join(INVI)
			.on((INVI.parent == INV.name) & (INVI.name == TD.item_row))
			.select(
				INV.supplier if invoice_type == "purchase" else INV.customer,
				INV.supplier_name if invoice_type == "purchase" else INV.customer_name,
				INV.tax_id,
				INV.name.as_("invoice_number"),
				INV.posting_date.as_("invoice_date"),
				INV.return_against,
				INV.etr_invoice_number,
				TD.item_row,
				TD.amount,
				TD.rate,
				TD.taxable_amount,
			)
			.where(INV.docstatus == 1)
			# .where(TD.rate != 0)
		)

		if invoice_type == "purchase":
			query = query.select(
				INV.bill_no.as_("supplier_invoice_no"),
				INV.bill_date.as_("supplier_invoice_date"),
			)

		if self.filters.get("company"):
			query = query.where(INV.company == self.filters.get("company"))

		if self.filters.get("from_date"):
			query = query.where(INV.posting_date >= self.filters.get("from_date"))

		if self.filters.get("to_date"):
			query = query.where(INV.posting_date <= self.filters.get("to_date"))

		if self.filters.get("item_tax_template"):
			query = query.where(INVI.item_tax_template == self.filters.get("item_tax_template"))

		if self.filters.get("taxes_and_charges_template"):
			query = query.where(INV.taxes_and_charges == self.filters.get("taxes_and_charges_template"))

		if self.filters.get("is_return"):
			query = query.where(INV.is_return == self.filters.get("is_return"))

		return query.run(as_dict=True)

	def process_invoice_data(self, invoice_data, invoice_type):
		self.currency = frappe.db.get_value("Company", self.filters.get("company"), "default_currency")
		party_field = "supplier" if invoice_type == "purchase" else "customer"
		party_name_field = "supplier_name" if invoice_type == "purchase" else "customer_name"

		invoice_map = {}
		seen_items = {}

		for row in invoice_data:
			invoice_number = row.get("invoice_number")
			item_row = row.get("item_row")

			if invoice_number not in invoice_map:
				invoice_map[invoice_number] = {
					"party": row.get(party_field),
					"party_name": row.get(party_name_field),
					"tax_id": row.get("tax_id"),
					"invoice_number": invoice_number,
					"invoice_date": row.get("invoice_date"),
					"return_against": row.get("return_against"),
					"supplier_invoice_no": row.get("supplier_invoice_no"),
					"supplier_invoice_date": row.get("supplier_invoice_date"),
					"etr_invoice_number": row.get("etr_invoice_number"),
					"taxable_amount": 0.0,
					"vat_amount": 0.0,
					"currency": self.currency,
				}
				seen_items[invoice_number] = set()

			invoice_map[invoice_number]["vat_amount"] += flt(row.get("amount", 0))

			if party_field == "supplier":
				if row.get("tax_id"):
					self.registered_suppliers_total_vat += flt(row.get("amount", 0))
				else:
					self.unregistered_suppliers_total_vat += flt(row.get("amount", 0))

			# Taxable amount is per item; only count it once when an item has
			# multiple tax rows (e.g. VAT + another charge on the same base).
			if item_row not in seen_items[invoice_number] and not (row.get("amount")) < 0:
				invoice_map[invoice_number]["taxable_amount"] += flt(row.get("taxable_amount", 0))
				seen_items[invoice_number].add(item_row)

				if party_field == "supplier":
					if row.get("tax_id"):
						self.registered_suppliers_total_purchases += flt(row.get("taxable_amount", 0))
					else:
						self.unregistered_suppliers_total_purchases += flt(row.get("taxable_amount", 0))

		return list(invoice_map.values())
