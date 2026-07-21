from abc import ABC, abstractmethod
from collections import defaultdict

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
			if self.filters.get("accounting_dimension") and data:
				data = self.group_by_dimension(data)
		return data

	def get_invoice_data(self, invoice_type):
		invoice_doctype = "Sales Invoice" if invoice_type == "sales" else "Purchase Invoice"
		item_doctype = f"{invoice_doctype} Item"
		INV = frappe.qb.DocType(invoice_doctype)
		INVI = frappe.qb.DocType(item_doctype)
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

		# TODO: handle invoice_type = sales

		query = self._select_accounting_dimension(query, INV, invoice_doctype)

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

	def _select_accounting_dimension(self, query, INV, invoice_doctype):
		accounting_dimension = self.filters.get("accounting_dimension")
		if not accounting_dimension:
			return query

		fieldname = frappe.scrub(accounting_dimension)
		if frappe.get_meta(invoice_doctype).has_field(fieldname):
			return query.select(getattr(INV, fieldname).as_("accounting_dimension_value"))

		return query

	def process_invoice_data(self, invoice_data, invoice_type):
		self.currency = frappe.db.get_value("Company", self.filters.get("company"), "default_currency")
		party_field = "supplier" if invoice_type == "purchase" else "customer"
		party_name_field = "supplier_name" if invoice_type == "purchase" else "customer_name"
		group_by_dimension = bool(self.filters.get("accounting_dimension"))

		invoice_map = {}
		seen_items = {}
		return_against_map = {}

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

				if row.get("return_against"):
					return_against_map[row.get("return_against")] = {
						"invoice_number": row.get("return_against"),
					}

				if group_by_dimension:
					invoice_map[invoice_number]["accounting_dimension_value"] = row.get(
						"accounting_dimension_value"
					)
				seen_items[invoice_number] = set()

			invoice_map[invoice_number]["vat_amount"] += flt(row.get("amount", 0))

			if party_field == "supplier":
				if row.get("tax_id"):
					self.registered_suppliers_total_vat += flt(row.get("amount", 0))
				else:
					self.unregistered_suppliers_total_vat += flt(row.get("amount", 0))

			# Taxable amount is per item; only count it once when an item has
			# multiple tax rows (e.g. VAT + another charge on the same base).
			if (
				item_row not in seen_items[invoice_number]
				# and not (row.get("amount")) == 0
			):
				invoice_map[invoice_number]["taxable_amount"] += flt(row.get("taxable_amount", 0))
				seen_items[invoice_number].add(item_row)

				if party_field == "supplier":
					if row.get("tax_id"):
						self.registered_suppliers_total_purchases += flt(row.get("taxable_amount", 0))
					else:
						self.unregistered_suppliers_total_purchases += flt(row.get("taxable_amount", 0))

		if invoice_type == "purchase":
			INV = frappe.qb.DocType("Purchase Invoice")
			if return_against_map:
				query = (
					frappe.qb.from_(INV)
					.select(
						INV.name,
						INV.etr_invoice_number,
						INV.bill_date,
						INV.posting_date,
					)
					.where(INV.name.isin(list(return_against_map.keys())))
					.where(INV.etr_invoice_number.isnotnull())
				)
				data = query.run(as_dict=True)
				for row in data:
					return_against_map[row.name] = {
						"original_cu_invoice_number": row.etr_invoice_number,
						"original_cu_invoice_date": row.get("bill_date", row.get("posting_date")),
					}

			if invoice_map and return_against_map:
				for __, invoice_data in invoice_map.items():
					if (
						invoice_data.get("return_against")
						and return_against_map.get(invoice_data.get("return_against"))
						and return_against_map.get(invoice_data.get("return_against")).get(
							"original_cu_invoice_number"
						)
					):
						invoice_data["original_cu_invoice_number"] = return_against_map[
							invoice_data.get("return_against")
						].get("original_cu_invoice_number")
						invoice_data["original_cu_invoice_date"] = return_against_map[
							invoice_data.get("return_against")
						].get("original_cu_invoice_date")

		# TODO: handle invoice_type = sales

		return list(invoice_map.values())

	def group_by_dimension(self, data):
		"""Group rows by accounting dimension with header totals per group."""
		grouped_data = defaultdict(list)
		for row in data:
			dimension_value = row.get("accounting_dimension_value") or _("No Dimension")
			# row["accounting_dimension_value"] = dimension_value
			grouped_data[dimension_value].append(row)

		final_data = []
		for dimension_value in sorted(grouped_data.keys()):
			group_rows = grouped_data[dimension_value]
			final_data.append(
				{
					"accounting_dimension_value": dimension_value,
					"party_name": None,
					"taxable_amount": sum(flt(row.get("taxable_amount")) for row in group_rows),
					"vat_amount": sum(flt(row.get("vat_amount")) for row in group_rows),
					"currency": self.currency,
					"is_group_header": True,
				}
			)
			for row in group_rows:
				row["indent"] = 1
				final_data.append(row)

		return final_data
