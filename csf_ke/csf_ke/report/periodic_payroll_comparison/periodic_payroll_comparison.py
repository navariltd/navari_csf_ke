# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt
from collections import defaultdict
import copy
import calendar

import frappe
import erpnext
from frappe.utils import getdate, get_first_day, get_last_day
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

    loans = salary_slip_loans_data(old_salary_slips, new_salary_slips)

    grouped_data = []

    if earnings_data and deductions_data:
        if filters.get("based_on") == "Department":
            grouped_data = get_department_breakdown(
                filters,
                earnings_data,
                deductions_data,
                loans,
            )

        elif filters.get("based_on") == "Employee":
            grouped_data = get_comparison_per_employee(
                filters, earnings_data, deductions_data, loans
            )
        else:
            grouped_data = get_comparison_per_company(
                filters,
                earnings_data,
                deductions_data,
                old_ss_count,
                new_ss_count,
                loans,
            )

    return grouped_data


def salary_slip_loans_data(old_salary_slips, new_salary_slips):
    old_ss_data = get_salary_slip_loans(old_salary_slips)
    new_ss_data = get_salary_slip_loans(new_salary_slips)

    if old_ss_data:
        old_ss_data = [
            {**record, "parentfield": "previous_loans"}
            for record in old_ss_data
            if record["parentfield"] == "loans"
        ]

    if new_ss_data:
        new_ss_data = [
            {**record, "parentfield": "current_loans"}
            for record in new_ss_data
            if record["parentfield"] == "loans"
        ]

    return old_ss_data + new_ss_data


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

    if filters.get("based_on") == "Company":
        new_columns = [
            {
                "fieldname": "salary_component",
                "label": _("Salary Component"),
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
        """.format(conditions=conditions),
        values=params,
        as_dict=1,
    )

    return salary_slips


def get_number_of_employees(salary_slips):
    return len(salary_slips)


def salary_slip_earnings(salary_slips):
    slip_names = [d.name for d in salary_slips]
    placeholders = ", ".join(["%s"] * len(slip_names))

    query = f"""
        SELECT ss.employee_name As employee, ss.department, ss.company, sd.salary_component, sd.parentfield, SUM(sd.amount) AS total
        FROM `tabSalary Slip` ss
        JOIN `tabSalary Detail` sd
        ON sd.parent=ss.name
        WHERE sd.parent in ({placeholders})
        AND sd.do_not_include_in_total = 0
        AND sd.parentfield = 'earnings'
        GROUP BY ss.employee, ss.department, ss.company, sd.salary_component
        ORDER BY sd.salary_component ASC"""

    return frappe.db.sql(query, tuple(slip_names), as_dict=1)


def salary_slip_deductions(salary_slips):
    slip_names = [d.name for d in salary_slips]
    placeholders = ", ".join(["%s"] * len(slip_names))

    query = f"""
        SELECT ss.employee_name AS employee, ss.department, ss.company, sd.salary_component, sd.parentfield, SUM(sd.amount) AS total
        FROM `tabSalary Slip` ss
        JOIN `tabSalary Detail` sd
        ON sd.parent=ss.name
        WHERE sd.parent in ({placeholders})
        AND sd.do_not_include_in_total = 0
        AND sd.parentfield = 'deductions'
        GROUP BY ss.employee, ss.department, ss.company, sd.salary_component
        ORDER BY sd.salary_component ASC"""

    return frappe.db.sql(query, tuple(slip_names), as_dict=1)


def get_salary_slip_loans(salary_slips):
    if not salary_slips:
        return []
    slip_names = [d.name for d in salary_slips]
    placeholders = ", ".join(["%s"] * len(slip_names))

    query = f"""
        SELECT ss.employee_name as employee, ss.department, ss.company, ssd.parentfield, SUM(ssd.total_payment) AS total_payment
        FROM `tabSalary Slip` ss
        JOIN `tabSalary Slip Loan` ssd
        ON ssd.parent = ss.name
        WHERE ssd.parent in ({placeholders})
        AND ssd.parentfield = 'loans'
        GROUP BY ss.employee, ss.department, ss.company
        ORDER BY ss.employee ASC"""

    return frappe.db.sql(query, tuple(slip_names), as_dict=1)


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


def get_comparison_per_company(
    filters, earnings_data, deductions_data, old_ss_count, new_ss_count, loans
):
    if loans:
        loans = get_company_wise_loan_totals(loans)

    all_data = earnings_data + deductions_data + (loans if loans else [])
    grouped = defaultdict(lambda: {"earnings": [], "deductions": [], "loans": []})

    for row in all_data:
        comp = row["company"]
        pf = row["parentfield"]
        grouped[comp][pf].append(row)

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

    for company in sorted(grouped.keys()):
        earnings = grouped[company]["earnings"]
        deductions = grouped[company]["deductions"]
        loans = grouped[company]["loans"]

        if earnings and not filters.get("component_type") == "Deductions":
            total_prev_month = sum(row["total_prev_month"] for row in earnings) or 0
            total = sum(row["total"] for row in earnings) or 0
            total_difference = total - total_prev_month
            final_output.append(
                {
                    "company": company,
                    "salary_component": "EARNINGS",
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

            combined_totals = get_components_total(deductions)

            if loans:
                loan = loans[0]
                loan_difference = loan.get("total", 0) - loan.get("total_prev_month", 0)
                total = total + loan.get("total", 0)
                total_prev_month = total_prev_month + loan.get("total_prev_month", 0)

                final_output.append(
                    {
                        "company": (
                            company
                            if filters.get("component_type") == "Deductions"
                            else None
                        ),
                        "salary_component": "DEDUCTIONS",
                        "total_prev_month": total_prev_month,
                        "total": total,
                        "is_title": True,
                        "difference_amount": total_difference,
                    }
                )

                final_output.extend(combined_totals)

                final_output.append(
                    {
                        "company": None,
                        "salary_component": "Loans",
                        "total_prev_month": loan.get("total_prev_month", 0),
                        "total": loan.get("total", 0),
                        "difference_amount": loan_difference,
                    }
                )
            else:
                final_output.append(
                    {
                        "company": (
                            company
                            if filters.get("component_type") == "Deductions"
                            else None
                        ),
                        "salary_component": "DEDUCTIONS",
                        "total_prev_month": total_prev_month,
                        "total": total,
                        "is_title": True,
                        "difference_amount": total_difference,
                    }
                )

                final_output.extend(combined_totals)

    return final_output


def get_department_breakdown(filters, earnings_data, deductions_data, loans):
    if loans:
        loans = get_department_wise_loan_totals(loans)
    all_data = earnings_data + deductions_data + (loans if loans else [])

    grouped = defaultdict(lambda: {"earnings": [], "deductions": [], "loans": []})

    for row in all_data:
        dept = row.get("department")
        pf = row["parentfield"]

        if dept is None:
            grouped["Others"][pf].append(row)
        else:
            grouped[dept][pf].append(row)

    final_output = []

    for department in grouped.keys():
        earnings = grouped[department]["earnings"]
        deductions = grouped[department]["deductions"]
        loans = grouped[department]["loans"]

        if earnings and not filters.get("component_type") == "Deductions":
            final_output.append(
                {
                    "department": department,
                    "salary_component": "SALARY COMPONENT",
                    "total_prev_month": None,
                    "total": None,
                    "is_title": True,
                    "difference_amount": None,
                }
            )

            combined_totals = get_components_total(earnings)
            final_output.extend(combined_totals)

        if deductions and not filters.get("component_type") == "Earnings":
            if filters.get("component_type") == "Deductions":
                final_output.append(
                    {
                        "department": department,
                        "salary_component": "SALARY COMPONENT",
                        "total_prev_month": None,
                        "total": None,
                        "is_title": True,
                        "difference_amount": None,
                    }
                )

            combined_totals = get_components_total(deductions)
            final_output.extend(combined_totals)

            if loans:
                loan = loans[0]
                final_output.append(
                    {
                        "department": None,
                        "salary_component": "Loans",
                        "total_prev_month": loan.get("total_prev_month", 0),
                        "total": loan.get("total", 0),
                        "difference_amount": loan.get("total", 0)
                        - loan.get("total_prev_month", 0),
                    }
                )

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


def get_comparison_per_employee(filters, earnings_data, deductions_data, loans):
    if loans:
        loans = get_employee_wise_loan_totals(loans)
    all_data = earnings_data + deductions_data + (loans if loans else [])

    grouped = defaultdict(lambda: {"earnings": [], "deductions": [], "loans": []})

    for row in all_data:
        dept = row.get("department")
        pf = row["parentfield"]

        if dept is None:
            key = ("Others", row["employee"])
            grouped[key][pf].append(row)
        else:
            key = (dept, row["employee"])
            grouped[key][pf].append(row)

    final_output = []

    for emp in sorted(grouped.keys()):
        earnings = grouped[emp]["earnings"]
        deductions = grouped[emp]["deductions"]
        loans = grouped[emp]["loans"]

        if earnings and not filters.get("component_type") == "Deductions":
            final_output.append(
                {
                    "department": emp[0],
                    "employee": emp[1],
                    "salary_component": "SALARY COMPONENT",
                    "total_prev_month": None,
                    "total": None,
                    "is_title": True,
                    "difference_amount": None,
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
            if filters.get("component_type") == "Deductions":
                final_output.append(
                    {
                        "department": emp[0],
                        "employee": emp[1],
                        "salary_component": "SALARY COMPONENT",
                        "total_prev_month": None,
                        "is_title": True,
                        "total": None,
                        "difference_amount": None,
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

            if loans:
                loan = loans[0]
                final_output.append(
                    {
                        "department": None,
                        "employee": None,
                        "salary_component": "Loan",
                        "total_prev_month": loan.get("total_prev_month", 0),
                        "total": loan.get("total", 0),
                        "difference_amount": loan.get("total", 0)
                        - loan.get("total_prev_month", 0),
                    }
                )

    return final_output


def get_department_wise_loan_totals(loans):
    if not loans:
        return []

    department_totals = defaultdict(
        lambda: {
            "department": "",
            "company": "",
            "total_prev_month": 0.0,
            "total": 0.0,
            "parentfield": "loans",
        }
    )

    for record in loans:
        dept = record["department"]

        if not department_totals[dept]["department"]:
            department_totals[dept]["department"] = dept
            department_totals[dept]["company"] = record["company"]

        if record["parentfield"] == "previous_loans":
            department_totals[dept]["total_prev_month"] += record["total_payment"]
        elif record["parentfield"] == "current_loans":
            department_totals[dept]["total"] += record["total_payment"]

    result = list(department_totals.values())

    return result


def get_company_wise_loan_totals(loans):
    if not loans:
        return []

    company_totals = defaultdict(
        lambda: {
            "company": "",
            "total_prev_month": 0.0,
            "total": 0.0,
            "parentfield": "loans",
        }
    )

    for record in loans:
        comp = record["company"]

        if not company_totals[comp]["company"]:
            company_totals[comp]["company"] = comp

        if record["parentfield"] == "previous_loans":
            company_totals[comp]["total_prev_month"] += record["total_payment"]
        elif record["parentfield"] == "current_loans":
            company_totals[comp]["total"] += record["total_payment"]

    result = list(company_totals.values())

    return result


def get_employee_wise_loan_totals(loans):
    if not loans:
        return []

    employee_totals = defaultdict(
        lambda: {
            "department": "",
            "employee": "",
            "total_prev_month": 0.0,
            "total": 0.0,
            "parentfield": "loans",
        }
    )

    for record in loans:
        emp = record["employee"]

        if not employee_totals[emp]["employee"]:
            employee_totals[emp]["employee"] = emp
            employee_totals[emp]["department"] = record["department"]

        if record["parentfield"] == "previous_loans":
            employee_totals[emp]["total_prev_month"] += record["total_payment"]
        elif record["parentfield"] == "current_loans":
            employee_totals[emp]["total"] += record["total_payment"]

    result = list(employee_totals.values())

    return result
