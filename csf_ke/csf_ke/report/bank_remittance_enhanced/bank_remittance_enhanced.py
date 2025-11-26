# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

from functools import reduce

import frappe
from frappe import _, get_all
from frappe.utils import getdate


def execute(filters=None):
    columns = [
        {
            "label": _("Bank Name"),
            "fieldtype": "Data",
            "fieldname": "bank_name",
            "width": 200,
        },
        {
            "label": _("Debit Account No"),
            "fieldtype": "Data",
            "fieldname": "debit_account",
            "width": 200,
        },
        {
            "label": _("Beneficiary Account No"),
            "fieldtype": "Data",
            "fieldname": "beneficiary_account_no",
            "width": 200,
        },
        {
            "label": _("Beneficiary Name"),
            "fieldtype": "Link",
            "fieldname": "beneficiary_name",
            "options": "Employee",
            "width": 200,
        },
    ]

    if frappe.db.has_column("Employee", "ifsc_code"):
        columns.append(
            {
                "label": _("IFSC Code"),
                "fieldtype": "Data",
                "fieldname": "bank_code",
                "width": 100,
            }
        )

    columns += [
        {
            "label": _("Transaction Currency"),
            "fieldtype": "Data",
            "fieldname": "currency",
            "width": 100,
        },
        {
            "label": _("Payment Amount"),
            "fieldtype": "Currency",
            "options": "currency",
            "fieldname": "amount",
            "width": 200,
        },
    ]

    data = []

    accounts = get_bank_accounts()
    payroll_entries = get_payroll_entries(accounts, filters)
    if not payroll_entries:
        return columns, data

    salary_slips = get_salary_slips(payroll_entries)

    if frappe.db.has_column("Employee", "ifsc_code"):
        get_emp_bank_ifsc_code(salary_slips)

    for salary in salary_slips:
        if salary.status == filters.get("salary_slip_status"):
            row = {
                "payroll_no": salary.payroll_entry,
                "debit_account": salary.debit_acc_no,
                "payment_date": frappe.utils.formatdate(
                    salary.modified.strftime("%Y-%m-%d")
                ),
                "bank_name": salary.bank_name,
                "beneficiary_account_no": salary.bank_account_no,
                "bank_code": salary.ifsc_code,
                "beneficiary_name": salary.employee_name,
                "currency": salary.currency
                or frappe.get_cached_value(
                    "Company", filters.company, "default_currency"
                ),
                "amount": salary.net_pay,
            }
            data.append(row)

    return columns, data


def get_bank_accounts():
    accounts = [d.name for d in get_all("Account", filters={"account_type": "Bank"})]
    return accounts


def get_payroll_entries(accounts, filters):
    pe = frappe.qb.DocType("Payroll Entry")

    payroll_filter = [
        pe.number_of_employees > 0,
    ]

    if filters.get("company"):
        payroll_filter.append(pe.company == filters.get("company"))

    if filters.get("from_date"):
        payroll_filter.append(pe.posting_date >= getdate(filters.get("from_date")))

    if filters.get("to_date"):
        payroll_filter.append(pe.posting_date <= getdate(filters.get("to_date")))

    if filters.get("payroll_entry"):
        payroll_filter.append(pe.name == filters.get("payroll_entry"))

    entries = (
        frappe.qb.from_(pe)
        .select(pe.name, pe.payment_account)
        .where(reduce(lambda x, y: x & y, payroll_filter))
        .run(as_dict=True)
    )

    payment_accounts = [d.payment_account for d in entries]

    entries = set_company_account(payment_accounts, entries)
    return entries


def get_salary_slips(payroll_entries):
    payroll = [d.name for d in payroll_entries]
    salary_slips = get_all(
        "Salary Slip",
        filters=[("payroll_entry", "IN", payroll)],
        fields=[
            "modified",
            "net_pay",
            "bank_name",
            "bank_account_no",
            "payroll_entry",
            "employee",
            "employee_name",
            "status",
        ],
    )

    payroll_entry_map = {}
    for entry in payroll_entries:
        payroll_entry_map[entry.name] = entry

    # appending company debit accounts
    for slip in salary_slips:
        if slip.payroll_entry:
            slip["debit_acc_no"] = payroll_entry_map[slip.payroll_entry][
                "company_account"
            ]
        else:
            slip["debit_acc_no"] = None

    return salary_slips


def get_emp_bank_ifsc_code(salary_slips):
    emp_names = [d.employee for d in salary_slips]
    ifsc_codes = get_all("Employee", [("name", "IN", emp_names)], ["ifsc_code", "name"])

    ifsc_codes_map = {code.name: code.ifsc_code for code in ifsc_codes}

    for slip in salary_slips:
        slip["ifsc_code"] = ifsc_codes_map[slip.employee]

    return salary_slips


def set_company_account(payment_accounts, payroll_entries):
    company_accounts = get_all(
        "Bank Account",
        [("account", "in", payment_accounts)],
        ["account", "bank_account_no"],
    )
    company_accounts_map = {}
    for acc in company_accounts:
        company_accounts_map[acc.account] = acc

    for entry in payroll_entries:
        company_account = ""
        if entry.payment_account in company_accounts_map:
            company_account = company_accounts_map[entry.payment_account][
                "bank_account_no"
            ]
        entry["company_account"] = company_account

    return payroll_entries
