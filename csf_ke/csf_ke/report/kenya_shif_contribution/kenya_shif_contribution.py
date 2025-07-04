# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
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
            "width": 100,
        },
        {
            "fieldname": "last_name",
            "label": "Last Name",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "fieldname": "identity_type",
            "label": "Identity Type",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "national_id",
            "label": "ID Number",
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
            "fieldname": "nhif_no",
            "label": "SHIF No",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "amount",
            "label": "Contribution Amount",
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "cell_number",
            "label": "Phone",
            "fieldtype": "Data",
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
            salary_slip.name.as_("payslip_number"),
            salary_slip.employee,
            employee.last_name if (employee.last_name) else "",
            employee.first_name,
            employee.national_id,
            employee.passport_number,
            employee.nhif_no,
            employee.cell_number,
            employee.tax_id,
            salary_details.amount,
        )
        .where(
            (salary_details.amount != 0)
            & (salary_slip.docstatus == 1)
            & (salary_details.salary_component == "SHIF")
        )
    )

    query = apply_filters(query, filters, employee, salary_slip)

    data = query.run(as_dict=True)

    for row in data:
        row["identity_type"] = None

        if row.get("national_id"):
            row["identity_type"] = "National ID"
            row["national_id"] = row.get("national_id")
        elif row.get("passport_number"):
            row["identity_type"] = "Passport"
            row["national_id"] = row.get("passport_number")

    return data


def apply_filters(query, filters, employee, salary_slip):
    """
    Applies relevant filters to the query.

    Args:
        query: The Frappe Query Builder query object.
        filters (dict): A dictionary of filters passed from the report.
        employee: The Frappe DocType for Employee.
        salary_slip: The Frappe DocType for Salary Slip.

    Returns:
        The modified query object with filters applied.
    """
    if filters.get("company"):
        query = query.where(employee.company == filters["company"])
    if filters.get("from_date"):
        query = query.where(salary_slip.start_date >= filters["from_date"])
    if filters.get("to_date"):
        query = query.where(salary_slip.end_date <= filters["to_date"])
    if filters.get("employee"):
        query = query.where(employee.name == filters["employee"])

    return query
