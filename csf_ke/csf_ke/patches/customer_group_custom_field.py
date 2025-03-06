import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    custom_fields = {"Customer Group": [
        {
            "fieldname": "custom_is_kra_pin_mandatory_in",
            "label": "Is KRA PIN Mandatory In",
            "fieldtype": "Select",
            "insert_after": "is_group",
            "options": "\nCustomer\nSales Order\nSales Invoice\nSales order and Invoice\nAll"
        }
    ]}          
    create_custom_fields(custom_fields)
