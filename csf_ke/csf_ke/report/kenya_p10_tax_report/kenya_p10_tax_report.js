// Copyright (c) 2023, Navari Limited and contributors
// For license information, please see license.txt

frappe.query_reports["Kenya P10 Tax Report"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"width": "100px",
			"reqd": 1,
			"on_change": () => {
				var company = frappe.query_reports.get_filter_value('company');

				if (company) {
					frappe.db.get_value('Company', company, "tax_id", (value) => {
							frappe.query_reports.set_filter_value('company_tax_id', value["tax_id"]);
						});
				}
			}
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(),-1),
			"reqd": 1,
			"width": "100px"
		},
		{
			"fieldname": "to_date",
			"label": __("End Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1,
			"width": "100px"
		},
		{
			"fieldname": "employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"reqd": 0,
			"width": "100px",
		}
	]
};
