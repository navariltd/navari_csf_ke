// Copyright (c) 2022, Navari Limited and contributors
// For license information, please see license.txt

frappe.query_reports["Kenya Purchase Tax Report"] = {
  filters: [
    {
      fieldname: "company",
      label: __("Company"),
      fieldtype: "Link",
      options: "Company",
      default: frappe.defaults.get_default("company"),
      reqd: 1,
    },
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
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
      fieldname: "item_tax_template",
      label: __("Item Tax Template"),
      fieldtype: "Link",
      options: "Item Tax Template",
      reqd: 0,
      hidden: 1,
    },
    {
      fieldname: "taxes_and_charges_template",
      label: __("Purchase Taxes and Charges Template"),
      fieldtype: "Link",
      options: "Purchase Taxes and Charges Template",
      reqd: 0,
      hidden: 1,
    },
    {
      fieldname: "accounting_dimension",
      label: __("Accounting Dimension"),
      fieldtype: "Select",
      options: ["", "Cost Center", "Project"],
      default: "",
      reqd: 0,
    },
    {
      fieldname: "is_return",
      label: __("Is Return"),
      fieldtype: "Check",
      default: 0,
      reqd: 0,
    },
  ],

  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    if (data && data.is_group_header) {
      if (
        [
          "accounting_dimension_value",
          "party_name",
          "taxable_amount",
          "vat_amount",
        ].includes(column.fieldname)
      ) {
        value = `<span style="font-weight: bold;">${value}</span>`;
      }
    }

    return value;
  },

  onload: function (report) {
    frappe.call({
      method: "frappe.client.get_value",
      args: {
        doctype: "Accounts Settings",
        fieldname: [
          "add_taxes_from_item_tax_template",
          "add_taxes_from_taxes_and_charges_template",
        ],
      },
      callback: function (r) {
        if (r.message) {
          const item_tax_template_filter =
            report.get_filter("item_tax_template");
          const taxes_and_charges_filter = report.get_filter(
            "taxes_and_charges_template",
          );
          if (item_tax_template_filter) {
            item_tax_template_filter.df.hidden =
              !r.message.add_taxes_from_item_tax_template;
            taxes_and_charges_filter.set_value("");
            item_tax_template_filter.refresh();
          }

          if (taxes_and_charges_filter) {
            taxes_and_charges_filter.df.hidden =
              !r.message.add_taxes_from_taxes_and_charges_template;
            item_tax_template_filter.set_value("");
            taxes_and_charges_filter.refresh();
          }
        }
      },
    });

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
          "csf_ke.csf_ke.report.kenya_purchase_tax_report.kenya_purchase_tax_report.download_custom_csv_format",
        args: {
          company: report.get_filter_value("company"),
          from_date: report.get_filter_value("from_date"),
          to_date: report.get_filter_value("to_date"),
        },
        callback: function (response) {
          if (response.message) {
            const fileLinks = Object.entries(response.message).map(
              ([template, fileUrl]) => {
                return `<a href="${fileUrl}" target="_blank">${template} Purchase Report</a>`;
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
            frappe.set_route("List", "File", {
              file_name: ["Like", `purchase`],
            });
          } else {
            frappe.msgprint(__("No files were generated"));
          }
        },
      });
    });
  },
};
