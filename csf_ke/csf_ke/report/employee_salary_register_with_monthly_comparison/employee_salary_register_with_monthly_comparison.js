// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Salary Register With Monthly Comparison"] = {
  filters: [
    {
      fieldname: "from_date",
      label: __("From"),
      fieldtype: "Date",
      default: frappe.datetime.add_months(frappe.datetime.month_start(), -2),
      reqd: 1,
      width: "100px",
    },
    {
      fieldname: "to_date",
      label: __("To"),
      fieldtype: "Date",
      default: frappe.datetime.add_months(frappe.datetime.month_end(), -2),
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
};

function get_last_month_date(inputDate) {
  const date = new Date(inputDate);

  if (date.getMonth() === 11) {
    date.setFullYear(date.getFullYear() + 1);
    date.setMonth(0);
  } else {
    date.setMonth(date.getMonth() + 1);
  }
  date.setDate(1);

  date.setDate(date.getDate() - 1);

  return date;
}

function get_first_month_date(inputDate) {
  const date = new Date(inputDate);

  date.setDate(1);

  return date;
}
