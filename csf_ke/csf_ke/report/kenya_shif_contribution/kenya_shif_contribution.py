# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    print("Generating columns for Kenya SHIF Contributions report...")

    return [
        {
            "fieldname": "payslip_number",
            "label": "Payroll Number",
            "fieldtype": "Link",
            "options": "Salary Slip",
            "width": 150,
        },
        {
            "fieldname": "first_name",
            "label": "First Name",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "last_name",
            "label": "Last Name",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "identity_type",
            "label": "Identity Type",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "fieldname": "identity_number",
            "label": "Identity Number",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "tax_id",
            "label": "KRA PIN",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "contribution",
            "label": "Contribution Amount",
            "fieldtype": "Currency",
            "width": 150,
        },
    ]


def get_data(filters):
    SalarySlip = frappe.qb.DocType("Salary Slip")
    Employee = frappe.qb.DocType("Employee")
    SalaryDetail = frappe.qb.DocType("Salary Detail")

    query = (
        frappe.qb.select(
            SalarySlip.name.as_("payslip_number"),
            Employee.first_name,
            Employee.last_name,
            Employee.tax_id,
            Employee.national_id.as_("identity_number"),
            SalaryDetail.amount.as_("contribution"),
        )
        .from_(SalarySlip)
        .join(Employee)
        .on(SalarySlip.employee == Employee.name)
        .join(SalaryDetail)
        .on(SalarySlip.name == SalaryDetail.parent)
        .where((SalarySlip.docstatus == 1) & (SalaryDetail.salary_component == "SHIF"))
    )

    data = query.run(as_dict=True)

    return data
