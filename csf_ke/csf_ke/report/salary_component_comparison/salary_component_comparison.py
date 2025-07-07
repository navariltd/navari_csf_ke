# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt
from datetime import datetime, timedelta
from calendar import monthrange
from collections import defaultdict
import copy
import calendar

import frappe
import erpnext
from frappe.utils import flt, getdate, get_first_day, get_last_day
from frappe import _


def execute(filters=None):
    if not filters:
        return
    company_currency = erpnext.get_company_currency(filters.get("company"))

    validate_date_filters(filters)

    columns = get_columns(filters)
    data = get_data(filters, company_currency)

    return columns, data


def validate_date_filters(filters):
    start = filters.get("from_date")
    end = filters.get("to_date")

    if getdate(end) < getdate(start):
        frappe.throw(_("To Date cannot be before From Date"))


def get_data(filters, company_currency):
    old_end_date = get_last_day(getdate(filters.get("from_date"))).strftime("%Y-%m-%d")
    new_start_date = get_first_day(getdate(filters.get("to_date"))).strftime("%Y-%m-%d")

    old_ss_filters = filters.copy()
    old_ss_filters.update(
        {"start_date": filters.get("from_date"), "end_date": old_end_date}
    )

    new_ss_filters = filters.copy()
    new_ss_filters.update(
        {"start_date": new_start_date, "end_date": filters.get("to_date")}
    )

    old_salary_slips = get_salary_slips(old_ss_filters, company_currency)

    new_salary_slips = get_salary_slips(new_ss_filters, company_currency)

    old_ss_count = len(old_salary_slips) if old_salary_slips else 0
    new_ss_count = len(new_salary_slips) if new_salary_slips else 0

    earnings_data = get_salary_slip_data(old_salary_slips, new_salary_slips)
    deductions_data = get_salary_slip_data(
        old_salary_slips, new_salary_slips, "deductions"
    )

    grouped_data = []

    if earnings_data and deductions_data:

        if filters.get("based_on") == "Department":
            grouped_data = get_department_breakdown(
                filters, earnings_data, deductions_data, old_ss_count, new_ss_count
            )

        elif filters.get("based_on") == "Employee":
            grouped_data = get_comparison_per_employee(
                filters, earnings_data, deductions_data
            )
        else:
            grouped_data = get_comparison_per_company(
                filters, earnings_data, deductions_data
            )

    return grouped_data


def get_columns(filters):
    old_date = getdate(filters.get("from_date"))
    new_date = getdate(filters.get("to_date"))

    old_month_name = calendar.month_name[old_date.month]
    new_month_name = calendar.month_name[new_date.month]

    columns = [
        {
            "fieldname": "total_prev_month",
            "label": _("{0} {1}".format(old_month_name, old_date.year)),
            "fieldtype": "Float",
            "width": 150,
            "precision": 2,
        },
        {
            "fieldname": "total",
            "label": _("{0} {1}".format(new_month_name, new_date.year)),
            "fieldtype": "Float",
            "width": 200,
            "precision": 2,
        },
        {
            "fieldname": "difference_amount",
            "label": _("Difference Amount"),
            "fieldtype": "Float",
            "width": 200,
            "precision": 2,
        },
    ]

    if filters.get("based_on") == "Department":
        new_columns = [
            {
                "fieldname": "salary_component",
                "label": _("Salary Component"),
                "fieldtype": "Data",
                "width": 200,
            },
            {
                "fieldname": "department",
                "label": _("Department"),
                "fieldtype": "Link",
                "options": "Department",
                "width": 200,
            },
        ]

        for column in new_columns:
            columns.insert(0, column)

    if filters.get("based_on") == "Employee":
        new_columns = [
            {
                "fieldname": "salary_component",
                "label": _("Salary Component"),
                "fieldtype": "Data",
                "width": 200,
            },
            {
                "fieldname": "employee",
                "label": _("Employee"),
                "fieldtype": "Link",
                "options": "Employee",
                "width": 200,
            },
            {
                "fieldname": "department",
                "label": _("Department"),
                "fieldtype": "Link",
                "options": "Department",
                "width": 200,
            },
        ]

        for column in new_columns:
            columns.insert(0, column)

    if filters.get("based_on") == "Company":
        new_columns = [
            {
                "fieldname": "component_group",
                "label": _("Component Group"),
                "fieldtype": "Data",
                "width": 200,
            },
            {
                "fieldname": "company",
                "label": _("Company"),
                "fieldtype": "Link",
                "options": "Company",
                "width": 200,
            },
        ]

        for column in new_columns:
            columns.insert(0, column)

    return columns


