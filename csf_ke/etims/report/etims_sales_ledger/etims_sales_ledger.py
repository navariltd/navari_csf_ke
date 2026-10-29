import frappe
from erpnext.setup.utils import get_exchange_rate
from frappe import _
from frappe.query_builder import DocType
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
			"label": _("Invoice / Receipt Date"),
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
			"width": 260,
		},
		{
			"label": _("ERP Invoice Amt"),
			"fieldname": "erp_invoice_amount",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("eTIMS Invoice Amt"),
			"fieldname": "etims_invoice_amount",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("ERP CN Amt"),
			"fieldname": "erp_credit_amount",
			"fieldtype": "Currency",
			"width": 140,
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
			"label": _("ERP Tax Amt"),
			"fieldname": "erp_tax_amount",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("eTIMS Tax Amt"),
			"fieldname": "etims_total_tax",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Tax Variance"),
			"fieldname": "tax_difference",
			"fieldtype": "Currency",
			"width": 130,
		},
		{"label": _("Indent"), "fieldname": "indent", "fieldtype": "Int", "hidden": 1},
		{"label": _("Parent"), "fieldname": "parent", "fieldtype": "Data", "hidden": 1},
		{"label": _("Group"), "fieldname": "is_group", "fieldtype": "Check", "hidden": 1},
	]


def _convert_amounts(invoice_doc):
	currency = invoice_doc.get("currency")
	company = invoice_doc.get("company")
	company_currency = frappe.get_value("Company", company, "default_currency")

	if currency == "KES":
		grand_total = flt(invoice_doc.get("grand_total"))
		tax_total = flt(invoice_doc.get("total_taxes_and_charges"))
	elif company_currency == "KES":
		grand_total = flt(invoice_doc.get("base_grand_total"))
		tax_total = flt(invoice_doc.get("base_total_taxes_and_charges"))
	else:
		conversion_rate = get_exchange_rate(currency, "KES", invoice_doc.get("posting_date"))
		grand_total = flt(invoice_doc.get("grand_total")) * conversion_rate
		tax_total = flt(invoice_doc.get("total_taxes_and_charges")) * conversion_rate

	return grand_total, tax_total


def _empty_group_row(key):
	return {
		"sales_invoice": key,
		"customer": "",
		"invoice_date": None,
		"erp_invoice_amount": 0,
		"erp_tax_amount": 0,
		"erp_credit_amount": 0,
		"erp_credit_tax_amount": 0,
		"etims_invoice_amount": 0,
		"etims_credit_amount": 0,
		"etims_total_tax": 0,
		"etims_credit_tax": 0,
		"difference": 0,
		"tax_difference": 0,
		"etims_status": "No",
		"reconciliation_status": "",
		"indent": 0,
		"parent": "",
		"is_group": 1,
		"children": [],
		"flags": set(),
	}


