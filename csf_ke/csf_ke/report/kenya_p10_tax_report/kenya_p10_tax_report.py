# # Copyright (c) 2023, Navari Limited and contributors
# # For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    if filters.from_date > filters.to_date:
        frappe.throw(_("From Date cannot be greater than To Date"))

    return get_columns(), get_p10_report_data(filters)


salary_components = [
    'Basic Salary',
    'House Allowance',
    'Transport Allowance',
    'Leave Allowance',
    'Overtime',
    'Gratuity',
    'PAYE',
    'NHIF'
]


def get_columns():
    columns = [
        {
            "fieldname": "employee",
            "label": _("PIN of Employee"),
            "fieldtype": "Link",
            "options": "Employee",
            "width": 150
        },
        {
            "fieldname": "employee_name",
            "label": _("Name of Employee"),
            "fieldtype": "Data",
            "read_only": 1,
            "width": 150
        }
    ]
    for component in salary_components:
        columns.append(
            {
                "fieldname": component.lower().replace(" ", "_"),
                "label": _(component),
                "fieldtype": "Currency",
                "width": 150
            }
        )
    return columns


def get_p10_report_data(filters):
    employee = filters.get("employee")
    company = filters.get("company")

    conditions = " AND ss.docstatus = 1 "
    if company:
        conditions += f" AND ss.company = '{company}'"
    if employee:
        conditions += f" AND ss.employee = '{employee}'"

    ss_p10_tax_deduction_card = frappe.db.sql(f"""
                SELECT
                    ss.employee,
                    ss.employee_name,
                    ss.posting_date,
                    sd.salary_component, 
                    IFNULL(sd.amount,0) as amount 
                FROM `tabSalary Slip` ss
                INNER JOIN `tabSalary Detail` sd ON ss.name=sd.parent
                WHERE sd.salary_component IN ('Basic Salary', 'House Income', 'Transport Allowance','Leave Allowance','Overtime', 'Gratuity', 'PAYE', 'NHIF')
                 {conditions}
                ORDER BY ss.employee
            """, {"employee": employee, "company": company}, as_dict=True)
    print("#" * 40)
    print(ss_p10_tax_deduction_card)
    print("*" * 40)
    print(conditions)

    # Pivot the data into a dictionary where keys are employees and values are dictionaries of salary components
    employee_data = {}
    for row in ss_p10_tax_deduction_card:
        employee_pin = row["employee"]
        employee_name = row["employee_name"]
        salary_component = row["salary_component"]
        amount = row["amount"]

        employee_key = f"{employee_pin}-{employee_name}"

        if employee_key not in employee_data:
            employee_data[employee_key] = {"employee_name": employee_name, "employee": employee_pin}

        employee_data[employee_key][salary_component.lower().replace(" ", "_")] = amount

    # Convert the dictionary into a list of rows for the report
    report_data = []
    for employee_key, components in employee_data.items():
        employee_pin, employee_name = employee_key.split("-")
        row = {"employee": employee_pin, "employee_name": employee_name}
        # print(f"Debug: employee_pin={row['employee']}, employee_name={row['employee_name']}")
        row.update(components)
        report_data.append(row)

    return report_data
