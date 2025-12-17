# Copyright (c) 2024, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class SellingItemPriceMargin(Document):
	def before_save(self):
		self.check_date_overlap()
		self.validate_margin_field()

	def on_update(self):
		self.check_date_overlap()
		self.validate_margin_field()

	def on_update_after_submit(self):
		self.check_date_overlap()
		self.validate_margin_field()

	def validate_margin_field(self):
		if self.margin_type == "Amount":
			if self.margin_percentage_or_amount < 0:
				frappe.throw(_("Margin Amount cannot be negative."))

		elif self.margin_type == "Percentage":
			if self.margin_percentage_or_amount < 0 or self.margin_percentage_or_amount > 100:
				frappe.throw(_("Margin Percentage must be between 0 and 100."))

	def check_date_overlap(self):
		item_codes = [item.item_code for item in self.items]
		duplicate_items = [item for item in set(item_codes) if item_codes.count(item) > 1]

		if duplicate_items:
			frappe.throw(
				title=_("Duplicate Items"),
				msg=_("{0}").format(", ".join(duplicate_items)),
				exc=frappe.DuplicateEntryError,
			)

		existing_records = frappe.get_all(
			"Selling Item Price Margin",
			filters={
				"docstatus": 1,
				"disabled": 0,
				"selling_price": self.selling_price,
				"name": ("!=", self.name),
				"start_date": ("<=", self.start_date),
				"end_date": (">=", self.end_date),
			},
			fields=["name", "selling_price", "start_date", "end_date"],
		)

		items = [item.item_code for item in self.items if self.items]

		for record in existing_records:
			sipm = frappe.get_doc("Selling Item Price Margin", record.name)

			for item in sipm.items:
				if item.item_code in items:
					overlap_details = _("Selling price: {0} (From: {1}, To: {2})").format(
						record["selling_price"], record["start_date"], record["end_date"]
					)
					frappe.throw(
						f"Item '{item.item_code}' already exists in another record with the same selling price. Date overlap:\n{overlap_details}"
					)
				else:
					continue
