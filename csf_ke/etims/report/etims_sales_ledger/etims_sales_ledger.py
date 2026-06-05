# Copyright (c) 2026, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Sum
from frappe.utils import add_to_date, flt, get_datetime, getdate


def execute(filters=None):
	filters = filters or {}
	validate_filters(filters)
	columns = get_columns(filters)
	data = get_data(filters)
	chart = get_chart(data)
	report_summary = get_report_summary(data)
	return columns, data, None, chart, report_summary


def normalize_date_range(from_date, to_date):
	if from_date:
		from_date = getdate(from_date)
	if to_date:
		to_date = get_datetime(add_to_date(getdate(to_date), days=1, seconds=-1))
	return from_date, to_date


def validate_filters(filters):
	if filters.get("from_date") and filters.get("to_date"):
		if getdate(filters.get("from_date")) > getdate(filters.get("to_date")):
			frappe.throw(_("From Date must be before To Date"))


def get_columns(filters):
	filters = filters or {}
	show_details = filters.get("show_details")

	base_columns = [
		{
			"label": _("Sales Invoice"),
			"fieldname": "sales_invoice",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 200,
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150,
		},
		{
			"label": _("Invoice Date"),
			"fieldname": "invoice_date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": _("Invoice Amount"),
			"fieldname": "erp_invoice_amount",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _(" Amount (Period)"),
			"fieldname": "erp_invoice_period_amount",
			"fieldtype": "Currency",
			"width": 160,
		},
		{
			"label": _("Tax Amount"),
			"fieldname": "erp_tax_amount",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("CN Amount"),
			"fieldname": "erp_credit_amount",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("CN Amount (Period)"),
			"fieldname": "erp_credit_period_amount",
			"fieldtype": "Currency",
			"width": 160,
		},
	]

	etims_columns = [
		{
			"label": _("Type"),
			"fieldname": "type",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Signed"),
			"fieldname": "is_signed",
			"fieldtype": "Check",
			"width": 80,
		},
		{
			"label": _("Reference"),
			"fieldname": "reference_number",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("SCU No"),
			"fieldname": "scu_invoice_number",
			"fieldtype": "Data",
			"width": 150,
		},
	]

	summary_columns = [
		{
			"label": _("eTIMS Invoice"),
			"fieldname": "etims_invoice_amount",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("eTIMS Credit"),
			"fieldname": "etims_credit_amount",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("eTIMS VAT"),
			"fieldname": "etims_total_tax",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Difference"),
			"fieldname": "difference",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Tax Difference"),
			"fieldname": "tax_difference",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Status"),
			"fieldname": "reconciliation_status",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("Indent"),
			"fieldname": "indent",
			"fieldtype": "Int",
			"hidden": 1,
		},
		{
			"label": _("Parent"),
			"fieldname": "parent",
			"fieldtype": "Data",
			"hidden": 1,
		},
		{
			"label": _("Group"),
			"fieldname": "is_group",
			"fieldtype": "Check",
			"hidden": 1,
		},
	]

	columns = base_columns
	if show_details:
		columns.extend(etims_columns)
	columns.extend(summary_columns)
	return columns


def _fetch_invoice_data(invoice_name):
	return frappe.db.get_value(
		"Sales Invoice",
		invoice_name,
		[
			"customer",
			"posting_date",
			"grand_total",
			"total_taxes_and_charges",
			"base_grand_total",
			"base_total_taxes_and_charges",
			"currency",
			"company",
		],
		as_dict=True,
	)


