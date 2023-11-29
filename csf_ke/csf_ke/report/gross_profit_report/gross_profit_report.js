frappe.query_reports["Gross Profit Report"] = {
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
      default: frappe.defaults.get_user_default("year_start_date"),
      reqd: 1,
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      default: frappe.defaults.get_user_default("year_end_date"),
      reqd: 1,
    },
    {
      fieldname: "sales_invoice",
      label: __("Sales Invoice"),
      fieldtype: "Link",
      options: "Sales Invoice",
    },
    {
      fieldname: "group_by",
      label: __("Group By"),
      fieldtype: "Select",
      options: "Item Code",
      default: "Item Code",
    },
    {
      fieldname: "item_group",
      label: __("Item Group"),
      fieldtype: "Link",
      options: "Item Group",
    },
    {
      fieldname: "sales_person",
      label: __("Sales Person"),
      fieldtype: "Link",
      options: "Sales Person",
    },
    {
      fieldname: "warehouse",
      label: __("Warehouse"),
      fieldtype: "Link",
      options: "Warehouse",
      get_query: function () {
        var company = frappe.query_report.get_filter_value("company");
        return {
          filters: [["Warehouse", "company", "=", company]],
        };
      },
    },
    {
      fieldname: "uom",
      label: __("Include UOM"),
      fieldtype: "Link",
      options: "UOM",
    },
  ],
  tree: true,
  name_field: "parent",
  parent_field: "parent_invoice",
  initial_depth: 3,
  formatter: function (value, row, column, data, default_formatter) {
    if (
      column.fieldname == "sales_invoice" &&
      column.options == "Item" &&
      data &&
      data.indent == 0
    ) {
      column._options = "Sales Invoice";
    } else {
      column._options = "";
    }
    value = default_formatter(value, row, column, data);

    if (data && (data.indent == 0.0 || (row[1] && row[1].content == "Total"))) {
      value = $(`<span>${value}</span>`);
      var $value = $(value).css("font-weight", "bold");
      value = $value.wrap("<p></p>").parent().html();
    }

    return value;
  },
};