def get_conditions(filters, company_currency):
    conditions = []
    params = {}

    doc_status_map = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
    if filters.get("docstatus"):
        conditions.append("docstatus = %(docstatus)s")
        params["docstatus"] = doc_status_map[filters["docstatus"]]
    else:
        conditions.append("docstatus = 1")

    if filters.get("start_date"):
        conditions.append("start_date >= %(start_date)s")
        params["start_date"] = filters["start_date"]

    if filters.get("end_date"):
        conditions.append("end_date <= %(end_date)s")
        params["end_date"] = filters["end_date"]

    if filters.get("company"):
        conditions.append("company = %(company)s")
        params["company"] = filters["company"]

    if filters.get("employee"):
        conditions.append("employee = %(employee)s")
        params["employee"] = filters["employee"]

    if filters.get("currency") and filters.get("currency") != company_currency:
        conditions.append("currency = %(currency)s")
        params["currency"] = filters["currency"]

    if filters.get("department"):
        conditions.append("department = %(department)s")
        params["department"] = filters["department"]

    return " AND ".join(conditions), params


def get_salary_slips(filters, company_currency):
    conditions, params = get_conditions(filters, company_currency)

    salary_slips = frappe.db.sql(
        """
        SELECT name, employee, start_date, end_date 
        FROM `tabSalary Slip` 
        WHERE {conditions}
        ORDER BY employee
        """.format(
            conditions=conditions
        ),
        values=params,
        as_dict=1,
    )

    return salary_slips


def get_number_of_employees(salary_slips):
    return len(salary_slips)


def salary_slip_earnings(salary_slips):
    ss_earnings = frappe.db.sql(
        """
        SELECT ss.employee, ss.department, ss.company, sd.salary_component, sd.parentfield, SUM(sd.amount) as total
        FROM `tabSalary Detail` sd, `tabSalary Slip` ss where sd.parent=ss.name 
        AND sd.parent in (%s)
        AND sd.do_not_include_in_total = 0
        AND sd.parentfield = 'earnings'
        GROUP BY ss.employee, ss.department, ss.company, sd.salary_component
        ORDER BY sd.salary_component ASC"""
        % (", ".join(["%s"] * len(salary_slips))),
        tuple([d.name for d in salary_slips]),
        as_dict=1,
    )
    return ss_earnings


def salary_slip_deductions(salary_slips):
    ss_earnings = frappe.db.sql(
        """
        SELECT ss.employee, ss.department, ss.company, sd.salary_component, sd.parentfield, SUM(sd.amount) as total
        FROM `tabSalary Detail` sd, `tabSalary Slip` ss where sd.parent=ss.name 
        AND sd.parent in (%s)
        AND sd.do_not_include_in_total = 0
        AND sd.parentfield = 'deductions'
        GROUP BY ss.employee, ss.department, ss.company, sd.salary_component
        ORDER BY sd.salary_component ASC"""
        % (", ".join(["%s"] * len(salary_slips))),
        tuple([d.name for d in salary_slips]),
        as_dict=1,
    )

    return ss_earnings


