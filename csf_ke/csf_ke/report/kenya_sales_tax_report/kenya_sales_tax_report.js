// Copyright (c) 2022, Navari Limited and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Kenya Sales Tax Report"] = {
  filters: [
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
      fieldname: "from_date",
      label: __("Start Date"),
      fieldtype: "Date",
      default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
      reqd: 1,
      width: "100px",
    },
    {
      fieldname: "to_date",
      label: __("End Date"),
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
      reqd: 1,
      width: "100px",
    },
    {
      fieldname: "is_return",
      label: __("Is Return"),
      fieldtype: "Select",
      options: ["", "Is Return", "Normal Sales Invoice"],
      default: "",
      reqd: 0,
      width: "100px",
    },
    {
      fieldname: "tax_template",
      label: __("Tax Template"),
      fieldtype: "Link",
      options: "Item Tax Template",
      reqd: 0,
      width: "100px",
    },
    {
      fieldname: "accounting_dimension",
      label: __("Accounting Dimension"),
      fieldtype: "Select",
      options: ["", "Cost Center", "Project"],
      default: "",
      reqd: 0,
      width: "120px",
    },
  ],

  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    // Bold formatting for group header rows
    if (data && data.is_group_header) {
      if (
        [
          "taxable_value",
          "amount_of_vat",
          "name_of_purchaser",
          "accounting_dimension_value",
        ].includes(column.fieldname)
      ) {
        value = `<span style="font-weight: bold;">${value}</span>`;
      }
    }

    return value;
  },

  onload: function (report) {
    frappe.call({
      method: "frappe.client.get_list",
      args: {
        doctype: "Accounting Dimension",
        fields: ["document_type"],
        filters: {
          disabled: 0,
        },
      },
      callback: function (r) {
        let options = ["", "Cost Center", "Project"];
        if (r.message) {
          r.message.forEach(function (d) {
            if (!options.includes(d.document_type)) {
              options.push(d.document_type);
            }
          });
        }
        let dimension_filter = report.get_filter("accounting_dimension");
        if (dimension_filter) {
          dimension_filter.df.options = options;
          dimension_filter.refresh();
        }
      },
    });

    report.page.add_menu_item("Export CSVs", function () {
      frappe.call({
        method:
          "csf_ke.csf_ke.report.kenya_sales_tax_report.kenya_sales_tax_report.download_custom_csv_format",
        args: {
          company: report.get_filter_value("company"),
          from_date: report.get_filter_value("from_date"),
          to_date: report.get_filter_value("to_date"),
        },
        callback: function (response) {
          if (response.message) {
            const fileLinks = Object.entries(response.message).map(
              ([template, fileUrl]) => {
                return `<a href="${fileUrl}" target="_blank">${template} Sales Report</a>`;
              },
            );

            // Display links in a modal
            frappe.msgprint({
              title: __("CSV Download Links"),
              message: __(
                "The files have been successfully generated. Redirecting to the File List...",
              ),
              indicator: "green",
            });

            // Redirect to the File List
            frappe.set_route("List", "File", { file_name: ["Like", `sales`] });
          } else {
            frappe.msgprint(__("No files were generated"));
          }
        },
      });
    });
  },
};
