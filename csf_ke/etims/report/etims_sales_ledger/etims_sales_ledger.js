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
      label: __("eTIMS Transaction Type"),
      fieldtype: "Select",
      options: "\nSales Invoice\nCredit Note",
    },
    {
      fieldname: "is_signed",
      label: __("eTIMS Signed Status"),
      fieldtype: "Select",
      options: "\nYes\nNo",
    },
    {
      fieldname: "sent_to_etims",
      label: __("Sent to eTIMS"),
      fieldtype: "Select",
      options: ["", __("Yes"), __("No")],
      default: "",
    },
    {
      fieldname: "reconciliation_status",
      label: __("Reconciliation Status"),
      fieldtype: "Select",
      options: [
        "",
        { label: __("Sent and Matched"), value: "Sent and Matched" },
        {
          label: __("Sent with Variance (>1%)"),
          value: "Sent with Variance (>1%)",
        },
        {
          label: __("Sent with Minor Variance (<1%)"),
          value: "Sent with Minor Variance (<1%)",
        },
        {
          label: __("Sent but No eTIMS Data"),
          value: "Sent but No eTIMS Data",
        },
        { label: __("Not Sent to eTIMS"), value: "Not Sent to eTIMS" },
        {
          label: __("eTIMS Data Found but Not Sent"),
          value: "eTIMS Data Found but Not Sent",
        },
        { label: __("Missing in ERPNext"), value: "Missing in ERPNext" },
      ],
      default: "",
    },
    {
      fieldname: "hide_matched",
      label: __("Hide Matched Invoices"),
      fieldtype: "Check",
      default: 0,
    },
  ],

  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    if (data && data.is_group && data.sales_invoice !== "TOTAL") {
      value = `<strong>${value}</strong>`;
    }

    if (
      column.fieldname === "difference" &&
      data &&
      data.sales_invoice !== "TOTAL"
    ) {
      let color = "#28a745";
      if (data.difference > 1) color = "#dc3545";
      else if (data.difference < -1) color = "#ffc107";
      value = data.is_group
        ? `<strong style="color:${color}">${value}</strong>`
        : `<span style="color:${color}">${value}</span>`;
    }

    if (
      column.fieldname === "tax_difference" &&
      data &&
      data.sales_invoice !== "TOTAL"
    ) {
      let color = "#28a745";
      if (data.tax_difference > 1) color = "#dc3545";
      else if (data.tax_difference < -1) color = "#ffc107";
      value = data.is_group
        ? `<strong style="color:${color}">${value}</strong>`
        : `<span style="color:${color}">${value}</span>`;
    }

    if (
      column.fieldname === "reconciliation_status" &&
      data &&
      data.sales_invoice !== "TOTAL"
    ) {
      let color = "#6c757d";
      if (data.reconciliation_status === "Sent and Matched") color = "#28a745";
      if (data.reconciliation_status === "Sent with Variance (>1%)")
        color = "#dc3545";
      if (data.reconciliation_status === "Sent with Minor Variance (<1%)")
        color = "#ffc107";
      if (data.reconciliation_status === "Sent but No eTIMS Data")
        color = "#fd7e14";
      if (data.reconciliation_status === "Not Sent to eTIMS") color = "#6c757d";
      if (data.reconciliation_status === "eTIMS Data Found but Not Sent")
        color = "#fd7e14";
      if (data.reconciliation_status === "Missing in ERPNext")
        color = "#6f42c1";
      value = data.is_group
        ? `<strong style="color:${color}">${value}</strong>`
        : `<span style="color:${color}">${value}</span>`;
    }

    if (
      column.fieldname === "etims_status" &&
      data &&
      data.sales_invoice !== "TOTAL"
    ) {
      let color = "#6c757d";
      if (data.etims_status === "Yes") color = "#28a745";
      if (data.etims_status === "No") color = "#fd7e14";
      value = data.is_group
        ? `<strong style="color:${color}">${value}</strong>`
        : `<span style="color:${color}">${value}</span>`;
    }

    return value;
  },

  onload: function (report) {
    const collapseAllRows = () => {
      setTimeout(() => {
        if (report.datatable) {
          report.collapse_all_rows();
        }
      }, 100);
    };

    report.after_refresh = function () {
      collapseAllRows();
    };

    collapseAllRows();
  },
};
