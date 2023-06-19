import frappe

def execute():
    # Delete the custom fields
    frappe.delete_doc("Custom Field", "Employee-column_break_84", force=True)
    frappe.delete_doc("Custom Field", "Employee-section_break_87", force=True)
