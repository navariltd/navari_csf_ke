import frappe

def execute():
    names = [
        "Employee-national_id",
        "Employee-nhif_no",
        "Employee-nssf_no",
        "Employee-tax_id",
        "Salary Component-p9a_tax_deduction_card_type",
        "Salary Component-custom_p10a_tax_deduction_card_type",
        "Item Tax-custom_column_break",
        "Item Tax-custom_tims_hscode",
        "Customer Group-custom_is_kra_pin_mandatory_in",
        "Company-custom_column_break_tunh2",
        "Company-custom_withholding_accounts",
        "Company-custom_default_debitors_withholding_account",
        "Company-custom_default_creditors_withholding_account",
        "Employee-custom_statutory_details",
        "Employee-custom_nssf_no",
        "Employee-custom_cb_csf_emp_01",
        "Employee-custom_nhif_no",
        "Employee-custom_tax_id",
        "Employee-custom_probation_start_date",
        "Employee-custom_probation_end_date",
        "Employee-custom_contract_start_date",
        "Employee-custom_bank_branch_name",
        "Job Offer-custom_valid_till",
        "Manufacturing Settings-custom_allow_default_time_logs",
        "Sales Invoice-etr_data",
        "Sales Invoice-etr_serial_number",
        "Sales Invoice-cu_invoice_date",
        "Sales Invoice-etr_column_break",
        "Sales Invoice-etr_invoice_number",
        "Sales Invoice-cu_link",
        "Sales Invoice-is_filed",
        "Purchase Invoice-etr_data",
        "Purchase Invoice-etr_serial_number",
        "Purchase Invoice-cu_invoice_date",
        "Purchase Invoice-etr_column_break",
        "Purchase Invoice-etr_invoice_number",
        "Purchase Invoice-cu_link",
        "Purchase Invoice-is_filed",
    ]

    for name in names:
        if frappe.db.exists("Custom Field", name):
            frappe.delete_doc("Custom Field", name, force=True)