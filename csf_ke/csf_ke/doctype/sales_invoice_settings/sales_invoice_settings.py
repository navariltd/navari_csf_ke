# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class SalesInvoiceSettings(Document):
	
	def before_save(self):
		self.toggle_item_code_mandatory()

	def toggle_item_code_mandatory(self):
		"""Toggle the 'reqd' property of item_code in Sales Invoice Item based on set_item_code_mandatory."""
		DOCTYPE = "Sales Invoice Item"
		FIELD_NAME = "item_code"
		PROPERTY = "reqd"
		PROPERTY_TYPE = "Check"
		VALUE = "1" if self.set_item_code_mandatory else "0"

		field_filters = {
			"doctype_or_field": "DocField",
			"doc_type": DOCTYPE,
			"field_name": FIELD_NAME,
			"property": PROPERTY,
			"property_type": PROPERTY_TYPE
		}

		existing_property = frappe.db.exists("Property Setter", field_filters)

		try:
			if self.set_item_code_mandatory:
				if existing_property:
				
					frappe.db.set_value("Property Setter", field_filters, "value", VALUE, update_modified=False)

				else:

					frappe.get_doc({
						"doctype": "Property Setter",
						"doctype_or_field": "DocField",
						"doc_type": DOCTYPE,
						"field_name": FIELD_NAME,
						"property": PROPERTY,
						"property_type": PROPERTY_TYPE,
						"value": VALUE
					}).insert(ignore_permissions=True)

			elif existing_property:
				frappe.delete_doc("Property Setter", existing_property, ignore_permissions=True)

			frappe.db.commit()

		except Exception as e:
			frappe.log_error(f"Error updating Property Setter: {str(e)[:135]}")