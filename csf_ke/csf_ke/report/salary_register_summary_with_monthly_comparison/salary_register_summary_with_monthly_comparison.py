# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt
from datetime import datetime, timedelta
from calendar import monthrange
from collections import defaultdict
import copy

import frappe
import erpnext
from frappe.utils import flt, getdate, get_first_day, get_last_day
from frappe import _
from frappe.utils.nestedset import get_descendants_of

import calendar


def execute(filters=None):
    company_currency = erpnext.get_company_currency(filters.get("company"))

    validate_date_filters(filters)

    columns = get_columns(filters)
    data = group_per_department(filters, company_currency)

    return columns, data


def validate_date_filters(filters):
    start = filters.get("from_date")
    end = filters.get("to_date")

    if not consecutive_months(start, end):
        frappe.throw(
            "Start Date must be the first day of the selected month and End Date must be the last day of the next consecutive month."
        )


def consecutive_months(date_1, date_2):
    start = datetime.strptime(date_1, "%Y-%m-%d")
    end = datetime.strptime(date_2, "%Y-%m-%d")
    expected_end = ""

    if start.day != 1:
        frappe.throw("From Date must be the first day of the selected month.")

    if start.month == 12:
        expected_end = datetime(start.year + 1, 2, 1) - timedelta(days=1)
    else:
        next_month = start.month + 1
        next_year = start.year
        if next_month == 13:
            next_month = 1
            next_yeart += 1

        days_in_the_next_month = monthrange(next_year, next_month)[1]
        expected_end = datetime(next_year, next_month, days_in_the_next_month)

    return end == expected_end


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

    if filters.get("department_breakdown"):
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
                "fieldtype": "Data",
                "width": 200,
            },
        ]

        for column in new_columns:
            columns.insert(0, column)

    else:
        columns.insert(
            0,
            {
                "fieldname": "component_group",
                "label": _("Component Group"),
                "fieldtype": "Data",
                "width": 200,
            },
        )

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

    if filters.get("department") and filters.get("company"):
        department_list = get_departments(filters["department"], filters["company"])
        if department_list:
            placeholders = ",".join(["%s"] * len(department_list))
            conditions.append(f"department IN ({placeholders})")
            params.update({f"dept_{i}": dept for i, dept in enumerate(department_list)})

    return " AND ".join(conditions), params


def get_departments(department, company):
    departments_list = get_descendants_of("Department", department)
    departments_list.append(department)
    return departments_list


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


def get_salary_slip_data(old_salary_slips, new_salary_slips, component_type="earnings"):
    data = []
    old_data = []
    new_data = []

    if component_type == "earnings":
        old_data = salary_slip_earnings(old_salary_slips) if old_salary_slips else []
        new_data = salary_slip_earnings(new_salary_slips) if new_salary_slips else []

    if component_type == "deductions":
        old_data = salary_slip_deductions(old_salary_slips) if old_salary_slips else []
        new_data = salary_slip_deductions(new_salary_slips) if new_salary_slips else []

    unique_old_salary_components = []
    unique_new_salary_components = []

    if old_data and new_data:
        for new_data_row in new_data:

            for old_data_row in old_data:
                if new_data_row.get("department") == old_data_row.get(
                    "department"
                ) and new_data_row.get("salary_component") == old_data_row.get(
                    "salary_component"
                ):
                    amount_diff = flt(
                        new_data_row.get("total") - old_data_row.get("total"),
                        2,
                    )

                    new_data_row.update(
                        {
                            "total_prev_month": old_data_row.get("total"),
                            "difference_amount": amount_diff,
                        }
                    )
                    data.append(new_data_row)

                    unique_new_salary_components.append(
                        {
                            "department": new_data_row.get("department"),
                            "salary_component": new_data_row.get("salary_component"),
                        }
                    )
                    unique_old_salary_components.append(
                        {
                            "department": old_data_row.get("department"),
                            "salary_component": old_data_row.get("salary_component"),
                        }
                    )

            cur_row = {
                "department": new_data_row.get("department"),
                "salary_component": new_data_row.get("salary_component"),
            }

            if cur_row not in unique_new_salary_components:
                unique_old_salary_components.append(
                    {
                        "department": new_data_row.get("department"),
                        "salary_component": new_data_row.get("salary_component"),
                    }
                )

                data.append(
                    {
                        "department": new_data_row.get("department"),
                        "salary_component": new_data_row.get("salary_component"),
                        "total_prev_month": 0,
                        "total_cur_month": new_data_row.get("total"),
                        "difference_amount": new_data_row.get("total"),
                    }
                )

        for row in old_data:
            old_row = {
                "department": row.get("department"),
                "salary_component": row.get("salary_component"),
            }
            if old_row not in unique_old_salary_components:
                data.append(
                    {
                        "department": row.get("department"),
                        "salary_component": row.get("salary_component"),
                        "total_prev_month": row.get("total") or 0,
                        "total": 0,
                        "difference_amount": row.get("total"),
                    }
                )

    elif old_data and not new_data:
        for earning in old_data:
            total = earning.get("total", 0)
            earning.update(
                {
                    "total_prev_month": total,
                    "total": 0,
                    "difference_amount": earning.get("total"),
                }
            )

            data.append(earning)

    elif new_data and not old_data:
        for earning in new_data:
            total = earning.get("total", 0)
            earning.update(
                {
                    "total_prev_month": 0,
                    "total": total,
                    "difference_amount": earning.get("total"),
                }
            )

            data.append(earning)

    return data


