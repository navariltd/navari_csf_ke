import frappe
from frappe import _


def validate_mandatory_hscode(doc, method):
	"""
	Validate that the TIMs HSCode field is filled if an Item Tax Template is linked.
	"""
	for tax in doc.taxes:
		if tax.item_tax_template:
			hscodes = frappe.get_all(
				"TIMs HSCode", filters={"item_tax": tax.item_tax_template}, fields=["name", "tims_hscode"]
			)

			if hscodes and not tax.tims_hscode:
				fieldname = "tims_hscode"
				message = _("TIMs HSCode is mandatory for Item Tax Template {0}.").format(
					frappe.bold(tax.item_tax_template), fieldname
				)

				frappe.throw(message, title=_("Missing TIMs HSCode"))
