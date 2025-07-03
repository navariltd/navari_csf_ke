// Copyright (c) 2022, Navari Limited and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Kenya P9A Tax Deduction Card Report"] = {
  onload(report) {
    report.page.add_inner_button("Print", function () {
      const filters = report.get_filter_values();
      const encodedFilters = encodeURIComponent(JSON.stringify(filters));
      const reportName = report.report_doc.report_name;

      const url = `/api/method/csf_ke.csf_ke.report.kenya_p9a_tax_deduction_card_report.custom_kenya_p9a_tax_deduction_card_print_report.print_report?report_name=${reportName}&filters=${encodedFilters}`;

      window.open(url, "_blank");
    });
  },
  filters: [
    {
      fieldname: "company",
      label: __("Company"),
      fieldtype: "Link",
      options: "Company",
      default: frappe.defaults.get_user_default("Company"),
      width: "100px",
      reqd: 1,
      on_change: function (query_report) {
        var company = frappe.query_report.get_filter_value("company");

        if (company) {
          frappe.db.get_value("Company", company, "tax_id", function (value) {
            frappe.query_report.set_filter_value(
              "company_tax_id",
              value["tax_id"]
            );
          });
        }
      },
    },
    {
      fieldname: "employee",
      label: __("Employee"),
      fieldtype: "Link",
      options: "Employee",
      width: "100px",
      reqd: 1,
      get_query: function () {
        var company = frappe.query_report.get_filter_value("company");
        return {
          doctype: "Employee",
          filters: {
            company: company,
          },
        };
      },
      on_change: function (query_report) {
        var employee = query_report.get_values().employee;
        if (!employee) {
          return;
        }
        frappe.model.with_doc("Employee", employee, function (r) {
          var emp = frappe.model.get_doc("Employee", employee);
          frappe.query_report.set_filter_value({
            employee_name: emp.employee_name,
            employee_tax_id: emp.tax_id,
          });
        });
        var company = frappe.query_report.get_filter_value("company");

        if (company) {
          frappe.db.get_value("Company", company, "tax_id", function (value) {
            frappe.query_report.set_filter_value(
              "company_tax_id",
              value["tax_id"]
            );
          });
        }
      },
    },
    {
      fieldname: "fiscal_year",
      label: __("Year"),
      fieldtype: "Link",
      options: "Fiscal Year",
      default: frappe.defaults.get_user_default("fiscal_year"),
      reqd: 1,
    },
    {
      fieldname: "currency",
      fieldtype: "Link",
      options: "Currency",
      label: __("Currency"),
      default: erpnext.get_currency(frappe.defaults.get_default("Company")),
      read_only: 1,
      width: "50px",
    },
    {
      fieldname: "company_tax_id",
      label: __("Company Tax Id"),
      fieldtype: "Data",
      hidden: 1,
    },
    {
      fieldname: "employee_name",
      label: __("Employee Name"),
      fieldtype: "Data",
      hidden: 1,
    },
    {
      fieldname: "employee_tax_id",
      label: __("Employee Tax Id"),
      fieldtype: "Data",
      hidden: 1,
    },
  ],
};
