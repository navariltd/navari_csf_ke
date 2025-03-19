# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class VATWithholding(Document):
	
	def before_insert(self):
		self.set_missing_values()
		

	def set_missing_values(self):
		self.currency = "KES"
		self.company = frappe.defaults.get_user_default("Company")
		self.customer = frappe.get_value("Customer", {'tax_id': self.withholder_pin}, "name")
		self.voucher_no = frappe.get_value("Sales Invoice", {'etr_invoice_number': self.invoice_no}, "name")
		self.outstanding_amount = frappe.get_value("Sales Invoice", self.voucher_no, "outstanding_amount")
		self.withholding_account = frappe.get_value("Company", self.company, "default_debitors_withholding_account")
		
		if self.outstanding_amount == self.vat_withholding_amount:
			self.allocate_payment = True
			self.submit_journal_entry = True

	def on_submit(self):
		if not self.withholding_account:
			frappe.throw("Please set the withholding account")
		
		journal_entry = self.create_journal_entry(
				self, "on_submit", submit_journal_entry=self.submit_journal_entry, allocate_payment=self.allocate_payment
			)

		frappe.db.set_value("VAT Withholding", self.name, "journal_entry", journal_entry)

	@staticmethod
	def create_journal_entry(doc, method, *args, **kwargs):

		customer_receivable_account = frappe.get_value("Company", doc.company, "default_receivable_account")

		reference_doctype = "Sales Invoice" if kwargs.get("allocate_payment") else ""
		reference_name = doc.voucher_no if kwargs.get("allocate_payment") else ""
		remark = f"Payment for Sales Invoice {doc.voucher_no} via VAT Withholding {doc.wht_certificate_no}"\
			  		if kwargs.get("allocate_payment")\
					else f"VAT Withholding Acknowledgment - Cert No: {doc.wht_certificate_no}"

		je = frappe.get_doc({
			"doctype": "Journal Entry",
			"posting_date": doc.certificate_date,
			"company": doc.company,
			"voucher_type": "Journal Entry",
			"cheque_no": doc.wht_certificate_no,
			"cheque_date": doc.certificate_date,
			"remark": remark,
			"accounts": [
				{
					"account": doc.withholding_account,
					"debit_in_account_currency": doc.vat_withholding_amount,
					"party_type": "",
					"party": "",
					"reference_type": "",
					"reference_name": "",
				},
				{
					"account": customer_receivable_account,
					"credit_in_account_currency": doc.vat_withholding_amount,
					"party_type": "Customer",
					"party": doc.customer,
					"reference_type": reference_doctype,
					"reference_name": reference_name,
				}
			]
		})

		je.insert()

		if kwargs.get("submit_journal_entry"):
			je.submit()
		
		return je.name