def get_data(filters):
	Ledger = DocType("eTIMS Sales Ledger Entry")
	SI = DocType("Sales Invoice")

	from_date, to_date = normalize_date_range(filters.get("from_date"), filters.get("to_date"))
	company = filters.get("company")

	period_ledgers = (
		frappe.qb.from_(Ledger)
		.select(
			Ledger.name,
			Ledger.sales_invoice,
			Ledger.scu_receipt_date,
			Ledger.type,
			Ledger.total_gross_amount,
			Ledger.total_vat,
			Ledger.customer_name,
			Ledger.reference_number,
			Ledger.scu_invoice_number,
			Ledger.is_signed,
			Ledger.etims_invoice,
		)
		.where(Ledger.company == company)
		.where(Ledger.scu_receipt_date.between(from_date, to_date))
	).run(as_dict=True)

	period_invoices = (
		frappe.qb.from_(SI)
		.select(
			SI.name,
			SI.customer,
			SI.posting_date,
			SI.grand_total,
			SI.total_taxes_and_charges,
			SI.base_grand_total,
			SI.base_total_taxes_and_charges,
			SI.currency,
			SI.company,
			SI.sent_to_etims,
			SI.docstatus,
			SI.is_return,
			SI.return_against,
		)
		.where(SI.company == company)
		.where(SI.docstatus == 1)
		.where(SI.posting_date.between(from_date, to_date))
	).run(as_dict=True)

	grouped = {}

	for inv in period_invoices:
		key = inv.name if not inv.is_return else inv.return_against
		if not key:
			key = inv.name

		if key not in grouped:
			grouped[key] = _empty_group_row(key)

		grand_total, tax_total = _convert_amounts(inv)
		p_date = getdate(inv.posting_date)

		if not inv.is_return:
			grouped[key]["customer"] = inv.customer
			grouped[key]["invoice_date"] = p_date
			grouped[key]["erp_invoice_amount"] += grand_total
			grouped[key]["erp_tax_amount"] += tax_total
			if inv.sent_to_etims:
				grouped[key]["etims_status"] = "Yes"
		else:
			grouped[key]["erp_credit_amount"] += grand_total
			grouped[key]["erp_credit_tax_amount"] += tax_total
			if inv.return_against:
				orig_inv = frappe.db.get_value(
					"Sales Invoice", inv.return_against, ["posting_date", "customer"], as_dict=True
				)
				if orig_inv:
					orig_date = getdate(orig_inv.posting_date)
					if orig_date < getdate(from_date):
						grouped[key]["flags"].add(
							f"Credit Note issued in period for older invoice dated {orig_date}"
						)
					if not grouped[key]["customer"]:
						grouped[key]["customer"] = orig_inv.customer
					if not grouped[key]["invoice_date"]:
						grouped[key]["invoice_date"] = orig_date

	for ledger in period_ledgers:
		key = ledger.sales_invoice
		if not key and ledger.etims_invoice:
			key = frappe.db.get_value("eTIMS Sales Ledger Entry", ledger.etims_invoice, "sales_invoice")

		key = key or "UNMATCHED_LEDGERS"

		if key not in grouped:
			grouped[key] = _empty_group_row(key)
			if key != "UNMATCHED_LEDGERS":
				parent_inv = frappe.db.get_value(
					"Sales Invoice",
					key,
					[
						"name",
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
				if parent_inv and parent_inv.docstatus == 1:
					gt, tt = _convert_amounts(parent_inv)
					grouped[key]["customer"] = parent_inv.customer
					grouped[key]["invoice_date"] = getdate(parent_inv.posting_date)
					grouped[key]["erp_invoice_amount"] = gt
					grouped[key]["erp_tax_amount"] = tt
					grouped[key]["etims_status"] = "Yes" if parent_inv.sent_to_etims else "No"
					p_date = getdate(parent_inv.posting_date)
					if p_date < getdate(from_date):
						grouped[key]["flags"].add(
							f"eTIMS Ledger processed in period for older invoice dated {p_date}"
						)

		if ledger.type == "Sales Invoice":
			grouped[key]["etims_invoice_amount"] += flt(ledger.total_gross_amount)
			grouped[key]["etims_total_tax"] += flt(ledger.total_vat)
		else:
			grouped[key]["etims_credit_amount"] += flt(ledger.total_gross_amount)
			grouped[key]["etims_credit_tax"] += flt(ledger.total_vat)

		receipt_date = getdate(ledger.scu_receipt_date)
		if grouped[key]["invoice_date"] and receipt_date != grouped[key]["invoice_date"]:
			grouped[key]["flags"].add(
				f"Date Mismatch: Invoice ({grouped[key]['invoice_date']}) vs eTIMS Receipt ({receipt_date})"
			)

		grouped[key]["children"].append(
			{
				"sales_invoice": f"Ledger: {ledger.scu_invoice_number or ledger.name}",
				"customer": ledger.customer_name,
				"invoice_date": receipt_date,
				"type": ledger.type,
				"is_signed": ledger.is_signed,
				"reference_number": ledger.reference_number,
				"scu_invoice_number": ledger.scu_invoice_number,
				"erp_invoice_amount": 0,
				"erp_tax_amount": 0,
				"erp_credit_amount": 0,
				"erp_credit_tax_amount": 0,
				"etims_invoice_amount": flt(ledger.total_gross_amount)
				if ledger.type == "Sales Invoice"
				else 0,
				"etims_credit_amount": flt(ledger.total_gross_amount) if ledger.type == "Credit Note" else 0,
				"etims_total_tax": flt(ledger.total_vat) if ledger.type == "Sales Invoice" else 0,
				"etims_credit_tax": flt(ledger.total_vat) if ledger.type == "Credit Note" else 0,
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
	tot_erp_inv = tot_etims_inv = tot_erp_cr = tot_etims_cr = 0
	tot_erp_tax = tot_etims_tax = tot_var = 0

	sorted_groups = sorted(
		grouped.items(),
		key=lambda kv: str(kv[1].get("invoice_date") or ""),
		reverse=True,
	)

	for key, row in sorted_groups:
		if key == "UNMATCHED_LEDGERS":
			row["reconciliation_status"] = "ERROR: eTIMS Ledgers exist without matching Sales Invoice"
			row["customer"] = "Unmatched Ledgers"
		else:
			net_erp_amt = row["erp_invoice_amount"] - row["erp_credit_amount"]
			net_etims_amt = row["etims_invoice_amount"] - row["etims_credit_amount"]
			row["difference"] = net_etims_amt - net_erp_amt

			net_erp_tax = row["erp_tax_amount"] - row["erp_credit_tax_amount"]
			net_etims_tax = row["etims_total_tax"] - row["etims_credit_tax"]
			row["tax_difference"] = net_etims_tax - net_erp_tax

			amt_var_pct = (abs(row["difference"]) / abs(net_erp_amt) * 100) if net_erp_amt else 0
			tax_var_pct = (abs(row["tax_difference"]) / abs(net_erp_tax) * 100) if net_erp_tax else 0

			has_ledgers = bool(row["children"])
			in_period_inv = row["invoice_date"] and getdate(from_date) <= row["invoice_date"] <= getdate(
				to_date
			)

			status_parts = []
			if in_period_inv and not has_ledgers and row["etims_status"] == "No":
				status_parts.append("ERROR: Invoice in period but missing eTIMS Ledger")
			elif in_period_inv and not has_ledgers and row["etims_status"] == "Yes":
				status_parts.append("ERROR: Marked Sent to eTIMS but Ledger missing")
			elif amt_var_pct > 1 or tax_var_pct > 1:
				status_parts.append(
					f"ERROR: Variance >1% detected (Amt: {row['difference']:.2f}, Tax: {row['tax_difference']:.2f})"
				)
			else:
				status_parts.append("Matched")

			if row["flags"]:
				status_parts.append(" | ".join(sorted(row["flags"])))

			row["reconciliation_status"] = " | ".join(status_parts)

		if filters.get("sales_invoice") and key != filters.get("sales_invoice"):
			continue
		if filters.get("customer") and filters.get("customer") != row.get("customer"):
			continue
		if filters.get("sent_to_etims") and row.get("etims_status") != filters.get("sent_to_etims"):
			continue
		if filters.get("reconciliation_status") and filters.get("reconciliation_status") not in row.get(
			"reconciliation_status"
		):
			continue
		if filters.get("hide_matched") and row["reconciliation_status"].startswith("Matched"):
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

		tot_erp_inv += row["erp_invoice_amount"]
		tot_etims_inv += row["etims_invoice_amount"]
		tot_erp_cr += row["erp_credit_amount"]
		tot_etims_cr += row["etims_credit_amount"]
		tot_erp_tax += row["erp_tax_amount"] - row["erp_credit_tax_amount"]
		tot_etims_tax += row["etims_total_tax"] - row["etims_credit_tax"]
		tot_var += abs(row["difference"])

		row.pop("flags", None)
		result.append(row)
		result.extend(filtered_children)

	result.append(
		{
			"sales_invoice": "TOTAL",
			"customer": "",
			"invoice_date": "",
			"erp_invoice_amount": tot_erp_inv,
			"etims_invoice_amount": tot_etims_inv,
			"erp_credit_amount": tot_erp_cr,
			"etims_credit_amount": tot_etims_cr,
			"difference": tot_var,
			"erp_tax_amount": tot_erp_tax,
			"etims_total_tax": tot_etims_tax,
			"tax_difference": tot_etims_tax - tot_erp_tax,
			"etims_status": "",
			"reconciliation_status": "",
			"indent": 0,
			"parent": "",
			"is_group": 1,
		}
	)

	return result


def get_chart(data):
	tot_erp_inv = tot_etims_inv = tot_erp_cr = tot_etims_cr = tot_var = 0
	for d in data:
		if d.get("sales_invoice") == "TOTAL":
			tot_erp_inv = flt(d.get("erp_invoice_amount"))
			tot_etims_inv = flt(d.get("etims_invoice_amount"))
			tot_erp_cr = flt(d.get("erp_credit_amount"))
			tot_etims_cr = flt(d.get("etims_credit_amount"))
			tot_var = flt(d.get("difference"))

	return {
		"data": {
			"labels": [
				_("ERP Invoice Amount"),
				_("eTIMS Invoice Amount"),
				_("ERP Credit Notes"),
				_("eTIMS Credit Notes"),
				_("Total Variance"),
			],
			"datasets": [
				{
					"name": _("Amounts (KES)"),
					"values": [tot_erp_inv, tot_etims_inv, tot_erp_cr, tot_etims_cr, tot_var],
				}
			],
		},
		"type": "bar",
		"height": 300,
		"barOptions": {"stacked": 0},
	}


def get_report_summary(data):
	tot_erp_inv = tot_etims_inv = tot_erp_cr = tot_etims_cr = tot_var = 0
	matched_count = error_count = 0

	for d in data:
		if d.get("sales_invoice") == "TOTAL":
			tot_erp_inv = flt(d.get("erp_invoice_amount"))
			tot_etims_inv = flt(d.get("etims_invoice_amount"))
			tot_erp_cr = flt(d.get("erp_credit_amount"))
			tot_etims_cr = flt(d.get("etims_credit_amount"))
			tot_var = flt(d.get("difference"))
		elif d.get("is_group") == 1:
			status = d.get("reconciliation_status", "")
			if status.startswith("Matched"):
				matched_count += 1
			elif "ERROR" in status:
				error_count += 1

	return [
		{
			"value": tot_erp_inv,
			"label": _("Total ERP Invoice Amt"),
			"datatype": "Currency",
			"indicator": "Blue",
		},
		{
			"value": tot_etims_inv,
			"label": _("Total eTIMS Invoice Amt"),
			"datatype": "Currency",
			"indicator": "Green",
		},
		{
			"value": tot_erp_cr,
			"label": _("Total ERP Credit Notes"),
			"datatype": "Currency",
			"indicator": "Blue",
		},
		{
			"value": tot_etims_cr,
			"label": _("Total eTIMS Credit Notes"),
			"datatype": "Currency",
			"indicator": "Green",
		},
		{
			"value": tot_var,
			"label": _("Total Variance Amount"),
			"datatype": "Currency",
			"indicator": "Red" if tot_var > 1 else "Green",
		},
		{"value": matched_count, "label": _("Matched Groups"), "datatype": "Int", "indicator": "Green"},
		{"value": error_count, "label": _("Error Groups"), "datatype": "Int", "indicator": "Red"},
	]
