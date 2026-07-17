# Copyright (c) 2022, Navari Limited and contributors
# For license information, please see license.txt


from typing import TypedDict

from frappe import _

from csf_ke.csf_ke.utils.tax_report import TaxReport


class KenyaPurchaseTaxReportFilters(TypedDict):
	company: str | None
	from_date: str | None
	to_date: str | None
	is_return: int | None
	item_tax_template: str | None
	taxes_and_charges_template: str | None


def execute(filters: KenyaPurchaseTaxReportFilters | None = None):
	report = KenyaPurchaseTaxReport(filters)
	return report.run()


class KenyaPurchaseTaxReport(TaxReport):
	def __init__(self, filters: KenyaPurchaseTaxReportFilters | None = None):
		super().__init__()
		self.filters = filters or {}
		self.company = self.filters.get("company")
		self.from_date = self.filters.get("from_date")
		self.to_date = self.filters.get("to_date")
		self.item_tax_template = self.filters.get("item_tax_template")
		self.taxes_and_charges_template = self.filters.get("taxes_and_charges_template")

	def run(self):
		columns = self.get_columns()
		data = self.get_data("purchase")

		return columns, data, None, None, self.get_report_summary()

	def get_columns(self):
		columns = [
			{
				"label": _("Supplier PIN"),
				"fieldname": "tax_id",
				"fieldtype": "Data",
				"width": 150,
			},
			{
				"label": _("Supplier Name"),
				"fieldname": "party_name",
				"fieldtype": "Data",
				"width": 200,
			},
			{
				"label": _("Invoice Number"),
				"fieldname": "invoice_number",
				"fieldtype": "Link",
				"options": "Purchase Invoice",
				"width": 200,
			},
			{
				"label": _("Invoice Date"),
				"fieldname": "invoice_date",
				"fieldtype": "Date",
				"width": 200,
			},
			{
				"label": _("ETR Invoice Number"),
				"fieldname": "etr_invoice_number",
				"fieldtype": "Data",
				"width": 200,
			},
			{
				"label": _("Supplier Invoice No"),
				"fieldname": "supplier_invoice_no",
				"fieldtype": "Data",
				"width": 200,
			},
			{
				"label": _("Supplier Invoice Date"),
				"fieldname": "supplier_invoice_date",
				"fieldtype": "Date",
				"width": 200,
			},
			{
				"label": _("Taxable Amount"),
				"fieldname": "taxable_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 200,
			},
			{
				"label": _("VAT Amount"),
				"fieldname": "vat_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 200,
			},
			{
				"label": _("Currency"),
				"fieldname": "currency",
				"fieldtype": "Data",
				"width": 200,
				"hidden": 1,
			},
		]

		if self.filters.get("is_return"):
			columns.append(
				{
					"label": _("Return Against"),
					"fieldname": "return_against",
					"fieldtype": "Data",
					"width": 200,
				}
			)

		return columns

	def get_report_summary(self):
		return [
			{
				"value": self.registered_suppliers_total_purchases,
				"indicator": "Green",
				"label": _("Registered Suppliers Total Purchases"),
				"datatype": "Currency",
				"currency": self.currency,
			},
			{
				"value": self.registered_suppliers_total_vat,
				"indicator": "Green",
				"label": _("Registered Suppliers Total VAT"),
				"datatype": "Currency",
				"currency": self.currency,
			},
			{
				"value": self.unregistered_suppliers_total_purchases,
				"indicator": "Green",
				"label": _("Unregistered Suppliers Total Purchases"),
				"datatype": "Currency",
				"currency": self.currency,
			},
			{
				"value": self.unregistered_suppliers_total_vat,
				"indicator": "Green",
				"label": _("Unregistered Suppliers Total VAT"),
				"datatype": "Currency",
				"currency": self.currency,
			},
		]
