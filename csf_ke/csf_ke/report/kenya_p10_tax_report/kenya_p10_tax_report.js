// Copyright (c) 2023, Navari Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('Salary Slip', {
    onload: function(frm) {
        let today = frappe.datetime.now_date();
        let startOfMonth = frappe.datetime.month_start(today);
        let endOfMonth = frappe.datetime.month_end(today);

        frm.set_df_property('from_date', 'default', startOfMonth);
        frm.set_df_property('to_date', 'default', endOfMonth);
    }
});

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
			"default": frappe.datetime.month_start(frappe.datetime.now_date())
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.month_end(frappe.datetime.now_date())
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