def get_salary_slip_data(old_salary_slips, new_salary_slips, component_type="earnings"):
    data = []

    if component_type == "earnings":
        old_data = salary_slip_earnings(old_salary_slips) if old_salary_slips else []
        new_data = salary_slip_earnings(new_salary_slips) if new_salary_slips else []
    elif component_type == "deductions":
        old_data = salary_slip_deductions(old_salary_slips) if old_salary_slips else []
        new_data = salary_slip_deductions(new_salary_slips) if new_salary_slips else []
    else:
        frappe.throw("Invalid component_type. Use 'earnings' or 'deductions'.")

    if old_data and new_data:
        seen_components = set()

        for new_row in new_data:
            new_key = (
                new_row["employee"],
                new_row["department"],
                new_row["salary_component"],
            )
            seen_components.add(new_key)

            matched = False
            for old_row in old_data:
                if (
                    new_row["employee"] == old_row["employee"]
                    and new_row["department"] == old_row["department"]
                    and new_row["salary_component"] == old_row["salary_component"]
                ):

                    data.append(
                        {
                            "company": new_row["company"],
                            "employee": new_row["employee"],
                            "department": new_row["department"],
                            "salary_component": new_row["salary_component"],
                            "total_prev_month": old_row["total"],
                            "total": new_row["total"],
                            "parentfield": new_row["parentfield"],
                        }
                    )
                    matched = True
                    break

            if not matched:
                data.append(
                    {
                        "company": new_row["company"],
                        "employee": new_row["employee"],
                        "department": new_row["department"],
                        "salary_component": new_row["salary_component"],
                        "total_prev_month": 0,
                        "total": new_row["total"],
                        "parentfield": new_row["parentfield"],
                    }
                )

        for old_row in old_data:
            old_key = (
                old_row["employee"],
                old_row["department"],
                old_row["salary_component"],
            )
            if old_key not in seen_components:
                data.append(
                    {
                        "company": old_row["company"],
                        "employee": old_row["employee"],
                        "department": old_row["department"],
                        "salary_component": old_row["salary_component"],
                        "total_prev_month": old_row["total"],
                        "total": 0,
                        "parentfield": old_row["parentfield"],
                    }
                )

    elif old_data and not new_data:
        for row in old_data:
            data.append(
                {
                    "company": row["company"],
                    "employee": row["employee"],
                    "department": row["department"],
                    "salary_component": row["salary_component"],
                    "total_prev_month": row["total"],
                    "total": 0,
                    "parentfield": row["parentfield"],
                }
            )

    elif new_data and not old_data:
        for row in new_data:
            data.append(
                {
                    "company": row["company"],
                    "employee": row["employee"],
                    "department": row["department"],
                    "salary_component": row["salary_component"],
                    "total_prev_month": 0,
                    "total": row["total"],
                    "parentfield": row["parentfield"],
                }
            )

    return data


def get_comparison_per_company(filters, earnings_data, deductions_data):
    all_data = earnings_data + deductions_data
    grouped = defaultdict(lambda: {"earnings": [], "deductions": []})

    for row in all_data:
        comp = row["company"]
        pf = row["parentfield"]
        grouped[comp][pf].append(row)

    final_output = []

    for company in sorted(grouped.keys()):
        earnings = grouped[company]["earnings"]
        deductions = grouped[company]["deductions"]

        if earnings and not filters.get("component_type") == "Deductions":
            total_prev_month = sum(row["total_prev_month"] for row in earnings) or 0
            total = sum(row["total"] for row in earnings) or 0
            total_difference = total - total_prev_month
            final_output.append(
                {
                    "company": company,
                    "component_group": "EARNINGS",
                    "total_prev_month": total_prev_month,
                    "total": total,
                    "is_title": True,
                    "difference_amount": total_difference,
                }
            )

        if deductions and not filters.get("component_type") == "Earnings":
            total_prev_month = sum(row["total_prev_month"] for row in deductions) or 0
            total = sum(row["total"] for row in deductions) or 0
            total_difference = total - total_prev_month
            final_output.append(
                {
                    "company": company,
                    "component_group": "DEDUCTIONS",
                    "total_prev_month": total_prev_month,
                    "total": total,
                    "is_title": True,
                    "difference_amount": total_difference,
                }
            )

    return final_output


