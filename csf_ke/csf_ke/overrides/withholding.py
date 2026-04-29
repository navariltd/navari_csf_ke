import frappe
from frappe import _
from frappe.utils import cint, flt


def _get_exchange_rate(doc):
	default_currency = frappe.get_value("Company", doc.company, "default_currency")
	exchange_rate = 1 if doc.party_account_currency == default_currency else doc.conversion_rate
	return default_currency, exchange_rate


def _get_party_mode_values(doc, party_wise_field, no_party_field):
	party_wise = cint(frappe.get_value("Company", doc.company, party_wise_field) or 0)
	no_party = cint(frappe.get_value("Company", doc.company, no_party_field) or 0)

	if party_wise and no_party:
		frappe.throw(_("Please select only one mode for {0}").format(party_wise_field))

	return "With Party" if party_wise else "No Party"


def _get_withholding_account(doc, tax_type, posting_side, mode):
	mode_map = {
		"With Party": "party_wise",
		"No Party": "no_party",
	}
	fieldname = (
		f"withholding_{tax_type}_{mode_map.get(mode, mode.lower().replace(' ', '_'))}_{posting_side}_account"
	)
	return frappe.get_value("Company", doc.company, fieldname)


def _cancel_journal_entry(journal_entry_name):
	if not journal_entry_name:
		return

	try:
		je = frappe.get_doc("Journal Entry", journal_entry_name)
	except frappe.DoesNotExistError:
		return

	if je.docstatus == 1:
		je.flags.ignore_permissions = True
		frappe.flags.ignore_account_permission = True
		je.cancel()


def _get_invoice_withholding_vat_rate(doctype, party):
	if not party:
		return 0

	party_doctype = "Customer" if doctype == "Sales Invoice" else "Supplier"
	return flt(frappe.get_value(party_doctype, party, "withholding_vat_rate") or 0)


def _set_item_withholding_tax_values(doc, item_rate_field):
	for item in doc.items:
		if item.item_code and not flt(item.withholding_tax_rate):
			item.withholding_tax_rate = flt(
				frappe.get_value("Item", item.item_code, item_rate_field) or 0
			)

		item.withholding_tax_amount = flt(item.base_net_amount) * flt(item.withholding_tax_rate) / 100


def _create_journal_entry(company, posting_date, accounts, user_remark, auto_submit):
	je_doc = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"voucher_type": "Contra Entry",
			"posting_date": posting_date,
			"accounts": accounts,
			"company": company,
			"user_remark": user_remark,
		}
	)
	je_doc.flags.ignore_permissions = True
	frappe.flags.ignore_account_permission = True
	je_doc.insert()

	if auto_submit:
		je_doc.submit()

	return je_doc


def prepare_purchase_withholding_values(doc, method=None):
	doc.withholding_vat_rate = _get_invoice_withholding_vat_rate(doc.doctype, doc.supplier)
	doc.withholding_vat_amount = flt(doc.base_net_total) * flt(doc.withholding_vat_rate) / 100
	_set_item_withholding_tax_values(doc, "withholding_tax_rate_on_purchase")


def prepare_sales_withholding_values(doc, method=None):
	doc.withholding_vat_rate = _get_invoice_withholding_vat_rate(doc.doctype, doc.customer)
	doc.withholding_vat_amount = flt(doc.base_net_total) * flt(doc.withholding_vat_rate) / 100
	_set_item_withholding_tax_values(doc, "withholding_tax_rate_on_sales")


def make_purchase_withholding_journal_entries(doc, method=None):
	auto_create = cint(frappe.get_value("Company", doc.company, "auto_create_purchase_withholding_je") or 0)
	if not auto_create:
		return

	auto_submit = cint(frappe.get_value("Company", doc.company, "auto_submit_purchase_withholding_je") or 0)
	default_currency, exchange_rate = _get_exchange_rate(doc)
	float_precision = cint(frappe.db.get_default("float_precision")) or 3

	wtax_mode = _get_party_mode_values(
		doc,
		"withholding_tax_party_wise",
		"withholding_tax_no_party",
	)
	wvat_mode = _get_party_mode_values(
		doc,
		"withholding_vat_party_wise",
		"withholding_vat_no_party",
	)
	wtax_payable_account = _get_withholding_account(doc, "tax", "payable", wtax_mode)
	wvat_payable_account = _get_withholding_account(doc, "vat", "payable", wvat_mode)

	for item in doc.items:
		if not flt(item.withholding_tax_rate) or cint(item.csf_ke_wtax_je_created):
			continue

		if not wtax_payable_account:
			frappe.throw(_("Please set Purchase Withholding Tax Account in Company {0}").format(doc.company))

		creditor_amount = flt(item.withholding_tax_amount / exchange_rate, float_precision)
		wtax_base_amount = creditor_amount * exchange_rate

		je_doc = _create_journal_entry(
			doc.company,
			doc.posting_date,
			[
				{
					"account": doc.credit_to,
					"party_type": "Supplier",
					"party": doc.supplier,
					"debit_in_account_currency": creditor_amount,
					"exchange_rate": exchange_rate,
					"cost_center": item.cost_center,
					"reference_type": "Purchase Invoice",
					"reference_name": doc.name,
				},
				{
					"account": wtax_payable_account,
					"party_type": "Supplier" if wtax_mode == "With Party" else "",
					"party": doc.supplier if wtax_mode == "With Party" else "",
					"credit_in_account_currency": wtax_base_amount,
					"cost_center": item.cost_center,
					"account_currency": default_currency,
				},
			],
			"Withholding Tax on item {0} for {1}".format(item.item_code, doc.name),
			auto_submit,
		)

		item.withholding_tax_entry = je_doc.name
		item.csf_ke_wtax_je_created = 1
		item.db_update()

	if flt(doc.withholding_vat_amount) and not cint(doc.csf_ke_wvat_je_created):
		if not wvat_payable_account:
			frappe.throw(_("Please set Purchase Withholding VAT Account in Company {0}").format(doc.company))

		wvat_creditor_amount = flt(doc.withholding_vat_amount / exchange_rate, float_precision)
		wvat_base_amount = wvat_creditor_amount * exchange_rate

		je_doc = _create_journal_entry(
			doc.company,
			doc.posting_date,
			[
				{
					"account": doc.credit_to,
					"party_type": "Supplier",
					"party": doc.supplier,
					"debit_in_account_currency": wvat_creditor_amount,
					"exchange_rate": exchange_rate,
					"reference_type": "Purchase Invoice",
					"reference_name": doc.name,
				},
				{
					"account": wvat_payable_account,
					"party_type": "Supplier" if wvat_mode == "With Party" else "",
					"party": doc.supplier if wvat_mode == "With Party" else "",
					"credit_in_account_currency": wvat_base_amount,
					"account_currency": default_currency,
				},
			],
			"Withholding VAT on {0}".format(doc.name),
			auto_submit,
		)

		doc.db_set("withholding_vat_entry", je_doc.name)
		doc.db_set("csf_ke_wvat_je_created", 1)