def _get_erp_invoice_data(key, invoice_data, from_date=None, to_date=None):
	SI = DocType("Sales Invoice")

	currency = invoice_data.get("currency")
	company = invoice_data.get("company")
	company_currency = frappe.get_value("Company", company, "default_currency")

	if currency == "KES":
		erp_grand_total = flt(invoice_data.get("grand_total"))
		erp_tax_total = flt(invoice_data.get("total_taxes_and_charges"))
	elif company_currency == "KES":
		erp_grand_total = flt(invoice_data.get("base_grand_total"))
		erp_tax_total = flt(invoice_data.get("base_total_taxes_and_charges"))
	else:
		conversion_rate = frappe.utils.get_exchange_rate(currency, "KES", invoice_data.get("posting_date"))
		erp_grand_total = flt(invoice_data.get("grand_total")) * conversion_rate
		erp_tax_total = flt(invoice_data.get("total_taxes_and_charges")) * conversion_rate

	def _sum_credits(extra_filters=None):
		q = (
			frappe.qb.from_(SI)
			.where(SI.is_return == 1)
			.where(SI.return_against == key)
			.where(SI.docstatus == 1)
		)
		if extra_filters:
			for f in extra_filters:
				q = q.where(f)

		if currency == "KES":
			return flt(q.select(Sum(SI.grand_total)).run()[0][0])
		elif company_currency == "KES":
			return flt(q.select(Sum(SI.base_grand_total)).run()[0][0])
		else:
			raw = flt(q.select(Sum(SI.grand_total)).run()[0][0])
			cr = frappe.utils.get_exchange_rate(currency, "KES", invoice_data.get("posting_date"))
			return raw * cr

	credit_amount_all = _sum_credits()
	credit_amount_period = (
		_sum_credits([SI.posting_date.between(from_date, to_date)]) if from_date and to_date else 0
	)

	return erp_grand_total, erp_tax_total, credit_amount_all, credit_amount_period


def _empty_group_row(key):
	return {
		"sales_invoice": key,
		"customer": "",
		"invoice_date": None,
		"erp_invoice_amount": 0,
		"erp_invoice_period_amount": 0,
		"erp_tax_amount": 0,
		"erp_credit_amount": 0,
		"erp_credit_period_amount": 0,
		"etims_invoice_amount": 0,
		"etims_credit_amount": 0,
		"etims_total_tax": 0,
		"difference": 0,
		"tax_difference": 0,
		"indent": 0,
		"parent": "",
		"is_group": 1,
	}


def _populate_erp_data(key, row, invoice_data, from_date, to_date):
	erp_grand_total, erp_tax_total, credit_amount_all, credit_amount_period = _get_erp_invoice_data(
		key, invoice_data, from_date, to_date
	)

	posting_date = invoice_data.get("posting_date")
	posting_date = getdate(posting_date) if posting_date else None

	in_period = (
		posting_date and from_date and to_date and getdate(from_date) <= posting_date <= getdate(to_date)
	)

	row.update(
		{
			"customer": invoice_data.get("customer"),
			"invoice_date": posting_date,
			"erp_invoice_amount": erp_grand_total,
			"erp_invoice_period_amount": erp_grand_total if in_period else 0,
			"erp_tax_amount": erp_tax_total,
			"erp_credit_amount": credit_amount_all,
			"erp_credit_period_amount": credit_amount_period,
		}
	)


