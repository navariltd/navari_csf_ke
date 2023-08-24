import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    custom_fields = {
        "Employee Separation": [
            {
                "fieldname": "employee_separation_type",
                "label": "Employee Separation Type",
                "fieldtype": "Link",
                "options": "Employee Separation Type",
                "insert_after": "employee_name",
                "reqd": 0,
                "translatable": 1
            },
        ]
    }

    create_custom_fields(custom_fields, update=True)