import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    custom_fields = {
        "Job Offer": [
            {
                "fieldname": "valid_till",
                "label": "Valid Till",
                "fieldtype": "Date",
                "insert_after": "offer_date",
                "reqd": 1,
                "translatable": 1
            },
        ]
    }

    create_custom_fields(custom_fields, update=True)