def get_data(filters):
	Ledger = DocType("eTIMS Sales Ledger Entry")
	SI = DocType("Sales Invoice")

	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	from_date, to_date = normalize_date_range(from_date, to_date)
	company = filters.get("company")

	etims_query = (
		frappe.qb.from_(Ledger)
		.select(
			Ledger.sales_invoice,
			Ledger.invoice_date,
			Ledger.type,
			Ledger.total_amount,
			Ledger.total_vat,
			Ledger.customer_name,
			Ledger.reference_number,
			Ledger.scu_invoice_number,
			Ledger.is_signed,
		)
		.where(Ledger.company == company)
		.where(Ledger.invoice_date.between(from_date, to_date))
	)

	if filters.get("sales_invoice"):
		etims_query = etims_query.where(Ledger.sales_invoice == filters.get("sales_invoice"))
	if filters.get("customer"):
		etims_query = etims_query.where(Ledger.customer_name == filters.get("customer"))
	if filters.get("type"):
		etims_query = etims_query.where(Ledger.type == filters.get("type"))
	if filters.get("is_signed"):
		etims_query = etims_query.where(Ledger.is_signed == (1 if filters.get("is_signed") == "Yes" else 0))

	etims_rows = etims_query.run(as_dict=True)

	erp_invoice_query = (
		frappe.qb.from_(SI)
		.select(SI.name)
		.where(SI.company == company)
		.where(SI.is_return == 0)
		.where(SI.docstatus == 1)
		.where(SI.posting_date.between(from_date, to_date))
	)

	if filters.get("sales_invoice"):
		erp_invoice_query = erp_invoice_query.where(SI.name == filters.get("sales_invoice"))
	if filters.get("customer"):
		erp_invoice_query = erp_invoice_query.where(SI.customer == filters.get("customer"))

	erp_invoice_names = {r[0] for r in erp_invoice_query.run()}

	erp_credit_query = (
		frappe.qb.from_(SI)
		.select(SI.name, SI.return_against)
		.where(SI.company == company)
		.where(SI.is_return == 1)
		.where(SI.docstatus == 1)
		.where(SI.posting_date.between(from_date, to_date))
	)

	if filters.get("sales_invoice"):
		erp_credit_query = erp_credit_query.where(SI.return_against == filters.get("sales_invoice"))
	if filters.get("customer"):
		erp_credit_query = erp_credit_query.where(SI.customer == filters.get("customer"))

	erp_credit_rows = erp_credit_query.run(as_dict=True)

	parent_invoice_names = {r.return_against for r in erp_credit_rows if r.return_against}
	all_parent_keys = erp_invoice_names | parent_invoice_names

	grouped = {}

	for inv_name in all_parent_keys:
		invoice_data = _fetch_invoice_data(inv_name)
		row = _empty_group_row(inv_name)
		if invoice_data:
			_populate_erp_data(inv_name, row, invoice_data, from_date, to_date)
		grouped[inv_name] = row

	for r in etims_rows:
		key = r.sales_invoice or "UNKNOWN"

		if key not in grouped:
			grouped[key] = _empty_group_row(key)
			if key != "UNKNOWN":
				invoice_data = _fetch_invoice_data(key)
				if invoice_data:
					_populate_erp_data(key, grouped[key], invoice_data, from_date, to_date)

		if r.type == "Sales Invoice":
			grouped[key]["etims_invoice_amount"] += flt(r.total_amount)
		else:
			grouped[key]["etims_credit_amount"] += flt(r.total_amount)

		grouped[key]["etims_total_tax"] += flt(r.total_vat)

		grouped[key].setdefault("children", []).append(
			{
				"sales_invoice": "",
				"customer": r.customer_name,
				"invoice_date": r.invoice_date,
				"type": r.type,
				"is_signed": r.is_signed,
				"reference_number": r.reference_number,
				"scu_invoice_number": r.scu_invoice_number,
				"erp_invoice_amount": 0,
				"erp_invoice_period_amount": 0,
				"erp_tax_amount": 0,
				"erp_credit_amount": 0,
				"erp_credit_period_amount": 0,
				"etims_invoice_amount": flt(r.total_amount) if r.type == "Sales Invoice" else 0,
				"etims_credit_amount": flt(r.total_amount) if r.type == "Credit Note" else 0,
				"etims_total_tax": flt(r.total_vat),
				"difference": 0,
				"tax_difference": 0,
				"indent": 1,
				"parent": key,
				"is_group": 0,
			}
		)

	period_erp_invoice_total = sum(flt(row.get("erp_invoice_period_amount", 0)) for row in grouped.values())

	result = []
	total_erp_invoice = 0
	total_erp_credit = 0
	total_erp_credit_period = 0
	total_erp_tax = 0
	total_etims_invoice = 0
	total_etims_credit = 0
	total_etims_tax = 0
	total_difference = 0

	sorted_groups = sorted(
		grouped.items(),
		key=lambda kv: str(kv[1].get("invoice_date") or ""),
		reverse=True,
	)

	for key, row in sorted_groups:
		etims_total = flt(row["etims_invoice_amount"]) + flt(row["etims_credit_amount"])
		erp_total = flt(row["erp_invoice_amount"]) + flt(row["erp_credit_amount"])

		row["difference"] = etims_total - erp_total
		row["tax_difference"] = flt(row["etims_total_tax"]) - flt(row["erp_tax_amount"])

		if key == "UNKNOWN":
			row["reconciliation_status"] = "Missing in ERPNext"
		elif flt(row["etims_invoice_amount"]) == 0 and flt(row["etims_credit_amount"]) == 0:
			row["reconciliation_status"] = "Missing in eTIMS"
		elif abs(row["difference"]) > 1:
			row["reconciliation_status"] = "Amount Mismatch"
		else:
			row["reconciliation_status"] = "Matched"

		total_erp_invoice += flt(row["erp_invoice_amount"])
		total_erp_credit += flt(row["erp_credit_amount"])
		total_erp_credit_period += flt(row["erp_credit_period_amount"])
		total_erp_tax += flt(row["erp_tax_amount"])
		total_etims_invoice += flt(row["etims_invoice_amount"])
		total_etims_credit += flt(row["etims_credit_amount"])
		total_etims_tax += flt(row["etims_total_tax"])
		total_difference += flt(row["difference"])

		children = row.pop("children", [])
		result.append(row)
		result.extend(children)

	result.append(
		{
			"sales_invoice": "TOTAL",
			"customer": "",
			"invoice_date": "",
			"erp_invoice_amount": period_erp_invoice_total,
			"erp_invoice_period_amount": period_erp_invoice_total,
			"erp_tax_amount": total_erp_tax,
			"erp_credit_amount": total_erp_credit,
			"erp_credit_period_amount": total_erp_credit_period,
			"etims_invoice_amount": total_etims_invoice,
			"etims_credit_amount": total_etims_credit,
			"etims_total_tax": total_etims_tax,
			"difference": total_difference,
			"tax_difference": total_etims_tax - total_erp_tax,
			"reconciliation_status": "",
			"indent": 0,
			"parent": "",
			"is_group": 1,
		}
	)

	return result


