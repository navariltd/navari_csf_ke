// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Bank Remittance Enhanced"] = {
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
      default: frappe.datetime.month_start(),
      reqd: 1,
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      default: frappe.datetime.month_end(),
      fieldtype: "Date",
      reqd: 1,
    },
    {
      fieldname: "payroll_entry",
      label: __("Payroll Entry"),
      fieldtype: "Link",
      options: "Payroll Entry",
      get_query: function () {
        var company = frappe.query_report.get_filter_value("company");
        return {
          filters: { company: company },
        };
      },
    },
    {
      fieldname: "salary_slip_status",
      label: __("Salary Slip Status"),
      fieldtype: "Select",
      options: ["Submitted", "Draft"],
      default: "Submitted",
      reqd: 1,
    },
  ],
};
