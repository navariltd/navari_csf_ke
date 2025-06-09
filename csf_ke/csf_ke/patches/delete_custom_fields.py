import frappe

def execute():
    custom_fields = [
        {"dt": "Employee", "fieldname": "national_id"},
        {"dt": "Employee", "fieldname": "nhif_no"},
        {"dt": "Employee", "fieldname": "nssf_no"},
        {"dt": "Employee", "fieldname": "tax_id"},
        {"dt": "Salary Component", "fieldname": "p9a_tax_deduction_card_type"},
        {"dt": "Salary Component", "fieldname": "p10a_tax_deduction_card_type"},
        {"dt": "Item Tax", "fieldname": "column_break"},
        {"dt": "Item Tax", "fieldname": "tims_hscode"},
        {"dt": "Customer Group", "fieldname": "is_kra_pin_mandatory_in"},
        {"dt": "Company", "fieldname": "column_break_tunh2"},
        {"dt": "Company", "fieldname": "withholding_accounts"},
        {"dt": "Company", "fieldname": "default_debitors_withholding_account"},
        {"dt": "Company", "fieldname": "default_creditors_withholding_account"},
        {"dt": "Employee", "fieldname": "statutory_details"},
        {"dt": "Employee", "fieldname": "cb_csf_emp_01"},
        {"dt": "Employee", "fieldname": "probation_start_date"},
        {"dt": "Employee", "fieldname": "probation_end_date"},
        {"dt": "Employee", "fieldname": "contract_start_date"},
        {"dt": "Employee", "fieldname": "bank_branch_name"},
        {"dt": "Job Offer", "fieldname": "valid_till"},
        {"dt": "Manufacturing Settings", "fieldname": "allow_default_time_logs"},
        {"dt": "Sales Invoice", "fieldname": "etr_data"},
        {"dt": "Sales Invoice", "fieldname": "etr_serial_number"},
        {"dt": "Sales Invoice", "fieldname": "cu_invoice_date"},
        {"dt": "Sales Invoice", "fieldname": "etr_column_break"},
        {"dt": "Sales Invoice", "fieldname": "etr_invoice_number"},
        {"dt": "Sales Invoice", "fieldname": "cu_link"},
        {"dt": "Sales Invoice", "fieldname": "is_filed"},
        {"dt": "Purchase Invoice", "fieldname": "etr_data"},
        {"dt": "Purchase Invoice", "fieldname": "is_filed"},
    ]

    for field in custom_fields:
        custom_field = frappe.db.get_value(
            "Custom Field", 
            {"dt": field["dt"], "fieldname": field["fieldname"]}, 
            "name"
        )
        if custom_field:
            frappe.delete_doc("Custom Field", custom_field, force=True)