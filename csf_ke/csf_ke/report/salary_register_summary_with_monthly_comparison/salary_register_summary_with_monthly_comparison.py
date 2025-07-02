# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt
from datetime import datetime, timedelta
from calendar import monthrange

import frappe
import erpnext
from frappe.utils import flt, cstr, getdate, get_first_day, get_last_day
from frappe import _
from frappe.utils.nestedset import get_descendants_of

import calendar


def execute(filters=None):
    company_currency = erpnext.get_company_currency(filters.get("company"))

    validate_date_filters(filters)

    columns = get_columns(filters)
    data = group_per_department(filters, company_currency)

    return columns, data


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

        days_in_the_next_month = monthrange(next_year, next_month)[
            1
        ]  # pick the second index (contains days)
        expected_end = datetime(next_year, next_month, days_in_the_next_month)

    return end == expected_end


def validate_date_filters(filters):
    start = filters.get("from_date")
    end = filters.get("to_date")

    if not consecutive_months(start, end):
        frappe.throw(
            "Start Date must be the first day of the selected month and End Date must be the last day of the next consecutive month."
        )


def get_columns(filters):
    old_date = getdate(filters.get("from_date"))
    new_date = getdate(filters.get("to_date"))

    old_month_name = calendar.month_name[old_date.month]
    new_month_name = calendar.month_name[new_date.month]

    columns = [
        {
            "fieldname": "department",
            "label": _("Department"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "salary_component",
            "label": _("Salary Component"),
            "fieldtype": "Data",
            "width": 150,
        },
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
            "width": 150,
            "precision": 2,
        },
        {
            "fieldname": "difference_amount",
            "label": _("Difference Amount"),
            "fieldtype": "Data",
            "width": 150,
        },
    ]
    return columns


def get_conditions(filters, company_currency):
    conditions = ""
    doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

    if filters.get("docstatus"):
        # conditions += "docstatus = {0}".format(doc_status[filters.get("docstatus")])
        conditions += "docstatus = 1"

    print("DOCSTATUS", conditions)

    if filters.get("from_date"):
        conditions += " and start_date >= %(from_date)s"
    if filters.get("to_date"):
        conditions += " and end_date <= %(to_date)s"
    if filters.get("company"):
        conditions += " and company = %(company)s"
    if filters.get("employee"):
        conditions += " and employee = %(employee)s"
    if filters.get("currency") and filters.get("currency") != company_currency:
        conditions += " and currency = %(currency)s"
    if filters.get("department") and filters.get("company"):
        department_list = get_departments(
            filters.get("department"), filters.get("company")
        )
        conditions += (
            "and department in ("
            + ",".join(("'" + n + "'" for n in department_list))
            + ")"
        )

    return conditions, filters


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
    pass


def group_per_department(filters, company_currency):
    # temp_old_date = getdate(filters.get("from_date"))
    # old_end_date = datetime(temp_old_date.year, temp_old_date.month + 1, 1) - timedelta(days=1)
    old_end_date = get_last_day(getdate(filters.get("from_date")))
    new_start_date = get_first_day(getdate(filters.get("to_date")))

    # print("OLD, NEW", old_end_date, new_start_date)

    old_ss_filters = filters.copy()
    old_ss_filters.update(
        {"start_date": filters.get("from_date"), "end_date": old_end_date}
    )

    new_ss_filters = filters.copy()
    new_ss_filters.update(
        {"start_date": new_start_date, "end_date": filters.get("to_date")}
    )

    # print("FILTERS", new_ss_filters)

    # Get previous month - 1 salary slips
    old_salary_slips = get_salary_slips(old_ss_filters, company_currency)

    # Get previous month salary slips
    new_salary_slips = get_salary_slips(new_ss_filters, company_currency)

    if old_salary_slips and new_salary_slips:
        data = get_earnings_data(old_salary_slips, new_salary_slips)

        return data
        # get both earnings previous - 1 and previous and compare

        # get both deductions previous - 1 and previous compare


def salary_slip_earnings(salary_slips):
    # TODO: group by employee conditionally
    ss_earnings = frappe.db.sql(
        """
        SELECT ss.department, sd.salary_component, SUM(sd.amount) as total
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


def get_earnings_data(
    old_salary_slips,
    new_salary_slips,
):
    data = []
    old_earnings = salary_slip_earnings(old_salary_slips)
    new_earnings = salary_slip_earnings(new_salary_slips)

    total_old_earning = sum(flt(d.total) for d in old_earnings)
    total_new_earning = sum(flt(d.total) for d in new_earnings)
    unique_old_earnings_salary_components = []
    unique_new_earnings_salary_components = []

    for new_earning_row in new_earnings:

        for old_earning_row in old_earnings:
            if new_earning_row.get("department") == old_earning_row.get(
                "department"
            ) and new_earning_row.get("salary_component") == old_earning_row.get(
                "salary_component"
            ):
                earn_amount_diff = flt(
                    new_earning_row.get("total") - old_earning_row.get("total"),
                    2,
                )
                result = ""
                if earn_amount_diff > 0:
                    result = "+" + cstr(earn_amount_diff)
                elif earn_amount_diff < 0:
                    result = "-" + cstr(abs(earn_amount_diff))
                else:
                    result = "0"

                new_earning_row.update(
                    {
                        "total_prev_month": old_earning_row.get("total"),
                        "difference_amount": result,
                    }
                )
                data.append(new_earning_row)

                unique_new_earnings_salary_components.append(
                    {
                        "department": new_earning_row.get("department"),
                        "salary_component": new_earning_row.get("salary_component"),
                    }
                )
                unique_old_earnings_salary_components.append(
                    {
                        "department": old_earning_row.get("department"),
                        "salary_component": old_earning_row.get("salary_component"),
                    }
                )

        cur_row = {
            "department": new_earning_row.get("department"),
            "salary_component": new_earning_row.get("salary_component"),
        }

        if cur_row not in unique_new_earnings_salary_components:
            unique_old_earnings_salary_components.append(
                {
                    "department": new_earning_row.get("department"),
                    "salary_component": new_earning_row.get("salary_component"),
                }
            )

            data.append(
                {
                    "department": new_earning_row.get("department"),
                    "salary_component": new_earning_row.get("salary_component"),
                    "total_prev_month": 0,
                    "total_cur_month": new_earning_row.get("total"),
                    "difference_amount": "+" + cstr(new_earning_row.get("total")),
                }
            )

    for row in old_earnings:
        old_row = {
            "department": row.get("department"),
            "salary_component": row.get("salary_component"),
        }
        if old_row not in unique_old_earnings_salary_components:
            data.append(
                {
                    "department": row.get("department"),
                    "salary_component": row.get("salary_component"),
                    "total_prev_month": row.get("total") or 0,
                    "total": 0,
                    "difference_amount": "-" + cstr(row.get("total")),
                }
            )
    # total_earn_amount_diff = flt(total_cur_earning - total_prev_earning, 2)
    # d = ""
    # if total_earn_amount_diff > 0:
    #     d = "+" + cstr(total_earn_amount_diff)
    # elif total_earn_amount_diff < 0:
    #     d = "-" + cstr(abs(total_earn_amount_diff))
    # else:
    #     d = "0"

    # data.append(
    #     {
    #         "department": "",
    #         "salary_component": "TOTAL ALLOWANCES",
    #         "total_prev_month": total_prev_earning,
    #         "total_cur_month": total_cur_earning,
    #         "difference_amount": d,
    #     }
    # )

    return data  # total_prev_earning, total_cur_earning


def group_per_employee():
    pass
