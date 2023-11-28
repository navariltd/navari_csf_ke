# # Copyright (c) 2023, Navari Limited and contributors
# # For license information, please see license.txt

import frappe
from frappe import _


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
            "width": 150
        },
        {   
            "fieldname": "employee_name", 
            "label": _("Employee Name"),
            "fieldtype": "Data", 
            "read_only": 1,
            "width": 150
        },
        {   
            "fieldname": "basic_salary", 
            "label": _("Basic Salary"), 
            "fieldtype": "Currency", 
            "width": 150
        },
        {
            "fieldname": "housing_allowance", 
            "label": _("Housing Allowance"), 
            "fieldtype": "Currency", 
            "width": 150
        },
        {
            "fieldname": "transport_allowance", 
            "label": _("Transport Allowance"), 
            "fieldtype": "Currency", 
            "width": 150
         },
        {
            "fieldname": "leave_pay", 
            "label": _("Leave Pay"), 
            "fieldtype": "Currency", 
            "width": 150
        },
        {
            "fieldname": "overtime", 
            "label": _("Overtime"), 
            "fieldtype": "Currency", 
            "width": 150
        },
        {
            "fieldname": "lump_sum_payment", 
            "label": _("Lump Sum Payment"), 
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "paye", 
            "label": _("PAYE"), 
            "fieldtype": "Currency",
            "width": 150
        },
    ]

    return columns


def get_p10_report_data(filters):
    employee = filters.get("employee")
    company = filters.get("company")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    conditions = " AND ss.docstatus = 1 "
    if company:
        conditions += f" AND ss.company = '{company}'"
    if employee:
        conditions += f" AND ss.employee = '{employee}'"
    if from_date and to_date:
        conditions += f" AND ss.posting_date BETWEEN '{from_date}' AND '{to_date}'"
   

    salary_components = ['Basic Salary','House Allowance','Transport Allowance','Leave Allowance','Overtime','Commissions','PAYE' ]

    p10_salary_component = ", ".join([f"'{component}'" for component in salary_components])

    ss_p10_tax_deduction_card = frappe.db.sql(f"""
                SELECT
                    emp.tax_id,
                    ss.employee_name,
                    ss.posting_date,
                    sd.salary_component, 
                    IFNULL(sd.amount,0) as amount 
                FROM `tabSalary Slip` ss
                INNER JOIN `tabSalary Detail` sd ON ss.name=sd.parent
                INNER JOIN `tabEmployee` emp ON emp.name=ss.employee
                WHERE sd.salary_component IN ({p10_salary_component})
                 {conditions}
                ORDER BY ss.employee
            """, as_dict=True)


    employee_data = {}
    for row in ss_p10_tax_deduction_card:
        employee_pin = row["tax_id"]
        employee_name = row["employee_name"]
        salary_component = row["salary_component"]
        amount = row["amount"]

        if salary_component is not None and amount is not None:
            employee_key = f"{employee_pin}-{employee_name}"

            if employee_key not in employee_data:
                employee_data[employee_key] = {"employee_name": employee_name, "tax_id": employee_pin}

            if salary_component is not None:
                employee_data[employee_key][salary_component.lower().replace(" ", "_")] = amount

    report_data = []
    for employee_key, components in employee_data.items():
        employee_pin, employee_name = employee_key.split("-", 1)
        row = {"tax_id": employee_pin, "employee_name": employee_name}
        row.update(components)
        report_data.append(row)

    return report_data