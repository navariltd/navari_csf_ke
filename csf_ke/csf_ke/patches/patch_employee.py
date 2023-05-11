import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    custom_fields = {
        "Employee": [
            {
                "collapsible": 1,
                "fieldname": "statutory_details",
                "fieldtype": "Section Break",
                "insert_after": "personal_details",
                "label": "Statutory Details",
                "translatable": 1
            },
            {
                "fieldname": "national_id",
                "fieldtype": "Data",
                "insert_after": "statutory_details",
                "label": "National ID",
                "translatable": 1
            },
            {
                "fieldname": "nssf_no",
                "fieldtype": "Data",
                "insert_after": "national_id",
                "label": "NSSF No",
                "translatable": 1
            },
            {
                "fieldname": "column_break_statutory_details_01",
                "fieldtype": "Column Break",
                "insert_after": "nssf_no"
            },
            {
                "fieldname": "nhif_no",
                "fieldtype": "Data",
                "insert_after": "column_break_statutory_details_01",
                "label": "NHIF No",
                "translatable": 1
            },
            {
                "fieldname": "tax_id",
                "fieldtype": "Data",
                "insert_after": "nhif_no",
                "label": "Tax ID",
                "translatable": 1
            },
            {
                "fieldname": "section_break_statutory_details_01",
                "fieldtype": "Section Break",
                "insert_after": "tax_id"
            }
        ]
    }

    create_custom_fields(custom_fields)