def get_chart(data):
	period_erp_invoice = 0
	period_erp_credit = 0
	total_etims_invoice = 0
	total_etims_credit = 0
	total_difference = 0

	for d in data:
		if d.get("sales_invoice") == "TOTAL":
			period_erp_invoice = flt(d.get("erp_invoice_amount"))
			period_erp_credit = flt(d.get("erp_credit_period_amount"))
			total_etims_invoice = flt(d.get("etims_invoice_amount"))
			total_etims_credit = flt(d.get("etims_credit_amount"))
			total_difference = flt(d.get("difference"))

	return {
		"data": {
			"labels": [
				"Invoice Amount (Period)",
				"eTIMS Invoice Amount",
				"Credit Note Amount (Period)",
				"eTIMS Credit Note Amount",
				"Difference",
			],
			"datasets": [
				{
					"name": "Amounts",
					"values": [
						period_erp_invoice,
						total_etims_invoice,
						period_erp_credit,
						total_etims_credit,
						total_difference,
					],
				}
			],
		},
		"type": "bar",
		"height": 300,
		"barOptions": {"stacked": 0},
	}


def get_report_summary(data):
	period_erp_invoice = 0
	total_erp_credit = 0
	period_erp_credit = 0
	total_etims_invoice = 0
	total_etims_credit = 0
	total_difference = 0

	for d in data:
		if d.get("sales_invoice") == "TOTAL":
			period_erp_invoice = flt(d.get("erp_invoice_amount"))
			total_erp_credit = flt(d.get("erp_credit_amount"))
			period_erp_credit = flt(d.get("erp_credit_period_amount"))
			total_etims_invoice = flt(d.get("etims_invoice_amount"))
			total_etims_credit = flt(d.get("etims_credit_amount"))
			total_difference = flt(d.get("difference"))

	return [
		{
			"value": period_erp_invoice,
			"label": _("Invoice Amount (Period)"),
			"datatype": "Currency",
		},
		{
			"value": total_erp_credit,
			"label": _("Credit Note Amount (All Time)"),
			"datatype": "Currency",
		},
		{
			"value": period_erp_credit,
			"label": _("Credit Notes (Period)"),
			"datatype": "Currency",
		},
		{
			"value": total_etims_invoice,
			"label": _("eTIMS Invoice Amount"),
			"datatype": "Currency",
		},
		{
			"value": total_etims_credit,
			"label": _("eTIMS Credit Notes"),
			"datatype": "Currency",
		},
		{
			"value": total_difference,
			"label": _("Total Difference"),
			"datatype": "Currency",
			"indicator": "Red" if abs(total_difference) > 1 else "Green",
		},
	]
