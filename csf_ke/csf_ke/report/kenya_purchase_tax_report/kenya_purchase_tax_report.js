// Copyright (c) 2022, Navari Limited and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Kenya Purchase Tax Report"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"width": "100px",
			"reqd": 1
		},
		{
			"fieldname":"from_date",
			"label": __("Start Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(),-1),
			"reqd": 1,
			"width": "100px"
		},
		{
			"fieldname":"to_date",
			"label": __("End Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1,
			"width": "100px"
		},
		{
			"fieldname":"is_return",
			"label": __("Is Return"),
			"fieldtype": "Select",
			"options": ["","Is Return","Normal Purchase Invoice"],
			"default": "",
			"reqd": 0,
			"width": "100px"
		},
		{
			"fieldname":"tax_template",
			"label": __("Tax Template"),
			"fieldtype": "Link",
			"options": "Item Tax Template",
			"reqd": 0,
			"width": "100px"
		}
	]
};
