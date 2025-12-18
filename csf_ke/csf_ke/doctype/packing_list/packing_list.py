# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class PackingList(Document):
	# Get submitted sales invoices
	@frappe.whitelist()
	def get_submitted_sales_invoices_and_items(self):
		# Validations
		if not self.territory:
			frappe.throw(
				_("Please select the Territory/Route Filter"),
				title=_("Territory/Route Required"),
			)

		if not self.from_date:
			frappe.throw(_("Please select the From Date Filter"), title=_("From Date Required"))

		if not self.to_date:
			frappe.throw(_("Please select the To Date Filter"), title=_("To Date Required"))
		# End Validations

		""" Pull sales invoices which are submitted based on criteria selected"""
		submitted_si = get_sales_invoices(self)

		if submitted_si:
			self.add_si_in_table(submitted_si)
			self.get_items()
			frappe.msgprint(
				_("Packing List generation completed"),
				title=_("Packing List Generation"),
			)
		else:
			frappe.msgprint(_("Sales invoices are not available for packing list"))

	# Add submitted sales invoices in table
	def add_si_in_table(self, submitted_si):
		"""Add sales invoices in the table"""
		self.set("sales_invoices", [])

		for data in submitted_si:
			credit_note_base_grand_total = get_credit_notes(self, data.name, "p_base_grand_total")
			credit_note_total_qty = get_credit_notes(self, data.name, "p_total_qty")
			self.append(
				"sales_invoices",
				{
					"sales_invoice": data.name,
					"customer": data.customer,
					"sales_invoice_date": data.posting_date,
					"grand_total": data.base_grand_total,
					"returned_grand_total": credit_note_base_grand_total,
					"net_total": (data.base_grand_total + credit_note_base_grand_total),
					"total_qty": data.total_qty,
					"returned_total_qty": credit_note_total_qty,
					"net_qty": (data.total_qty + credit_note_total_qty),
				},
			)

	# Get Items
	@frappe.whitelist()
	def get_items(self):
		self.get_si_items()

	# Get list of Sales Invoices for Items
	def get_si_list(self, field, table):
		"""Returns a list of Sales Invoices from the respective tables"""
		si_list = [d.get(field) for d in self.get(table) if d.get(field)]
		return si_list

	# Get list of Sales Invoice Items query
	def get_si_items(self):
		# Check for empty table or empty rows
		if not self.get("sales_invoices") or not self.get_si_list("sales_invoice", "sales_invoices"):
			frappe.throw(
				_("Please fill the Sales Invoices table"),
				title=_("Sales Invoices Required"),
			)

		si_list = self.get_si_list("sales_invoice", "sales_invoices")

		if not si_list:
			return []

		placeholders = ", ".join(["%s"] * len(si_list))

		items = frappe.db.sql(
			f"""
				SELECT
					item_code,
					item_name,
					warehouse,
					uom,
					description,
					ifnull(sum(qty),0) as qty
				FROM `tabSales Invoice Item`
				WHERE parent in ({placeholders})
				GROUP BY item_code, item_name, warehouse, uom, description
				ORDER BY item_name
			""",
			tuple(si_list),
			as_dict=1,
		)

		self.add_items(items)

	# Add sales invoice items
	def add_items(self, items):
		self.set("pl_items", [])
		for data in items:
			credit_note_qty = get_credit_note_items(self, data.item_code)
			self.append(
				"pl_items",
				{
					"item_code": data.item_code,
					"item_name": data.item_name,
					"warehouse": data.warehouse,
					"invoiced_qty": data.qty,
					"returned_qty": credit_note_qty,
					"packed_qty": (data.qty + credit_note_qty),
					"uom": data.uom,
					"description": data.description,
				},
			)


# Get submitted sales invoices query
def get_sales_invoices(doc: Document):
	si_filter = ""

	if doc.territory:
		si_filter += " and si.territory = %(territory)s"
	if doc.customer:
		si_filter += " and si.customer = %(customer)s"
	if doc.from_date:
		si_filter += " and si.posting_date >= %(from_date)s"
	if doc.to_date:
		si_filter += " and si.posting_date <= %(to_date)s"

	submitted_si = frappe.db.sql(
		f"""
        SELECT distinct si.name,
            si.posting_date,
            si.customer,
            si.base_grand_total,
            si.total_qty
        FROM `tabSales Invoice` si
        WHERE si.docstatus = 1
            AND si.is_return != 1
            AND si.company = %(company)s
            {si_filter}
            AND (
                si.name NOT in (
                    SELECT plsi.sales_invoice
                    FROM `tabPacking List Sales Invoice` plsi,
                        `tabPacking List` pl
                    WHERE plsi.parent = pl.name
                        and pl.docstatus != 2
                )
            )
        ORDER BY si.customer
        """,
		{
			"territory": doc.territory,
			"customer": doc.customer,
			"from_date": doc.from_date,
			"to_date": doc.to_date,
			"company": doc.company,
		},
		as_dict=1,
	)
	return submitted_si


# Get submitted credit notes query
def get_credit_notes(self, original_sales_invoice, pwhich):
	si_filter = ""
	if original_sales_invoice:
		si_filter += " and si.return_against = %(original_sales_invoice)s"

	cr_grand_total = 0
	cr_total_qty = 0

	submitted_cr = frappe.db.sql(
		"""
        SELECT DISTINCT si.name,
            ifnull(sum(si.base_grand_total), 0) as base_grand_total,
            ifnull(sum(si.total_qty), 0) as total_qty
        FROM `tabSales Invoice` si
        WHERE si.docstatus = 1
            AND si.is_return = 1
            AND si.company = %(company) s { 0 }
            AND (
                si.name not in (
                    SELECT plsi.sales_invoice
                    FROM `tabPacking List Sales Invoice` plsi,
                        `tabPacking List` pl
                    WHERE plsi.parent = pl.name
                        AND pl.docstatus != 2
                )
            )
        GROUP BY si.name
        """,
		{"original_sales_invoice": original_sales_invoice, "company": self.company},
		as_dict=1,
	)

	if submitted_cr:
		for credit_note in submitted_cr:
			cr_grand_total += credit_note.base_grand_total
			cr_total_qty += credit_note.total_qty

	if pwhich == "p_base_grand_total":
		return cr_grand_total
	else:
		return cr_total_qty


# Get list of Credit Note Items query
def get_credit_note_items(self, item_code):
	si_list = self.get_si_list("sales_invoice", "sales_invoices")

	cr_total_qty = 0

	placeholders = ", ".join(["%s"] * len(si_list))

	cr_items = frappe.db.sql(
		f"""
			SELECT
				si_item.item_code,
				IFNULL(SUM(si_item.qty),0) as qty
            FROM `tabSales Invoice Item` si_item
			JOIN `tabSales Invoice` si
				ON si_item.parent = si.name
            WHERE si_item.item_code = %s
            	AND si.return_against in ({placeholders})
            GROUP BY si_item.item_code
		""",
		tuple([item_code, *si_list]),
		as_dict=1,
	)

	if cr_items:
		for credit_note_qty in cr_items:
			cr_total_qty += credit_note_qty.qty

	return cr_total_qty
