# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from ..kenya_shif_contribution.kenya_shif_contribution import apply_filters


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {
            "fieldname": "national_id",
            "label": "Member Number (ID Number)",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "full_name",
            "label": "Member Name",
            "fieldtype": "Data",
            "width": 250,
        },
        {
            "fieldname": "tax_id",
            "label": "KRA PIN",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "amount",
            "label": "Gross Salary",
            "fieldtype": "Currency",
            "width": 150,
        },
    ]


def get_data(filters):
    employee = frappe.qb.DocType("Employee")
    salary_slip = frappe.qb.DocType("Salary Slip")
    salary_details = frappe.qb.DocType("Salary Detail")

    query = (
        frappe.qb.from_(employee)
        .inner_join(salary_slip)
        .on(employee.name == salary_slip.employee)
        .inner_join(salary_details)
        .on(salary_slip.name == salary_details.parent)
        .select(
            salary_slip.employee,
            employee.employee_name.as_("full_name"),
            employee.national_id,
            employee.tax_id,
            salary_details.amount,
        )
        .where(
            (salary_details.amount != 0)
            & (salary_slip.docstatus == 1)
            & (salary_details.salary_component == "Gross Pay")
        )
    )

    query = apply_filters(query, filters, employee, salary_slip)

    data = query.run(as_dict=True)

    return data
