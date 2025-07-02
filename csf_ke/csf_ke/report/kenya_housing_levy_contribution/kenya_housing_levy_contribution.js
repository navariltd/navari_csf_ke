// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Kenya Housing Levy Contribution"] = {
  filters: [
    {
      fieldname: "company",
      label: __("Company"),
      fieldtype: "Link",
      options: "Company",
      default: frappe.defaults.get_user_default("Company"),
      reqd: 1,
    },
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      default: frappe.datetime.add_months(frappe.datetime.get_today(), -1), // Default to last month
      reqd: 1,
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
      reqd: 1,
    },
    {
      fieldname: "employee",
      label: __("Employee"),
      fieldtype: "Link",
      options: "Employee",
      get_query: function () {
        var company = frappe.query_report.get_filter_value("company");
        return {
          doctype: "Employee",
          filters: {
            company,
          },
        };
      },
    },
  ],
};
