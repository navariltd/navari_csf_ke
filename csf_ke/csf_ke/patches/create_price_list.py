import erpnext
import frappe


def execute():
	currency = erpnext.get_default_currency()
	doc = frappe.new_doc("Price List")
	doc.update(
		{
			"doctype": "Price List",
			"price_list_name": "Last Selling Price",
			"enabled": 1,
			"buying": 0,
			"selling": 1,
			"currency": currency,
		},
	)

	doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
	frappe.db.commit()
