// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Salary Register Summary With Monthly Comparison"] = {
  filters: [
    {
      fieldname: "from_date",
      label: __("From"),
      fieldtype: "Date",
      default: get_first_month_date(frappe.datetime.get_today()),
      reqd: 1,
      width: "100px",
    },
    {
      fieldname: "to_date",
      label: __("To"),
      fieldtype: "Date",
      default: get_last_date_of_next_month(frappe.datetime.get_today()),
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
    {
      fieldname: "department_breakdown",
      label: __("Department Breakdown"),
      fieldtype: "Check",
      default: 1,
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

function get_last_date_of_next_month(inputDate) {
  const date = new Date(inputDate);
  date.setMonth(date.getMonth() + 2, 0); // Move to next month + 1, day 0 gives last day of previous month
  return date;
}

function get_first_month_date(inputDate) {
  const date = new Date(inputDate);

  date.setDate(1);

  return date;
}
