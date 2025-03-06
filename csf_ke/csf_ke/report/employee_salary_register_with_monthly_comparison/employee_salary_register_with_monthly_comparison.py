# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from erpnext import get_company_currency
from frappe import _
from frappe.utils import getdate, flt, cstr, cint
from frappe.utils.nestedset import get_descendants_of

import calendar


def execute(filters):
    company_currency = get_company_currency(filters.get("company"))

    prev_first_date, prev_last_date, prev_month, prev_year = get_prev_month_date(
        filters
    )
    cur_month_name = calendar.month_name[getdate(filters.from_date).month]
    cur_year = getdate(filters.from_date).year

    prev_month_name = calendar.month_name[prev_month]
    columns = get_columns(prev_month_name, cur_month_name, prev_year, cur_year)

    prev_salary_slips = get_prev_salary_slips(
        filters, company_currency, prev_first_date, prev_last_date
    )
    cur_salary_slips = get_cur_salary_slips(filters, company_currency)

    if len(prev_salary_slips) == 0:
        return columns, cur_salary_slips

    if len(cur_salary_slips) == 0:
        return columns, prev_salary_slips

    data = get_data(prev_salary_slips, cur_salary_slips)

    return columns, data


def get_columns(prev_month_name, cur_month_name, prev_year, cur_year):
    columns = [
        {
            "fieldname": "employee",
            "label": _("Employee"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "employee_name",
            "label": _("Employee Name"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "department",
            "label": _("Department"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "prev_gross_pay",
            "label": _("Gross Pay {0}-{1}".format(prev_month_name, prev_year)),
            "fieldtype": "Float",
            "width": 250,
            "precision": 2,
        },
        {
            "fieldname": "cur_gross_pay",
            "label": _("Gross Pay {0}-{1}".format(cur_month_name, cur_year)),
            "fieldtype": "Float",
            "width": 250,
            "precision": 2,
        },
        {
            "fieldname": "gross_difference_amount",
            "label": _("Gross Difference Amount"),
            "fieldtype": "Data",
            "width": 150,
        },
    ]
    return columns


def get_data(prev_ss, cur_ss):
    """Merge employee details from current and previous months"""

    data = []
    unique_cur_employees = []
    unique_prev_employees = []

    for cur_ss_row in cur_ss:
        for prev_ss_row in prev_ss:
            if cur_ss_row.employee == prev_ss_row.employee and flt(
                cur_ss_row.cur_gross_pay, 2
            ) == flt(prev_ss_row.prev_gross_pay, 2):
                unique_prev_employees.append(prev_ss_row.employee)
                unique_cur_employees.append(cur_ss_row.employee)

            elif cur_ss_row.employee == prev_ss_row.employee and flt(
                cur_ss_row.cur_gross_pay, 2
            ) != flt(prev_ss_row.prev_gross_pay, 2):
                unique_prev_employees.append(prev_ss_row.employee)
                unique_cur_employees.append(cur_ss_row.employee)

                gross_amount_diff = flt(
                    flt(cur_ss_row.cur_gross_pay) - flt(prev_ss_row.prev_gross_pay), 2
                )

                cur_ss_row.update(
                    {
                        "prev_gross_pay": prev_ss_row.prev_gross_pay,
                        "cur_gross_pay": cur_ss_row.cur_gross_pay,
                        "gross_difference_amount": get_difference_amount_detail(
                            gross_amount_diff
                        ),
                    }
                )
                data.append(cur_ss_row)

        # Update employee details for the current month if the employee is not in the list of employees for previous month
        if cur_ss_row.employee not in unique_cur_employees:
            unique_cur_employees.append(cur_ss_row.employee)
            cur_ss_row.update(
                {
                    "prev_gross_pay": 0,
                    "cur_gross_pay": cur_ss_row.cur_gross_pay,
                    "gross_difference_amount": "+ " + str(cur_ss_row.cur_gross_pay),
                }
            )

            data.append(cur_ss_row)

    return update_unique_prev_employee_ss_details(data, prev_ss, unique_prev_employees)


def update_unique_prev_employee_ss_details(data, prev_ss, unique_prev_employees):
    """ "Updating unique employee details of previous month if the employee is not in the list of employees for the current month"""

    for prev_row in prev_ss:
        if prev_row.employee not in unique_prev_employees:
            unique_prev_employees.append(prev_row.employee)
            prev_row.update(
                {
                    "prev_gross_pay": prev_row.prev_gross_pay,
                    "cur_gross_pay": 0,
                    "gross_difference_amount": "- " + str(prev_row.prev_gross_pay),
                }
            )

            data.append(prev_row)

    # add total row for gross of previous month and current month
    total_prev_gross = sum([d.prev_gross_pay for d in data])
    total_cur_gross = sum([d.cur_gross_pay for d in data])
    total_diff = get_difference_amount_detail(
        flt(flt(total_cur_gross) - flt(total_prev_gross), 2)
    )
    data.append({"employee_name": ""})
    data.append(
        {
            "employee_name": "Total",
            "prev_gross_pay": total_prev_gross,
            "cur_gross_pay": total_cur_gross,
            "gross_difference_amount": total_diff,
        }
    )
    return data


def get_difference_amount_detail(bsc_amount_diff):
    """Show + or - sign on the amount difference between current and previous month"""

    result = ""
    if bsc_amount_diff > 0:
        result = "+" + cstr(bsc_amount_diff)
    elif bsc_amount_diff < 0:
        result = "-" + cstr(abs(bsc_amount_diff))
    else:
        result = "0"
    return result


def get_prev_salary_slips(filters, company_currency, prev_first_date, prev_last_date):
    """Get submitted salary slips for precious month"""

    custom_filters = filters
    custom_filters.update(
        {"prev_first_date": prev_first_date, "prev_last_date": prev_last_date}
    )
    prev_conditions = get_prev_conditions(custom_filters, company_currency)
    prev_salary_slips = frappe.db.sql(
        """
		select name, employee, employee_name, department, gross_pay as prev_gross_pay from `tabSalary Slip` where %s
		order by employee"""
        % prev_conditions,
        filters,
        as_dict=1,
    )

    return prev_salary_slips or []


def get_cur_salary_slips(filters, company_currency):
    """Get salary slips for the current month"""

    filters.update(
        {"from_date": filters.get("from_date"), "to_date": filters.get("to_date")}
    )
    conditions, filters = get_cur_conditions(filters, company_currency)
    salary_slips = frappe.db.sql(
        """
		select name, employee, employee_name, department, gross_pay as cur_gross_pay from `tabSalary Slip` where %s
        order by employee"""
        % conditions,
        filters,
        as_dict=1,
    )

    return salary_slips or []


def get_prev_month_date(filters):
    """Get date deatils for previous month"""

    prev_month = getdate(filters.from_date).month - 1
    prev_year = getdate(filters.from_date).year

    if prev_month == 0:
        prev_month = 12
        prev_year = prev_year - 1

    prev_first_date = getdate(str(prev_year) + "-" + str(prev_month) + "-" + "01")
    prev_last_date = getdate(
        str(prev_year)
        + "-"
        + str(prev_month)
        + "-"
        + "{0}".format(calendar.monthrange(prev_year, prev_month)[1])
    )

    return prev_first_date, prev_last_date, prev_month, prev_year


def get_prev_conditions(filters, company_currency):
    """Conditions that will be used to get salary slips for previous month"""

    # this is get submitted salary slips for the previous month
    conditions = "docstatus <= 1"

    if filters.get("prev_first_date"):
        conditions += " and start_date >= %(prev_first_date)s"
    if filters.get("prev_last_date"):
        conditions += " and end_date <= %(prev_last_date)s"
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

    return conditions


def get_cur_conditions(filters, company_currency):
    """Conditions that will be used to get salary slips for current month"""

    conditions = ""
    doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

    if filters.get("docstatus"):
        conditions += "docstatus = {0}".format(doc_status[filters.get("docstatus")])

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
