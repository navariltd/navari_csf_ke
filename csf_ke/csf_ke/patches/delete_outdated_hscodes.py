import json
import os

import frappe


def execute():
	base_path = frappe.get_module_path("csf_ke")
	json_file_path = os.path.join(base_path, "doctype", "tims_hscode", "tims_hscode_data.json")

	if not os.path.exists(json_file_path):
		frappe.log_error("TIMs HSCode JSON file not found", "Migration Error")
		return

	with open(json_file_path) as file:
		data = json.load(file)

	if not data:
		return

	hs_codes = [record["name"] for record in data]

	outdated_hscodes = frappe.get_all("TIMs HSCode", filters={"name": ["not in", hs_codes]})

	if not outdated_hscodes:
		return

	for hscode in outdated_hscodes:
		frappe.delete_doc("TIMs HSCode", hscode.name)