def make_sales_withholding_journal_entries(doc, method=None):
	auto_create = cint(frappe.get_value("Company", doc.company, "auto_create_sales_withholding_je") or 0)
	if not auto_create:
		return

	auto_submit = cint(frappe.get_value("Company", doc.company, "auto_submit_sales_withholding_je") or 0)
	default_currency, exchange_rate = _get_exchange_rate(doc)
	float_precision = cint(frappe.db.get_default("float_precision")) or 3

	wtax_mode = _get_party_mode_values(
		doc,
		"withholding_tax_party_wise",
		"withholding_tax_no_party",
	)
	wvat_mode = _get_party_mode_values(
		doc,
		"withholding_vat_party_wise",
		"withholding_vat_no_party",
	)
	wtax_receivable_account = _get_withholding_account(doc, "tax", "receivable", wtax_mode)
	wvat_receivable_account = _get_withholding_account(doc, "vat", "receivable", wvat_mode)

	for item in doc.items:
		if not flt(item.withholding_tax_rate) or cint(item.csf_ke_wtax_je_created):
			continue

		if not wtax_receivable_account:
			frappe.throw(_("Please set Sales Withholding Tax Account in Company {0}").format(doc.company))

		debtor_amount = flt(item.withholding_tax_amount / exchange_rate, float_precision)
		wtax_base_amount = debtor_amount * exchange_rate

		je_doc = _create_journal_entry(
			doc.company,
			doc.posting_date,
			[
				{
					"account": doc.debit_to,
					"party_type": "Customer",
					"party": doc.customer,
					"credit_in_account_currency": debtor_amount,
					"exchange_rate": exchange_rate,
					"cost_center": item.cost_center,
					"reference_type": "Sales Invoice",
					"reference_name": doc.name,
				},
				{
					"account": wtax_receivable_account,
					"party_type": "Customer" if wtax_mode == "With Party" else "",
					"party": doc.customer if wtax_mode == "With Party" else "",
					"debit_in_account_currency": wtax_base_amount,
					"cost_center": item.cost_center,
					"account_currency": default_currency,
				},
			],
			"Withholding Tax on item {0} for {1}".format(item.item_code, doc.name),
			auto_submit,
		)

		item.withholding_tax_entry = je_doc.name
		item.csf_ke_wtax_je_created = 1
		item.db_update()

	if flt(doc.withholding_vat_amount) and not cint(doc.csf_ke_wvat_je_created):
		if not wvat_receivable_account:
			frappe.throw(_("Please set Sales Withholding VAT Account in Company {0}").format(doc.company))

		wvat_debtor_amount = flt(doc.withholding_vat_amount / exchange_rate, float_precision)
		wvat_base_amount = wvat_debtor_amount * exchange_rate

		je_doc = _create_journal_entry(
			doc.company,
			doc.posting_date,
			[
				{
					"account": doc.debit_to,
					"party_type": "Customer",
					"party": doc.customer,
					"credit_in_account_currency": wvat_debtor_amount,
					"exchange_rate": exchange_rate,
					"reference_type": "Sales Invoice",
					"reference_name": doc.name,
				},
				{
					"account": wvat_receivable_account,
					"party_type": "Customer" if wvat_mode == "With Party" else "",
					"party": doc.customer if wvat_mode == "With Party" else "",
					"debit_in_account_currency": wvat_base_amount,
					"account_currency": default_currency,
				},
			],
			"Withholding VAT on {0}".format(doc.name),
			auto_submit,
		)

		doc.db_set("withholding_vat_entry", je_doc.name)
		doc.db_set("csf_ke_wvat_je_created", 1)


def cancel_purchase_withholding_journal_entries(doc, method=None):
	for item in doc.items:
		_cancel_journal_entry(item.withholding_tax_entry)

	_cancel_journal_entry(doc.withholding_vat_entry)


def cancel_sales_withholding_journal_entries(doc, method=None):
	for item in doc.items:
		_cancel_journal_entry(item.withholding_tax_entry)

	_cancel_journal_entry(doc.withholding_vat_entry)
