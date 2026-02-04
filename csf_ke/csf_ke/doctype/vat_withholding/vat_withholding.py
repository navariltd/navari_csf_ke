# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class VATWithholding(Document):
	def before_validate(self):
		self.set_missing_values()

	@frappe.whitelist()
	def set_missing_values(self):
		self.currency = "KES"

		if not self.customer and self.withholder_pin:
			self.customer = frappe.db.get_value("Customer", {"tax_id": self.withholder_pin}, "name")

		if self.invoice_no:
			invoice_filters = [
				{"etr_invoice_number": self.invoice_no},
				{"name": self.invoice_no},
			]

			for invoice_filter in invoice_filters:
				invoice_data = frappe.db.get_value(
					"Sales Invoice",
					invoice_filter,
					["name", "outstanding_amount", "customer", "tax_id"],
					as_dict=True,
				)
				if invoice_data:
					self.voucher_no = invoice_data.name
					self.outstanding_amount = invoice_data.outstanding_amount
					if not self.customer:
						self.customer = invoice_data.customer
					if not self.withholder_pin:
						self.withholder_pin = invoice_data.tax_id
					break

		if self.company and not self.withholding_account:
			company_data = frappe.db.get_value(
				"Company",
				self.company,
				["default_debitors_withholding_account"],
				as_dict=True,
			)
			self.withholding_account = company_data.default_debitors_withholding_account

		if self.outstanding_amount and self.vat_withholding_amount:
			if self.outstanding_amount == self.vat_withholding_amount:
				self.allocate_payment = True
				self.submit_journal_entry = True

		return self.as_dict()

	def on_submit(self):
		if not self.withholding_account:
			frappe.throw("Please set the withholding account")

		journal_entry = self.create_journal_entry(
			self,
			"on_submit",
			submit_journal_entry=self.submit_journal_entry,
			allocate_payment=self.allocate_payment,
		)

		frappe.db.set_value("VAT Withholding", self.name, "journal_entry", journal_entry)

	@staticmethod
	def create_journal_entry(doc, method, *args, **kwargs):
		customer_receivable_account = frappe.get_value("Company", doc.company, "default_receivable_account")

		reference_doctype = "Sales Invoice" if kwargs.get("allocate_payment") else ""
		reference_name = doc.voucher_no if kwargs.get("allocate_payment") else ""
		remark = f"Reference #{doc.wht_certificate_no} dated {doc.certificate_date} for {doc.invoice_no} Voucher {doc.voucher_no}"

		je = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"posting_date": doc.certificate_date,
				"company": doc.company,
				"voucher_type": "Journal Entry",
				"cheque_no": doc.wht_certificate_no,
				"cheque_date": doc.certificate_date,
				"user_remark": remark,
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
					},
				],
			}
		)

		je.insert()

		if kwargs.get("submit_journal_entry"):
			je.submit()

		return je.name
