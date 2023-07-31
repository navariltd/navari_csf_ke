import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():

    # Had created these fields in previous patches, delete to clear employee doctype
    frappe.delete_doc("Custom Field", "Employee-column_break_84", force=True)
    frappe.delete_doc("Custom Field", "Employee-section_break_87", force=True)
    frappe.delete_doc("Custom Field", "Employee-column_break_statutory_details_01", force=True)
    frappe.delete_doc("Custom Field", "Employee-section_break_statutory_details_01", force=True)
    frappe.delete_doc("Custom Field", "Employee-statutory_details", force=True)
    frappe.delete_doc("Custom Field", "Employee-sd_column_break", force=True)
    frappe.delete_doc("Custom Field", "Employee-sd_section_break", force=True)
    frappe.delete_doc("Custom Field", "Employee-statutory", force=True)
    frappe.delete_doc("Custom Field", "Employee-national_id", force=True)
    frappe.delete_doc("Custom Field", "Employee-nssf_no", force=True)
    frappe.delete_doc("Custom Field", "Employee-column_break_csf_emp_01", force=True)
    frappe.delete_doc("Custom Field", "Employee-nhif_no", force=True)
    frappe.delete_doc("Custom Field", "Employee-tax_id", force=True)
    frappe.delete_doc("Custom Field", "Employee-section_break_csf_emp_01", force=True)

    custom_fields = {
        "Employee": [
            {
                "fieldname": "statutory",
                "fieldtype": "Section Break",
                "collapsible": 1,
                "label": "Statutory Details",
                "translatable": 1,
                "insert_after": "personal_details"
            },
            {
                "fieldname": "national_id",
                "fieldtype": "Data",
                "label": "National ID",
                "translatable": 1,
                "insert_after": "statutory"
            },
            {
                "fieldname": "nssf_no",
                "fieldtype": "Data",
                "label": "NSSF No",
                "translatable": 1,
                "insert_after": "national_id"
            },
            {
                "fieldname": "cb_csf_emp_01",
                "fieldtype": "Column Break",
                "Label": "",
                "insert_after": "nssf_no"
            },
            {
                "fieldname": "nhif_no",
                "fieldtype": "Data",
                "label": "NHIF No",
                "translatable": 1,
                "insert_after": "cb_csf_emp_01"
            },
            {
                "fieldname": "tax_id",
                "fieldtype": "Data",
                "label": "Tax ID",
                "translatable": 1,
                "insert_after": "nhif_no"
            },
            {
                "fieldname": "sb_csf_emp_01",
                "fieldtype": "Section Break",
                "label": "",
                "insert_after": "tax_id"
            }
        ]
    }

    create_custom_fields(custom_fields, update=True)