def group_per_department(filters, company_currency):
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
    department_breakdown = filters.get("department_breakdown")
    if earnings_data and deductions_data and department_breakdown:
        grouped_data = get_department_breakdown(
            earnings_data, deductions_data, old_ss_count, new_ss_count
        )

    elif earnings_data and deductions_data and not department_breakdown:
        grouped_data = get_comparison_per_component(earnings_data, deductions_data)

    return grouped_data


def get_comparison_per_component(earnings_data, deductions_data):
    total_prev_month_earnings = sum(
        row["total_prev_month"]
        for row in earnings_data
        if row.parentfield == "earnings"
    )
    total_cur_month_earnings = sum(
        row["total"] for row in earnings_data if row.parentfield == "earnings"
    )
    earnings_diff = total_cur_month_earnings - total_prev_month_earnings

    total_prev_month_deductions = sum(
        row["total_prev_month"]
        for row in deductions_data
        if row.parentfield == "deductions"
    )
    total_cur_month_deductions = sum(
        row["total"] for row in deductions_data if row.parentfield == "deductions"
    )
    deductions_diff = total_cur_month_deductions - total_prev_month_deductions

    final_output = []

    earnings_dict = {
        "component_group": "EARNINGS TOTAL",
        "total_prev_month": total_prev_month_earnings,
        "total": total_cur_month_earnings,
        "difference_amount": earnings_diff,
    }

    final_output.append(earnings_dict)

    deductions_dict = {
        "component_group": "DEDUCTIONS TOTAL",
        "total_prev_month": total_prev_month_deductions,
        "total": total_cur_month_deductions,
        "difference_amount": deductions_diff,
    }

    final_output.append(deductions_dict)

    return final_output


def get_department_breakdown(
    earnings_data, deductions_data, old_ss_count, new_ss_count
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
            "indent": 0,
            "is_title": True,
            "difference_amount": None,
        }
    )

    for department in sorted(grouped.keys()):
        earnings = grouped[department]["earnings"]
        deductions = grouped[department]["deductions"]

        if earnings:
            total_prev_month = sum(row["total_prev_month"] for row in earnings)
            total = sum(row["total"] for row in earnings)
            total_difference = sum(row["difference_amount"] for row in earnings)
            final_output.append(
                {
                    "department": department,
                    "salary_component": "EARNINGS TOTAL",
                    "total_prev_month": total_prev_month,
                    "total": total,
                    "indent": 0,
                    "is_title": True,
                    "difference_amount": total_difference,
                }
            )

            for earning in earnings:
                new_earning = copy.deepcopy(earning)
                new_earning["department"] = None
                new_earning["indent"] = 1
                final_output.append(new_earning)

        if deductions:
            total_prev_month = sum(row["total_prev_month"] for row in deductions)
            total = sum(row["total"] for row in deductions)
            total_difference = sum(row["difference_amount"] for row in deductions)
            final_output.append(
                {
                    "department": department,
                    "salary_component": "DEDUCTIONS TOTAL",
                    "total_prev_month": total_prev_month,
                    "total": total,
                    "indent": 0,
                    "is_title": True,
                    "difference_amount": total_difference,
                }
            )

            for deduction in deductions:
                new_deduction = copy.deepcopy(deduction)
                new_deduction["department"] = None
                new_deduction["indent"] = 1
                final_output.append(new_deduction)

    return final_output


def salary_slip_earnings(salary_slips):
    ss_earnings = frappe.db.sql(
        """
        SELECT ss.department, sd.salary_component, sd.parentfield, SUM(sd.amount) as total
        FROM `tabSalary Detail` sd, `tabSalary Slip` ss where sd.parent=ss.name 
        AND sd.parent in (%s)
        AND sd.do_not_include_in_total = 0
        AND sd.parentfield = 'earnings'
        GROUP BY ss.department, sd.salary_component 
        ORDER BY sd.salary_component ASC"""
        % (", ".join(["%s"] * len(salary_slips))),
        tuple([d.name for d in salary_slips]),
        as_dict=1,
    )

    return ss_earnings


def salary_slip_deductions(salary_slips):
    ss_earnings = frappe.db.sql(
        """
        SELECT ss.department, sd.salary_component, sd.parentfield, SUM(sd.amount) as total
        FROM `tabSalary Detail` sd, `tabSalary Slip` ss where sd.parent=ss.name 
        AND sd.parent in (%s)
        AND sd.do_not_include_in_total = 0
        AND sd.parentfield = 'deductions'
        GROUP BY ss.department, sd.salary_component 
        ORDER BY sd.salary_component ASC"""
        % (", ".join(["%s"] * len(salary_slips))),
        tuple([d.name for d in salary_slips]),
        as_dict=1,
    )

    return ss_earnings
