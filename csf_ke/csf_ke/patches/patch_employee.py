import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    frappe.delete_doc("Custom Field", "Employee-statutory", force=True)
    frappe.delete_doc("Custom Field", "Employee-national_id", force=True)
    frappe.delete_doc("Custom Field", "Employee-nssf_no", force=True)
    frappe.delete_doc("Custom Field", "Employee-cb_csf_emp_01", force=True)
    frappe.delete_doc("Custom Field", "Employee-nhif_no", force=True)
    frappe.delete_doc("Custom Field", "Employee-tax_id", force=True)
    frappe.delete_doc("Custom Field", "Employee-sb_csf_emp_01", force=True)

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
                "label": "",
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
                "insert_after": "tax_id"
            },
            {
                "fieldname": "probation_start_date",
                "label": "Probation Start Date",
                "fieldtype": "Date",
                "insert_after": "col_break_22",
                "translatable": 1
            },
            {
                "fieldname": "probation_end_date",
                "label": "Probation End Date",
                "fieldtype": "Date",
                "insert_after": "probation_start_date",
                "translatable": 1
            },
            {
                "fieldname": "cb_navari_vf_emp_01",
                "fieldtype": "Column Break",
                "insert_after": "probation_end_date",
                "translatable": 1
            },
            {
                "fieldname": "contract_start_date",
                "label": "Contract Start Date",
                "fieldtype": "Date",
                "insert_after": "final_confirmation_date",
                "translatable": 1
            },
            {
                "fieldname": "bank_branch_name",
                "fieldtype": "Data",
                "label": "Bank Branch Name",
                "translatable": 1,
                "insert_after": "bank_name"
            },
        ]
    }

    create_custom_fields(custom_fields, update=True)