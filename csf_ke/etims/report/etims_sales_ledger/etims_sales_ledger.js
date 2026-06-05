// Copyright (c) 2026, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["eTIMS Sales Ledger"] = {
  tree: true,
  name_field: "sales_invoice",
  parent_field: "parent",
  indent_field: "indent",

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
      reqd: 1,
      default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      reqd: 1,
      default: frappe.datetime.get_today(),
    },
    {
      fieldname: "sales_invoice",
      label: __("Sales Invoice"),
      fieldtype: "Link",
      options: "Sales Invoice",
    },
    {
      fieldname: "customer",
      label: __("Customer"),
      fieldtype: "Link",
      options: "Customer",
    },
    {
      fieldname: "type",
      label: __("Type"),
      fieldtype: "Select",
      options: "\nSales Invoice\nCredit Note",
    },
    {
      fieldname: "is_signed",
      label: __("Is Signed"),
      fieldtype: "Select",
      options: "\nYes\nNo",
    },
    {
      fieldname: "show_details",
      label: __("Show Details"),
      fieldtype: "Check",
      default: 0,
      on_change: function () {
        frappe.query_report.refresh();
        setTimeout(() => {
          const v = frappe.query_report.get_filter_value("show_details");
          v
            ? frappe.query_report.expand_all_rows()
            : frappe.query_report.collapse_all_rows();
        }, 120);
      },
    },
  ],

  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    if (data && data.is_group) {
      value = `<strong>${value}</strong>`;
    }

    if (column.fieldname === "difference" && data) {
      let color = "#28a745";
      if (data.difference > 1) color = "#dc3545";
      else if (data.difference < -1) color = "#ffc107";

      value = data.is_group
        ? `<strong style="color:${color}">${value}</strong>`
        : `<span style="color:${color}">${value}</span>`;
    }
    if (column.fieldname === "tax_difference" && data) {
      let color = "#28a745";
      if (data.tax_difference > 1) color = "#dc3545";
      else if (data.tax_difference < -1) color = "#ffc107";

      value = data.is_group
        ? `<strong style="color:${color}">${value}</strong>`
        : `<span style="color:${color}">${value}</span>`;
    }

    if (column.fieldname === "reconciliation_status" && data) {
      let color = "#6c757d";

      if (data.reconciliation_status === "Matched") color = "#28a745";
      if (data.reconciliation_status === "Amount Mismatch") color = "#dc3545";
      if (data.reconciliation_status === "Missing in ERPNext")
        color = "#fd7e14";

      value = data.is_group
        ? `<strong style="color:${color}">${value}</strong>`
        : `<span style="color:${color}">${value}</span>`;
    }

    return value;
  },

  onload: function (report) {
    report.after_refresh = function () {
      const show = this.get_filter_value("show_details");
      show ? this.expand_all_rows() : this.collapse_all_rows();
    };

    setTimeout(() => {
      report.collapse_all_rows();
    }, 300);
  },
};
