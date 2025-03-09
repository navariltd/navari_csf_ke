# # Copyright (c) 2023, Navari Limited and contributors
# # For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate
from pypika import Case
from functools import reduce
from collections import defaultdict


def execute(filters=None):
    if filters.from_date > filters.to_date:
        frappe.throw(_("From Date cannot be greater than To Date"))

    execute2(filters)

    return get_columns(), get_p10_report_data(filters)


def execute2(filters=None):
    employees = get_employees(filters)
    if not employees:
        return [], []

    for employee in employees:
        component = get_p10a_tax_deduction(filters, employee.name, "PAYE Tax")

        # TODO: Get each component individually and process the data, then render(report)
        # TODO: Create another function to get the data for components whose value are not currencies


def get_employees(filters):
    employees_doc = frappe.qb.DocType("Employee")
    employees_query = (
        frappe.qb.from_(employees_doc)
        .select(employees_doc.name, employees_doc.tax_id, employees_doc.company)
        .where(employees_doc.company == filters.get("company"))
    )

    if filters.get("employee"):
        employees_query = employees_query.where(
            employees_doc.name == filters.get("employee")
        )

    employees = employees_query.run(as_dict=True)

    return employees


def get_p10a_tax_deduction(filters, employee, p10a_tax_deduction_card_type):
    salary_slip_doc = frappe.qb.DocType("Salary Slip")
    salary_detail_doc = frappe.qb.DocType("Salary Detail")
    salary_component_doc = frappe.qb.DocType("Salary Component")

    salary_slip_query = (
        frappe.qb.from_(salary_slip_doc)
        .inner_join(salary_detail_doc)
        .on(salary_slip_doc.name == salary_detail_doc.parent)
        .inner_join(salary_component_doc)
        .on(salary_detail_doc.salary_component == salary_component_doc.name)
        .select(
            salary_slip_doc.employee,
            salary_slip_doc.docstatus,
            salary_slip_doc.company,
            salary_detail_doc.amount,
            salary_component_doc.p10a_tax_deduction_card_type,
        )
        .where(
            (salary_slip_doc.docstatus == 1)
            & (
                salary_component_doc.p10a_tax_deduction_card_type
                == p10a_tax_deduction_card_type
            )
            & (salary_slip_doc.employee == employee)
            & (salary_slip_doc.company == filters.get("company"))
            & (salary_slip_doc.posting_date >= getdate(filters.get("from_date")))
            & (salary_slip_doc.posting_date <= getdate(filters.get("to_date")))
        )
    )

    deduction_component = salary_slip_query.run(as_dict=True)
    if not deduction_component:
        return []
    else:
        db_key = "_".join(p10a_tax_deduction_card_type.split()).lower()
        component_total = defaultdict(lambda: defaultdict(int))
        for component in deduction_component:
            key = component.get("p10a_tax_deduction_card_type")
            component_total[key][db_key] += component.get("amount")
        total = list(component_total.values())
        return total[0][db_key]


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
            "fieldname": "director_fee",
            "label": _("Director's Fee"),
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
            "fieldname": "affordable_housing_relief",
            "label": _("Affordable Housing Relief"),
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
        {
            "fieldname": "lump_sum_payment",
            "label": _("Lump Sum Payment"),
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "fieldname": "paye",
            "label": _("PAYE"),
            "fieldtype": "Currency",
            "width": 150,
        },
    ]

    return columns


def get_p10_report_data(filters):
    employee = frappe.qb.DocType("Employee")
    salary_slip = frappe.qb.DocType("Salary Slip")
    salary_detail = frappe.qb.DocType("Salary Detail")

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
        "House Allowance",
        "Transport Allowance",
        "Leave Allowance",
        "Overtime",
        "Commissions",
        "PAYE",
    ]

    query = (
        frappe.qb.from_(salary_slip)
        .inner_join(employee)
        .on(employee.name == salary_slip.employee)
        .inner_join(salary_detail)
        .on(salary_slip.name == salary_detail.parent)
        .select(
            employee.tax_id,
            salary_slip.employee_name,
            salary_slip.posting_date,
            salary_detail.salary_component,
            Case()
            .when(salary_detail.amount.isnull(), 0)
            .else_(salary_detail.amount)
            .as_("amount"),
        )
        .where(
            salary_detail.salary_component.isin(salary_components)
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
