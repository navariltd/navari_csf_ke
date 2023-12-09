# Copyright (c) 2022, Navari Limited and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe.utils import flt
from frappe import _
from functools import reduce 

def execute(filters=None):
	if not filters: filters = {}
	currency = None
	if filters.get('currency'):
		currency = filters.get('currency')
	company_currency = erpnext.get_company_currency(filters.get("company"))
	salary_slips = get_salary_slips(filters, company_currency)
	if not salary_slips: return [], []

	columns, earning_types, ded_types = get_columns(salary_slips)
	ss_earning_map = get_ss_earning_map(salary_slips, currency, company_currency)
	ss_ded_map = get_ss_ded_map(salary_slips,currency, company_currency)
	doj_map = get_employee_doj_map()

	data = []
	for ss in salary_slips:
		emp_det = doj_map.get(ss.employee)
		if not emp_det:
			continue

		row = [ss.name, ss.employee, ss.employee_name, emp_det.date_of_joining, emp_det.national_id, emp_det.nssf_no, emp_det.nhif_no, emp_det.tax_id, 
		ss.bank_name, ss.bank_account_no, ss.branch, ss.department, ss.designation,
		ss.company, ss.start_date, ss.end_date, ss.leave_without_pay, ss.payment_days]

		if ss.branch is not None: columns[3] = columns[3].replace('-1','120')
		if ss.department is not None: columns[4] = columns[4].replace('-1','120')
		if ss.designation is not None: columns[5] = columns[5].replace('-1','120')
		if ss.leave_without_pay is not None: columns[9] = columns[9].replace('-1','130')


		for e in earning_types:
			row.append(ss_earning_map.get(ss.name, {}).get(e))

		if currency == company_currency:
			row += [flt(ss.gross_pay) * flt(ss.exchange_rate)]
		else:
			row += [ss.gross_pay]

		for d in ded_types:
			row.append(ss_ded_map.get(ss.name, {}).get(d))

		row.append(ss.total_loan_repayment)

		if currency == company_currency:
			row += [flt(ss.total_deduction) * flt(ss.exchange_rate), flt(ss.net_pay) * flt(ss.exchange_rate)]
		else:
			row += [ss.total_deduction, ss.net_pay]
		row.append(currency or company_currency)
		data.append(row)

	return columns, data

def get_columns(salary_slips):
	"""
	columns = [
		_("Salary Slip ID") + ":Link/Salary Slip:150",
		_("Employee") + ":Link/Employee:120",
		_("Employee Name") + "::140",
		_("Date of Joining") + "::80",
		_("National ID") + "::90",
		_("NSSF No") + "::90",
		_("NHIF No") + "::90",
		_("KRA Pin") + "::100",
		_("Bank Name") + ":Link/Salary Slip:100",
		_("Bank Account No") + ":Link/Salary Slip:120",		
		_("Branch") + ":Link/Branch:120",
		_("Department") + ":Link/Department:120",
		_("Designation") + ":Link/Designation:120",
		_("Company") + ":Link/Company:120",
		_("Start Date") + "::80",
		_("End Date") + "::80",
		_("Leave Without Pay") + ":Float:130",
		_("Payment Days") + ":Float:120",
		_("Currency") + ":Link/Currency:80"
	]
	"""
	columns = [
		_("Salary Slip ID") + ":Link/Salary Slip:150",_("Employee") + ":Link/Employee:120", _("Employee Name") + "::140",
		_("Date of Joining") + "::80",_("National ID") + "::90",_("NSSF No") + "::90",_("NHIF No") + "::90",
		_("KRA Pin") + "::100",_("Bank Name") + ":Link/Salary Slip:100",_("Bank Account No") + ":Link/Salary Slip:120",
		_("Branch") + ":Link/Branch:120", _("Department") + ":Link/Department:120",
		_("Designation") + ":Link/Designation:120", _("Company") + ":Link/Company:120", _("Start Date") + "::80",
		_("End Date") + "::80", _("Leave Without Pay") + ":Float:70", _("Payment Days") + ":Float:120"
	]

	salary_components = {_("Earning"): [], _("Deduction"): []}
	
	salary_detail_doc=frappe.qb.DocType("Salary Detail")
	salary_component_doc=frappe.qb.DocType("Salary Component")
	salary_component_query = frappe.qb.from_(salary_detail_doc) \
		.inner_join(salary_component_doc) \
		.on(salary_detail_doc.salary_component == salary_component_doc.name) \
		.select(
			frappe.qb.functions("Distinct", salary_detail_doc.salary_component).as_("salary_component"),
			salary_component_doc.type.as_("type")
		)
	salary_slips = [d.name for d in salary_slips]  

	# Constructing the OR conditions for names in salary_slips
	conditions = [
		salary_detail_doc.parent.like("%" + name + "%") for name in salary_slips
	]

	# Combining the conditions with OR logic
	if conditions:
		combined_condition = conditions[0] if len(conditions) == 1 else reduce(lambda x, y: x | y, conditions[1:], conditions[0])
		salary_component_query = salary_component_query.where(combined_condition)
  
	salary_components_data = salary_component_query.run(as_dict=True)
	
	for component in salary_components_data:
		salary_components[_(component.type)].append(component.salary_component)
	
	columns = columns + [(e + ":Currency:120") for e in salary_components[_("Earning")]] + \
		[_("Gross Pay") + ":Currency:120"] + [(d + ":Currency:120") for d in salary_components[_("Deduction")]] + \
		[_("Loan Repayment") + ":Currency:120", _("Total Deduction") + ":Currency:120", _("Net Pay") + ":Currency:120"]

	return columns, salary_components[_("Earning")], salary_components[_("Deduction")]

