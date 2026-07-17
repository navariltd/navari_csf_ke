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
      fieldname: "is_return",
      label: __("Is Return"),
      fieldtype: "Check",
      default: 0,
      reqd: 0,
    },
  ],

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
  },
};
