import frappe
from frappe import _
from frappe.utils import get_link_to_form


def validate_deposit_item(doc, method):
	# Deposit Item must not be a stock item.
	if doc.is_stock_item:
		doc.is_deposit_item = 0
	# Only 1 active deposit item allowed
	if doc.is_deposit_item and not doc.disabled:
		existing_deposit_item = frappe.get_all(
			"Item", filters={"is_deposit_item": 1, "name": ("!=", doc.name), "disabled": 0}, limit=1
		)
		if existing_deposit_item:
			frappe.throw(
				_(
					"Another item is already set as a Deposit Item. "
					"Only one Deposit Item can be active at a time."
				)
			)


@frappe.whitelist()
def get_deposit_item(company):
	# Fetch the deposit item
	deposit_item = frappe.db.get_value(
		"Item", {"is_deposit_item": 1, "disabled": 0}, ["name", "item_name", "stock_uom"], as_dict=True
	)
	if not deposit_item:
		frappe.throw(_("No active Deposit Item"))

	# Fetch the sales_deposit_account from item_defaults for the correct company
	item_default = frappe.db.get_value(
		"Item Default",
		{"parent": deposit_item["name"], "company": company},
		["sales_deposit_account", "purchase_deposit_account", "selling_cost_center", "buying_cost_center"],
		as_dict=True,
	)
	if (
		not item_default
		or not item_default.get("sales_deposit_account")
		or not item_default.get("purchase_deposit_account")
	):
		link = get_link_to_form("Item", deposit_item["name"])
		frappe.throw(
			_("{}'s Deposit Account is not set in Item Defaults").format(link),
		)

	# Return the deposit item details with the account
	return {
		"item_code": deposit_item["name"],
		"item_name": deposit_item["item_name"],
		"sales_deposit_account": item_default["sales_deposit_account"],
		"purchase_deposit_account": item_default["purchase_deposit_account"],
		"uom": deposit_item["stock_uom"],
		"selling_cost_center": item_default["selling_cost_center"],
		"buying_cost_center": item_default["buying_cost_center"],
	}
