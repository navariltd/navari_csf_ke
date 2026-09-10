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
      label: __("Reconciliation Filter"),
      fieldtype: "Data",
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
      (column.fieldname === "difference" ||
        column.fieldname === "tax_difference") &&
      data &&
      data.sales_invoice !== "TOTAL"
    ) {
      let net_erp = flt(data.erp_invoice_amount) - flt(data.erp_credit_amount);
      let val = flt(data[column.fieldname]);
      let pct = net_erp ? (Math.abs(val) / Math.abs(net_erp)) * 100 : 0;

      let color = "#28a745";
      if (pct > 1) color = "#dc3545";

      value = data.is_group
        ? `<strong style="color:${color}">${value}</strong>`
        : `<span style="color:${color}">${value}</span>`;
    }

    if (
      column.fieldname === "reconciliation_status" &&
      data &&
      data.sales_invoice !== "TOTAL"
    ) {
      let color = "#28a745";
      if (data.reconciliation_status.includes("ERROR")) color = "#dc3545";
      else if (data.reconciliation_status.includes("Date Mismatch"))
        color = "#fd7e14";

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
