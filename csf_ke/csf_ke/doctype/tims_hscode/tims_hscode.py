# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import json
import os

import frappe
from frappe.model.document import Document


class TIMsHSCode(Document):
	pass


def insert_new_records():
	uom_list = ["Kg", "Litre"]
	for uom in uom_list:
		if not frappe.db.exists("UOM", uom):
			frappe.get_doc({"doctype": "UOM", "uom_name": uom, "enabled": 1}).insert(ignore_permissions=True)

	base_path = frappe.get_module_path("csf_ke")
	json_file_path = os.path.join(base_path, "doctype", "tims_hscode", "tims_hscode_data.json")

	if not os.path.exists(json_file_path):
		frappe.log_error("TIMs HSCode JSON file not found", "Migration Error")
		return

	with open(json_file_path) as file:
		data = json.load(file)

	for record in data:
		existing_record = frappe.get_all("TIMs HSCode", filters={"name": record["name"]}, fields=["name"])

		if not existing_record:
			doc = frappe.get_doc(
				{
					"doctype": "TIMs HSCode",
					"name": record["name"],
					"tims_hscode": record["tims_hscode"],
					"description": record["description"],
					"disabled": record["disabled"],
					"docstatus": record["docstatus"],
					"item_tax": record["item_tax"],
					"uom": record["uom"],
					"vat_": record["vat_"],
				}
			)
			doc.insert(ignore_permissions=True)
			frappe.logger().info(f"Inserted: {record['name']}")

		else:
			doc = frappe.get_doc("TIMs HSCode", existing_record[0]["name"])

			if doc.description != record["description"]:
				doc.description = record["description"]
				doc.save()
				frappe.logger().info(f"Updated: {record['name']}")
			else:
				frappe.logger().info(f"Skipped (No Changes): {record['name']}")
