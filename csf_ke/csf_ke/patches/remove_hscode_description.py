import frappe


def execute():
	frappe.delete_doc("Custom Field", "Delivery Note Item-custom_tims_hscode", force=True)
	frappe.delete_doc("Custom Field", "Sales Invoice Item-custom_tims_hscode", force=True)
	frappe.delete_doc("Custom Field", "Purchase Receipt Item-custom_tims_hscode", force=True)
	frappe.delete_doc("Custom Field", "Purchase Invoice Item-custom_tims_hscode", force=True)
	frappe.delete_doc("Custom Field", "Item Tax-custom_description", force=True)
	frappe.delete_doc("Custom Field", "Item Tax-custom_section_break_k5uid", force=True)
