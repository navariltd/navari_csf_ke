// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Salary Register Summary With Monthly Comparison"] = {
  filters: [
    {
      fieldname: "from_date",
      label: __("From"),
      fieldtype: "Date",
      default: frappe.datetime.add_months(frappe.datetime.get_today(), -2),
      reqd: 1,
      width: "100px",
    },
    {
      fieldname: "to_date",
      label: __("To"),
      fieldtype: "Date",
      default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
      reqd: 1,
      width: "100px",
    },
    {
      fieldname: "currency",
      fieldtype: "Link",
      options: "Currency",
      label: __("Currency"),
      default: erpnext.get_currency(frappe.defaults.get_default("Company")),
      width: "50px",
    },
    {
      fieldname: "employee",
      label: __("Employee"),
      fieldtype: "Link",
      options: "Employee",
      width: "100px",
    },
    {
      fieldname: "company",
      label: __("Company"),
      fieldtype: "Link",
      options: "Company",
      default: frappe.defaults.get_user_default("Company"),
      width: "100px",
      reqd: 1,
    },
    {
      fieldname: "department",
      label: __("Department"),
      fieldtype: "Link",
      options: "Department",
      default: "",
      width: "100px",
      get_query: function () {
        var company = frappe.query_report.get_filter_value("company");
        return {
          doctype: "Department",
          filters: {
            company: company,
          },
        };
      },
    },
    {
      fieldname: "docstatus",
      label: __("Document Status"),
      fieldtype: "Select",
      options: ["Draft", "Submitted", "Cancelled"],
      default: "Submitted",
      width: "100px",
    },
  ],

  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    if (
      column.fieldname === "difference_amount" &&
      data &&
      data.difference_amount > 0
    ) {
      value = `<b style="color:green;">${value}</b>`;
    } else if (
      column.fieldname === "difference_amount" &&
      data &&
      data.difference_amount < 0
    ) {
      value = `<b style="color:red;">${value}</b>`;
    }

    if (data && data.is_title) {
      value = `<b>${value}</b>`;
    }
    return value;
  },
};
