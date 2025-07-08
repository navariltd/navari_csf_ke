# # Copyright (c) 2023, Navari Limited and contributors
# # For license information, please see license.txt

import frappe
from frappe import _
from pypika import Case
from functools import reduce


def execute(filters=None):
    if filters.from_date > filters.to_date:
        frappe.throw(_("From Date cannot be greater than To Date"))

    return get_columns(), get_p10_report_data(filters)


def get_columns():
    columns = [
        {
            "fieldname": "tax_id",
            "label": _("PIN of Employee"),
            "fieldtype": "Link",
            "options": "Employee",
            "width": 150,
        },
        {
            "fieldname": "employee_name",
            "label": _("Employee Name"),
            "fieldtype": "Data",
            "read_only": 1,
            "width": 150,
        },
        {
            "fieldname": "basic_salary",
            "label": _("Basic Salary"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "housing_allowance",
            "label": _("Housing Allowance"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "transport_allowance",
            "label": _("Transport Allowance"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "leave_pay",
            "label": _("Leave Pay"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "overtime",
            "label": _("Overtime"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "directors_fee",
            "label": _("Director's Fee"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "lump_sum_payment",
            "label": _("Lump Sum Payment"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "other_allowance",
            "label": _("Other Allowance"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "total_cash_pay",
            "label": _("Total Cash Pay"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "value_of_car_benefit",
            "label": _("Value of Car Benefit"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "other_non_cash_benefits",
            "label": _("Other Non Cash Benefits"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "total_non_cash_pay",
            "label": _("Total Non Cash Pay"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "global_income",
            "label": _("Global Income"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "type_of_housing",
            "label": _("Type of Housing"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "rent_of_house",
            "label": _("Rent of House"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "computed_rent_of_house",
            "label": _("Computed Rent of House"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "rent_recovered_from_employee",
            "label": _("Rent Recovered from Employee"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "net_value_of_housing",
            "label": _("Net Value of Housing"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "total_gross_pay",
            "label": _("Total Gross Pay"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "30_percent_of_cash_pay",
            "label": _("30 Percent of Cash Pay"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "actual_contribution",
            "label": _("Actual Contribution"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "permissible limit",
            "label": _("Permissible Limit"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "mortgage_interest",
            "label": _("Mortgage Interest"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "affordable_housing_levy",
            "label": _("Affordable Housing Levy"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "shif",
            "label": _("SHIF"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "amount_of_benefit",
            "label": _("Amount of Benefit"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "taxable_pay",
            "label": _("Taxable Pay"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "tax_payable",
            "label": _("Tax Payable"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "monthly_personal_relief",
            "label": _("Monthly Personal Relief"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "amount_of_insurance",
            "label": _("Amount of Insurance"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "paye_tax",
            "label": _("PAYE Tax"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "self_assessed_paye_tax",
            "label": _("Self Assessed PAYE Tax"),
            "fieldtype": "Currency",
            "width": 150,
        },
    ]

    return columns


def get_p10_report_data(filters):
    employee = frappe.qb.DocType("Employee")
    salary_slip = frappe.qb.DocType("Salary Slip")
    salary_detail = frappe.qb.DocType("Salary Detail")
    salary_component_doc = frappe.qb.DocType("Salary Component")

    conditions = [salary_slip.docstatus == 1]
    if filters.get("company"):
        conditions.append(salary_slip.company == filters.get("company"))
    if filters.get("employee"):
        conditions.append(salary_slip.employee == filters.get("employee"))
    if filters.get("from_date") and filters.get("to_date"):
        conditions.append(
            salary_slip.posting_date.between(
                filters.get("from_date"), filters.get("to_date")
            )
        )

    salary_components = [
        "Basic Salary",
        "Housing Allowance",
        "Transport Allowance",
        "Leave Pay",
        "Overtime",
        "Directors Fee",
        "Lump Sum Payment",
        "Other Allowance",
        "Total Cash Pay",
        "Value of Car Benefit",
        "Other Non Cash Benefits",
        "Total Non Cash Pay",
        "Global Income",
        "Type of Housing",
        "Rent of House",
        "Computed Rent of House",
        "Rent Recovered from Employee",
        "Net Value of Housing",
        "Total Gross Pay",
        "30 Percent of Cash Pay",
        "Actual Contribution",
        "Permissible Limit",
        "Mortgage Interest",
        "Affordable Housing Levy",
        "SHIF",
        "Amount of Benefit",
        "Taxable Pay",
        "Tax Payable",
        "Monthly Personal Relief",
        "Amount of Insurance",
        "PAYE Tax",
        "Self Assessed PAYE Tax",
    ]

    query = (
        frappe.qb.from_(salary_slip)
        .inner_join(employee)
        .on(employee.name == salary_slip.employee)
        .inner_join(salary_detail)
        .on(salary_slip.name == salary_detail.parent)
        .inner_join(salary_component_doc)
        .on(salary_component_doc.name == salary_detail.salary_component)
        .select(
            employee.tax_id,
            salary_slip.employee_name,
            salary_slip.posting_date,
            salary_component_doc.p10a_tax_deduction_card_type.as_("salary_component"),
            Case()
            .when(salary_detail.amount.isnull(), 0)
            .else_(salary_detail.amount)
            .as_("amount"),
        )
        .where(
            salary_component_doc.p10a_tax_deduction_card_type.isin(salary_components)
            & reduce(lambda x, y: x & y, conditions)
        )
        .orderby(salary_slip.employee)
    )

    data = query.run(as_dict=True)

    employee_data = {}
    for row in data:
        employee_pin = row["tax_id"]
        employee_name = row["employee_name"]
        salary_component = row["salary_component"]
        amount = row["amount"]

        if salary_component is not None and amount is not None:
            employee_key = f"{employee_pin}-{employee_name}"

            if employee_key not in employee_data:
                employee_data[employee_key] = {
                    "employee_name": employee_name,
                    "tax_id": employee_pin,
                }

            if salary_component is not None:
                employee_data[employee_key][
                    salary_component.lower().replace(" ", "_")
                ] = amount

    report_data = []
    for employee_key, components in employee_data.items():
        employee_pin, employee_name = employee_key.rsplit("-", 1)
        row = {"tax_id": employee_pin, "employee_name": employee_name}
        row.update(components)
        report_data.append(row)

    return report_data