def get_department_breakdown(
    filters, earnings_data, deductions_data, old_ss_count, new_ss_count
):

    all_data = earnings_data + deductions_data

    grouped = defaultdict(lambda: {"earnings": [], "deductions": []})

    for row in all_data:
        dept = row["department"]
        pf = row["parentfield"]
        grouped[dept][pf].append(row)

    final_output = []

    final_output.append(
        {
            "department": None,
            "salary_component": "TOTAL EMPLOYEES",
            "total_prev_month": old_ss_count,
            "total": new_ss_count,
            "is_title": True,
            "difference_amount": None,
        }
    )

    for department in sorted(grouped.keys()):
        earnings = grouped[department]["earnings"]
        deductions = grouped[department]["deductions"]

        if earnings and not filters.get("component_type") == "Deductions":
            total_prev_month = sum(row["total_prev_month"] for row in earnings) or 0
            total = sum(row["total"] for row in earnings) or 0
            total_difference = total - total_prev_month
            final_output.append(
                {
                    "department": department,
                    "salary_component": "EARNINGS TOTAL",
                    "total_prev_month": total_prev_month,
                    "total": total,
                    "is_title": True,
                    "difference_amount": total_difference,
                }
            )

            combined_totals = get_components_total(earnings)
            final_output.extend(combined_totals)

        if deductions and not filters.get("component_type") == "Earnings":
            total_prev_month = sum(row["total_prev_month"] for row in deductions) or 0
            total = sum(row["total"] for row in deductions) or 0
            total_difference = total - total_prev_month
            final_output.append(
                {
                    "department": (
                        department
                        if filters.get("component_type") == "Deductions"
                        else None
                    ),
                    "salary_component": "DEDUCTIONS TOTAL",
                    "total_prev_month": total_prev_month,
                    "total": total,
                    "is_title": True,
                    "difference_amount": total_difference,
                }
            )

            combined_totals = get_components_total(deductions)
            final_output.extend(combined_totals)

    return final_output


def get_components_total(data):

    grouped_earnings = defaultdict(lambda: {"total": 0, "total_prev_month": 0})

    for d in data:
        component = d["salary_component"]
        grouped_earnings[component]["total"] += d.get("total", 0)
        grouped_earnings[component]["total_prev_month"] += d.get("total_prev_month", 0)

    final_output = []

    for component, totals in grouped_earnings.items():
        new_earning = {
            "salary_component": component,
            "department": None,
            "total": totals["total"],
            "total_prev_month": totals["total_prev_month"],
            "difference_amount": totals["total"] - totals["total_prev_month"],
        }
        final_output.append(new_earning)

    return final_output


def get_comparison_per_employee(filters, earnings_data, deductions_data):
    all_data = earnings_data + deductions_data

    grouped = defaultdict(lambda: {"earnings": [], "deductions": []})

    for row in all_data:
        key = (row["department"], row["employee"])
        pf = row["parentfield"]
        grouped[key][pf].append(row)

    final_output = []

    for emp in sorted(grouped.keys()):
        earnings = grouped[emp]["earnings"]
        deductions = grouped[emp]["deductions"]

        if earnings and not filters.get("component_type") == "Deductions":
            total_prev_month = sum(row["total_prev_month"] for row in earnings) or 0
            total = sum(row["total"] for row in earnings) or 0
            total_difference = total - total_prev_month
            final_output.append(
                {
                    "department": emp[0],
                    "employee": emp[1],
                    "salary_component": "EARNINGS TOTAL",
                    "total_prev_month": total_prev_month,
                    "total": total,
                    "is_title": True,
                    "difference_amount": total_difference,
                }
            )

            for earning in earnings:
                new_earning = copy.deepcopy(earning)
                new_earning["department"] = None
                new_earning["employee"] = None
                new_earning["difference_amount"] = new_earning.get(
                    "total", 0
                ) - new_earning.get("total_prev_month", 0)
                final_output.append(new_earning)

        if deductions and not filters.get("component_type") == "Earnings":
            total_prev_month = sum(row["total_prev_month"] for row in deductions) or 0
            total = sum(row["total"] for row in deductions) or 0
            total_difference = total - total_prev_month
            final_output.append(
                {
                    "department": (
                        emp[0]
                        if filters.get("component_type") == "Deductions"
                        else None
                    ),
                    "employee": (
                        emp[1]
                        if filters.get("component_type") == "Deductions"
                        else None
                    ),
                    "salary_component": "DEDUCTIONS TOTAL",
                    "total_prev_month": total_prev_month,
                    "total": total,
                    "is_title": True,
                    "difference_amount": total_difference,
                }
            )

            for deduction in deductions:
                new_deduction = copy.deepcopy(deduction)
                new_deduction["department"] = None
                new_deduction["employee"] = None
                new_deduction["difference_amount"] = new_deduction.get(
                    "total", 0
                ) - new_deduction.get("total_prev_month", 0)
                final_output.append(new_deduction)

    return final_output
