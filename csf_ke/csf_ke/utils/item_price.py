import frappe


def update_item_price(doc, method=None):
	enable_auto_item_price_update = frappe.db.get_single_value(
		"Selling Settings", "custom_enable_auto_item_price_update"
	)
	if not enable_auto_item_price_update:
		return

	if doc.is_pos:
		return

	price_list = frappe.db.get_value(
		"Price List", {"price_list_name": "Last Selling Price"}, ["name", "currency"]
	)
	if not price_list:
		return

	company_currency = frappe.db.get_value("Company", doc.company, "default_currency")

	if price_list[1] != company_currency:
		return

	for item in doc.items:
		if not item.item_code or not item.base_rate:
			continue

		update_or_create_item_price(
			item_code=item.item_code,
			price_list_name=price_list[0],
			currency=price_list[1],
			price=item.base_rate,
			customer=doc.customer,
		)


def update_or_create_item_price(item_code, price_list_name, currency, price, customer):
	existing_item_price = frappe.db.exists(
		"Item Price",
		{"item_code": item_code, "price_list": price_list_name, "customer": customer},
	)

	if not existing_item_price:
		item_price_doc = frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": item_code,
				"price_list": price_list_name,
				"currency": currency,
				"price_list_rate": price,
				"customer": customer,
			}
		)
		item_price_doc.save(ignore_permissions=True)
		frappe.db.commit()

	else:
		item_price_doc = frappe.get_doc("Item Price", existing_item_price)
		if item_price_doc.price_list_rate != price:
			item_price_doc.price_list_rate = price
			item_price_doc.save(ignore_permissions=True)
