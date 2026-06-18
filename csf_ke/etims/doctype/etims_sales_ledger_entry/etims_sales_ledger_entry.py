# Copyright (c) 2026, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class eTIMSSalesLedgerEntry(Document):
	def validate(self):
		self.link_related_document()

	def link_related_document(self):
		if not self.reference_number:
			return

		base_ref = self.reference_number.split("-REV")[0]
		existing_inv = frappe.db.get_value("Sales Invoice", {"name": base_ref, "is_return": 0})
		if existing_inv:
			self.sales_invoice = existing_inv

		if self.type == "Credit Note" and self.etims_invoice:
			sales_invoice = frappe.db.get_value(
				"eTIMS Sales Ledger Entry",
				self.etims_invoice,
				"sales_invoice",
				cache=True,
			)
			if sales_invoice:
				self.sales_invoice = sales_invoice

		if self.sales_invoice:
			company = frappe.db.get_value("Sales Invoice", self.sales_invoice, "company")
			self.company = company
