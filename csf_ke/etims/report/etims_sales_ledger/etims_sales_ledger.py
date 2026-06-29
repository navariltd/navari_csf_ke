# Copyright (c) 2026, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from erpnext.setup.utils import get_exchange_rate
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
	return [
		{
			"label": _("Sales Invoice"),
			"fieldname": "sales_invoice",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 140,
		},
		{
			"label": _("Invoice Date"),
			"fieldname": "invoice_date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 160,
		},
		{
			"label": _("Sent to eTIMS"),
			"fieldname": "etims_status",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": _("Reconciliation Status"),
			"fieldname": "reconciliation_status",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Invoice Amt"),
			"fieldname": "erp_invoice_amount",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Invoice Amt (Period)"),
			"fieldname": "erp_invoice_period_amount",
			"fieldtype": "Currency",
			"width": 160,
		},
		{
			"label": _("eTIMS Invoice Amt"),
			"fieldname": "etims_invoice_amount",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("CN Amt"),
			"fieldname": "erp_credit_amount",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("CN Amt (Period)"),
			"fieldname": "erp_credit_period_amount",
			"fieldtype": "Currency",
			"width": 170,
		},
		{
			"label": _("eTIMS CN Amt"),
			"fieldname": "etims_credit_amount",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Amount Variance"),
			"fieldname": "difference",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Invoice Tax Amt"),
			"fieldname": "erp_tax_amount",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("eTIMS Invoice Tax Amt"),
			"fieldname": "etims_total_tax",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("CN Tax Amt"),
			"fieldname": "erp_credit_tax_amount",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("eTIMS CN Tax Amt"),
			"fieldname": "etims_credit_tax",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Tax Variance"),
			"fieldname": "tax_difference",
			"fieldtype": "Currency",
			"width": 130,
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
			"sent_to_etims",
			"docstatus",
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
		conversion_rate = get_exchange_rate(currency, "KES", invoice_data.get("posting_date"))
		erp_grand_total = flt(invoice_data.get("grand_total")) * conversion_rate
		erp_tax_total = flt(invoice_data.get("total_taxes_and_charges")) * conversion_rate

	def _sum_credits(field, extra_filters=None):
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
			return flt(q.select(Sum(getattr(SI, field))).run()[0][0])
		elif company_currency == "KES":
			base_field = f"base_{field}"
			return flt(q.select(Sum(getattr(SI, base_field))).run()[0][0])
		else:
			raw = flt(q.select(Sum(getattr(SI, field))).run()[0][0])
			cr = get_exchange_rate(currency, "KES", invoice_data.get("posting_date"))
			return raw * cr

	credit_amount_all = _sum_credits("grand_total")
	credit_amount_period = (
		_sum_credits("grand_total", [SI.posting_date.between(from_date, to_date)])
		if from_date and to_date
		else 0
	)
	credit_tax_period = (
		_sum_credits("total_taxes_and_charges", [SI.posting_date.between(from_date, to_date)])
		if from_date and to_date
		else 0
	)

	return erp_grand_total, erp_tax_total, credit_amount_all, credit_amount_period, credit_tax_period


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
		"erp_credit_tax_amount": 0,
		"etims_invoice_amount": 0,
		"etims_credit_amount": 0,
		"etims_total_tax": 0,
		"etims_credit_tax": 0,
		"difference": 0,
		"tax_difference": 0,
		"etims_status": "",
		"reconciliation_status": "",
		"indent": 0,
		"parent": "",
		"is_group": 1,
	}


def _populate_erp_data(key, row, invoice_data, from_date, to_date):
	erp_grand_total, erp_tax_total, credit_amount_all, credit_amount_period, credit_tax_period = (
		_get_erp_invoice_data(key, invoice_data, from_date, to_date)
	)

	posting_date = invoice_data.get("posting_date")
	posting_date = getdate(posting_date) if posting_date else None

	in_period = (
		posting_date and from_date and to_date and getdate(from_date) <= posting_date <= getdate(to_date)
	)

	sent_to_etims = invoice_data.get("sent_to_etims", 0)
	docstatus = invoice_data.get("docstatus", 0)

	if docstatus != 1:
		return

	etims_status = "Yes" if sent_to_etims else "No"

	row.update(
		{
			"customer": invoice_data.get("customer"),
			"invoice_date": posting_date,
			"erp_invoice_amount": erp_grand_total,
			"erp_invoice_period_amount": erp_grand_total if in_period else 0,
			"erp_tax_amount": erp_tax_total if in_period else 0,
			"erp_credit_amount": credit_amount_all,
			"erp_credit_period_amount": credit_amount_period,
			"erp_credit_tax_amount": credit_tax_period,
			"etims_status": etims_status,
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
			Ledger.name,
			Ledger.sales_invoice,
			Ledger.invoice_date,
			Ledger.type,
			Ledger.total_gross_amount,
			Ledger.total_vat,
			Ledger.customer_name,
			Ledger.reference_number,
			Ledger.scu_invoice_number,
			Ledger.is_signed,
		)
		.where(Ledger.company == company)
		.where(Ledger.invoice_date.between(from_date, to_date))
	)
	etims_rows = etims_query.run(as_dict=True)

	erp_invoice_query = (
		frappe.qb.from_(SI)
		.select(SI.name)
		.where(SI.company == company)
		.where(SI.is_return == 0)
		.where(SI.docstatus == 1)
		.where(SI.posting_date.between(from_date, to_date))
	)
	erp_invoice_names = {r[0] for r in erp_invoice_query.run()}

	erp_credit_query = (
		frappe.qb.from_(SI)
		.select(SI.name, SI.return_against)
		.where(SI.company == company)
		.where(SI.is_return == 1)
		.where(SI.docstatus == 1)
		.where(SI.posting_date.between(from_date, to_date))
	)
	erp_credit_rows = erp_credit_query.run(as_dict=True)

	parent_invoice_names = {r.return_against for r in erp_credit_rows if r.return_against}
	all_parent_keys = erp_invoice_names | parent_invoice_names

	grouped = {}

	for inv_name in all_parent_keys:
		invoice_data = _fetch_invoice_data(inv_name)
		if not invoice_data or invoice_data.get("docstatus") != 1:
			continue
		row = _empty_group_row(inv_name)
		_populate_erp_data(inv_name, row, invoice_data, from_date, to_date)
		grouped[inv_name] = row

	for r in etims_rows:
		key = r.sales_invoice or "UNKNOWN"

		if key not in grouped and key != "UNKNOWN":
			invoice_data = _fetch_invoice_data(key)
			if invoice_data and invoice_data.get("docstatus") == 1:
				grouped[key] = _empty_group_row(key)
				_populate_erp_data(key, grouped[key], invoice_data, from_date, to_date)
			else:
				if key not in grouped:
					grouped[key] = _empty_group_row(key)
					grouped[key].update(
						{
							"customer": r.customer_name,
							"invoice_date": r.invoice_date,
							"reconciliation_status": "Missing in ERPNext",
						}
					)

		if key in grouped:
			if r.type == "Sales Invoice":
				grouped[key]["etims_invoice_amount"] += flt(r.total_gross_amount)
				grouped[key]["etims_total_tax"] += flt(r.total_vat)
			else:
				grouped[key]["etims_credit_amount"] += flt(r.total_gross_amount)
				grouped[key]["etims_credit_tax"] += flt(r.total_vat)

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
					"erp_credit_tax_amount": 0,
					"etims_invoice_amount": flt(r.total_gross_amount) if r.type == "Sales Invoice" else 0,
					"etims_credit_amount": flt(r.total_gross_amount) if r.type == "Credit Note" else 0,
					"etims_total_tax": flt(r.total_vat) if r.type == "Sales Invoice" else 0,
					"etims_credit_tax": flt(r.total_vat) if r.type == "Credit Note" else 0,
					"difference": 0,
					"tax_difference": 0,
					"etims_status": "",
					"reconciliation_status": "",
					"indent": 1,
					"parent": key,
					"is_group": 0,
				}
			)

	result = []
	total_erp_invoice_period = 0
	total_erp_tax = 0
	total_erp_credit = 0
	total_erp_credit_period = 0
	total_erp_credit_tax = 0
	total_etims_invoice = 0
	total_etims_credit = 0
	total_etims_tax = 0
	total_etims_credit_tax = 0
	total_variance = 0

	sorted_groups = sorted(
		grouped.items(),
		key=lambda kv: str(kv[1].get("invoice_date") or ""),
		reverse=True,
	)

	for key, row in sorted_groups:
		etims_total = flt(row["etims_invoice_amount"]) + flt(row["etims_credit_amount"])
		erp_total = flt(row["erp_invoice_period_amount"]) + flt(row["erp_credit_period_amount"])

		row["difference"] = etims_total - erp_total

		etims_tax_total = flt(row["etims_total_tax"]) + flt(row["etims_credit_tax"])
		erp_tax_total = flt(row["erp_tax_amount"]) + flt(row["erp_credit_tax_amount"])
		row["tax_difference"] = etims_tax_total - erp_tax_total

		variance_percent = (abs(row["difference"]) / erp_total * 100) if erp_total > 0 else 0
		tax_variance_percent = (abs(row["tax_difference"]) / erp_tax_total * 100) if erp_tax_total > 0 else 0

		is_sent = row.get("etims_status") == "Yes"
		has_etims_data = flt(row["etims_invoice_amount"]) != 0 or flt(row["etims_credit_amount"]) != 0

		if row.get("reconciliation_status") == "Missing in ERPNext":
			pass
		elif not is_sent and not has_etims_data:
			row["reconciliation_status"] = "Not Sent to eTIMS"
		elif is_sent and not has_etims_data:
			row["reconciliation_status"] = "Sent but No eTIMS Data"
		elif is_sent and (variance_percent > 1 or tax_variance_percent > 1):
			row["reconciliation_status"] = "Sent with Variance (>1%)"
		elif is_sent and variance_percent > 0:
			row["reconciliation_status"] = "Sent with Minor Variance (<1%)"
		elif is_sent and variance_percent == 0:
			row["reconciliation_status"] = "Sent and Matched"
		elif not is_sent and has_etims_data:
			row["reconciliation_status"] = "eTIMS Data Found but Not Sent"

		if filters.get("sales_invoice") and key != filters.get("sales_invoice"):
			continue
		if filters.get("customer") and filters.get("customer") != row.get("customer"):
			continue
		if filters.get("sent_to_etims") and row.get("etims_status") != filters.get("sent_to_etims"):
			continue
		if filters.get("reconciliation_status") and row.get("reconciliation_status") != filters.get(
			"reconciliation_status"
		):
			continue
		if filters.get("hide_matched") and row["reconciliation_status"] == "Sent and Matched":
			continue

		children = row.pop("children", [])
		filtered_children = []

		for child in children:
			if filters.get("type") and child.get("type") != filters.get("type"):
				continue
			if filters.get("is_signed"):
				filter_signed = 1 if filters.get("is_signed") == "Yes" else 0
				if child.get("is_signed") != filter_signed:
					continue
			filtered_children.append(child)

		if (filters.get("type") or filters.get("is_signed")) and not filtered_children:
			continue

		total_erp_invoice_period += flt(row["erp_invoice_period_amount"])
		total_erp_tax += flt(row["erp_tax_amount"])
		total_erp_credit += flt(row["erp_credit_amount"])
		total_erp_credit_period += flt(row["erp_credit_period_amount"])
		total_erp_credit_tax += flt(row["erp_credit_tax_amount"])
		total_etims_invoice += flt(row["etims_invoice_amount"])
		total_etims_credit += flt(row["etims_credit_amount"])
		total_etims_tax += flt(row["etims_total_tax"])
		total_etims_credit_tax += flt(row["etims_credit_tax"])
		total_variance += abs(row["difference"])

		result.append(row)
		result.extend(filtered_children)

	result.append(
		{
			"sales_invoice": "TOTAL",
			"customer": "",
			"invoice_date": "",
			"erp_invoice_amount": total_erp_invoice_period,
			"erp_invoice_period_amount": total_erp_invoice_period,
			"erp_tax_amount": total_erp_tax,
			"erp_credit_amount": total_erp_credit,
			"erp_credit_period_amount": total_erp_credit_period,
			"erp_credit_tax_amount": total_erp_credit_tax,
			"etims_invoice_amount": total_etims_invoice,
			"etims_credit_amount": total_etims_credit,
			"etims_total_tax": total_etims_tax,
			"etims_credit_tax": total_etims_credit_tax,
			"difference": total_variance,
			"tax_difference": (total_etims_tax + total_etims_credit_tax)
			- (total_erp_tax + total_erp_credit_tax),
			"etims_status": "",
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
	total_variance = 0

	for d in data:
		if d.get("sales_invoice") == "TOTAL":
			period_erp_invoice = flt(d.get("erp_invoice_amount"))
			period_erp_credit = flt(d.get("erp_credit_period_amount"))
			total_etims_invoice = flt(d.get("etims_invoice_amount"))
			total_etims_credit = flt(d.get("etims_credit_amount"))
			total_variance = flt(d.get("difference"))

	return {
		"data": {
			"labels": [
				_("Invoice Amount (Period)"),
				_("eTIMS Invoice Amount"),
				_("Credit Notes (Period)"),
				_("eTIMS Credit Notes"),
				_("Total Variance"),
			],
			"datasets": [
				{
					"name": _("Amounts (KES)"),
					"values": [
						period_erp_invoice,
						total_etims_invoice,
						period_erp_credit,
						total_etims_credit,
						total_variance,
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
	period_erp_credit = 0
	total_etims_invoice = 0
	total_etims_credit = 0
	total_variance = 0
	sent_total_amount = 0
	sent_with_variance_amount = 0
	sent_with_variance_count = 0
	sent_matched_count = 0
	sent_matched_amount = 0
	not_sent_total_amount = 0
	not_sent_count = 0

	for d in data:
		if d.get("sales_invoice") == "TOTAL":
			period_erp_invoice = flt(d.get("erp_invoice_amount"))
			period_erp_credit = flt(d.get("erp_credit_period_amount"))
			total_etims_invoice = flt(d.get("etims_invoice_amount"))
			total_etims_credit = flt(d.get("etims_credit_amount"))
			total_variance = flt(d.get("difference"))
		elif d.get("is_group") == 1 and d.get("sales_invoice") != "TOTAL":
			status = d.get("reconciliation_status", "")
			erp_total = flt(d.get("erp_invoice_period_amount")) + flt(d.get("erp_credit_period_amount"))

			if status.startswith("Sent"):
				if status == "Sent and Matched":
					sent_matched_count += 1
					sent_matched_amount += erp_total
				elif status in [
					"Sent with Variance (>1%)",
					"Sent with Minor Variance (<1%)",
					"Sent but No eTIMS Data",
				]:
					sent_with_variance_count += 1
					sent_with_variance_amount += abs(flt(d.get("difference")))
				sent_total_amount += erp_total
			elif status in ["Not Sent to eTIMS", "eTIMS Data Found but Not Sent"]:
				not_sent_count += 1
				not_sent_total_amount += erp_total

	return [
		{
			"value": period_erp_invoice,
			"label": _("Total Invoice Amount (Period)"),
			"datatype": "Currency",
			"indicator": "Blue",
		},
		{
			"value": total_etims_invoice,
			"label": _("Total eTIMS Invoice Amount"),
			"datatype": "Currency",
			"indicator": "Green",
		},
		{
			"value": period_erp_credit,
			"label": _("Total Credit Notes (Period)"),
			"datatype": "Currency",
			"indicator": "Blue",
		},
		{
			"value": total_etims_credit,
			"label": _("Total eTIMS Credit Notes"),
			"datatype": "Currency",
			"indicator": "Green",
		},
		{
			"value": total_variance,
			"label": _("Total Variance Amount"),
			"datatype": "Currency",
			"indicator": "Red" if total_variance > 1 else "Green",
		},
		{
			"value": sent_total_amount,
			"label": _("Total Value Sent to eTIMS"),
			"datatype": "Currency",
			"indicator": "Blue",
		},
		{
			"value": sent_matched_count,
			"label": _("Sent and Matched Invoices"),
			"datatype": "Int",
			"indicator": "Green",
		},
		{
			"value": sent_matched_amount,
			"label": _("Value of Sent and Matched"),
			"datatype": "Currency",
			"indicator": "Green",
		},
		{
			"value": sent_with_variance_count,
			"label": _("Sent with Variance Invoices"),
			"datatype": "Int",
			"indicator": "Red",
		},
		{
			"value": sent_with_variance_amount,
			"label": _("Variance Amount on Sent Invoices"),
			"datatype": "Currency",
			"indicator": "Red",
		},
		{
			"value": not_sent_count,
			"label": _("Not Sent to eTIMS Invoices"),
			"datatype": "Int",
			"indicator": "Orange",
		},
		{
			"value": not_sent_total_amount,
			"label": _("Value of Unsent Invoices"),
			"datatype": "Currency",
			"indicator": "Orange",
		},
	]