def get_salary_slips(filters, company_currency):
	filters.update({"from_date": filters.get("from_date"), "to_date":filters.get("to_date")})
	salary_slip_doc=frappe.qb.DocType("Salary Slip")
	salary_slip_query = frappe.qb.from_(salary_slip_doc).select("*").orderby(salary_slip_doc.employee)
	salary_slip_query = get_conditions(salary_slip_query, filters, company_currency, salary_slip_doc)
	salary_slips = salary_slip_query.run(as_dict=True)
	
	return salary_slips or []

def get_conditions(query, filters, company_currency, salary_slip):
	doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

	for filter_key, filter_value in filters.items():
		if filter_key == "from_date":
			query = query.where(salary_slip.start_date == filter_value)
		if filter_key == "to_date":
			query = query.where(salary_slip.end_date == filter_value)
		if filter_key == "company":
			query = query.where(salary_slip.company == filter_value)
		if filter_key == "currency" and filter_value != company_currency:
			query = query.where(salary_slip.currency == filter_value)
		if filter_key == "docstatus":
			query = query.where(salary_slip.docstatus == doc_status.get(filter_value, 0))
		if filter_key == "employee":
			query = query.where(salary_slip.employee == filter_value)

	return query

def get_employee_doj_map():
	doj_map = frappe._dict()
	employee=frappe.qb.DocType("Employee")
	employee_query=frappe.qb.from_(employee).select(
		employee.name.as_("name"),
		employee.date_of_joining.as_("date_of_joining"),
		employee.national_id.as_("national_id"),
		employee.nssf_no.as_("nssf_no"),
		employee.nhif_no.as_("nhif_no"),
		employee.tax_id.as_("tax_id")
	)
	
	for d in employee_query.run(as_dict=True):
		doj_map.setdefault(d.name, d)
	return doj_map

def get_ss_deduction_and_earnings(salary_slips, currency, company_currency, is_earning=True):
    salary_slips = [d.name for d in salary_slips]
    salary_slip_doc = frappe.qb.DocType("Salary Slip")
    salary_detail_doc = frappe.qb.DocType("Salary Detail")

    # Building the query
    salary_slip_query = frappe.qb.from_(salary_slip_doc) \
        .inner_join(salary_detail_doc) \
        .on(salary_slip_doc.name == salary_detail_doc.parent) \
        .select(
            salary_detail_doc.parent,
            salary_slip_doc.name.as_("salary_slip_name"),
            salary_detail_doc.salary_component.as_("salary_component"),
            salary_detail_doc.amount.as_("amount"),
            salary_slip_doc.exchange_rate.as_("exchange_rate"),
            salary_slip_doc.name
        )

    # Constructing the OR conditions for names in salary_slips
    conditions = [
        salary_detail_doc.parent.like("%" + name + "%") for name in salary_slips
    ]

    # Combining the conditions with OR logic
    if conditions:
        combined_condition = conditions[0] if len(conditions) == 1 else reduce(lambda x, y: x | y, conditions[1:], conditions[0])
        salary_slip_query = salary_slip_query.where(combined_condition)

    salary_slip_records = salary_slip_query.run(as_dict=True)

    ss_map = {}
    for d in salary_slip_records:
        ss_map.setdefault(d.parent, frappe._dict()).setdefault(d.salary_component, [])
        if currency == company_currency:
            ss_map[d.parent][d.salary_component] = flt(d.amount) * flt(d.exchange_rate if d.exchange_rate else 1)
        else:
            ss_map[d.parent][d.salary_component] = flt(d.amount)

    return ss_map

def get_ss_earning_map(salary_slips, currency, company_currency):
    return get_ss_deduction_and_earnings(salary_slips, currency, company_currency, is_earning=True)

def get_ss_ded_map(salary_slips, currency, company_currency):
    return get_ss_deduction_and_earnings(salary_slips, currency, company_currency, is_earning=False)