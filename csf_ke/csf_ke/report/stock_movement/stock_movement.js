// Copyright (c) 2025, Navari Limited and contributors
// For license information, please see license.txt

frappe.query_reports["Stock Movement"] = {
  filters: [
    {
      fieldname: "company",
      label: __("Company"),
      fieldtype: "Link",
      width: "80",
      options: "Company",
      default: frappe.defaults.get_default("company"),
    },
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      width: "80",
      reqd: 1,
      default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
    },
    {
      fieldname: "from_time",
      label: __("From Time"),
      fieldtype: "Time",
      default: "00:00:00",
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      width: "80",
      reqd: 1,
      default: frappe.datetime.get_today(),
    },
    {
      fieldname: "to_time",
      label: __("To Time"),
      fieldtype: "Time",
      default: "23:59:59",
    },
    {
      fieldname: "item_group",
      label: __("Item Group"),
      fieldtype: "Link",
      width: "80",
      options: "Item Group",
    },
    {
      fieldname: "item_code",
      label: __("Items"),
      fieldtype: "MultiSelectList",
      width: "80",
      options: "Item",
      get_data: async function (txt) {
        let item_group = frappe.query_report.get_filter_value("item_group");

        let filters = {
          ...(item_group && { item_group }),
          is_stock_item: 1,
        };

        let { message: data } = await frappe.call({
          method: "erpnext.controllers.queries.item_query",
          args: {
            doctype: "Item",
            txt: txt,
            searchfield: "name",
            start: 0,
            page_len: 10,
            filters: filters,
            as_dict: 1,
          },
        });

        data = data.map(({ name, ...rest }) => {
          return {
            value: name,
            description: Object.values(rest),
          };
        });

        return data || [];
      },
    },
    {
      fieldname: "price_list",
      label: __("Selling Price"),
      fieldtype: "Link",
      width: "80",
      options: "Price List",
      get_query: function () {
        return {
          filters: {
            selling: 1,
          },
        };
      },
    },
    {
      fieldname: "warehouse_type",
      label: __("Warehouse Type"),
      fieldtype: "Link",
      width: "80",
      options: "Warehouse Type",
    },
    {
      fieldname: "warehouse",
      label: __("Warehouses"),
      fieldtype: "MultiSelectList",
      width: "80",
      options: "Warehouse",
      get_data: (txt) => {
        let warehouse_type =
          frappe.query_report.get_filter_value("warehouse_type");
        let company = frappe.query_report.get_filter_value("company");

        let filters = {
          ...(warehouse_type && { warehouse_type }),
          ...(company && { company }),
        };

        return frappe.db.get_link_options("Warehouse", txt, filters);
      },
    },
    {
      fieldname: "valuation_field_type",
      label: __("Valuation Field Type"),
      fieldtype: "Select",
      width: "80",
      options: "Currency\nFloat",
      default: "Currency",
    },
    {
      fieldname: "include_uom",
      label: __("Include UOM"),
      fieldtype: "Link",
      options: "UOM",
    },
    {
      fieldname: "show_variant_attributes",
      label: __("Show Variant Attributes"),
      fieldtype: "Check",
    },
    {
      fieldname: "show_stock_ageing_data",
      label: __("Show Stock Ageing Data"),
      fieldtype: "Check",
    },
    {
      fieldname: "ignore_closing_balance",
      label: __("Ignore Closing Balance"),
      fieldtype: "Check",
      default: 0,
    },
    {
      fieldname: "include_zero_stock_items",
      label: __("Include Zero Stock Items"),
      fieldtype: "Check",
      default: 0,
    },
    {
      fieldname: "show_dimension_wise_stock",
      label: __("Show Dimension Wise Stock"),
      fieldtype: "Check",
      default: 0,
    },
  ],

  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    const qty_colors = {
      in_qty: "in",
      stock_recon_in: "in",
      purchased_qty: "in",
      stock_in_qty: "in",
      stock_out_qty: "out",
      out_qty: "out",
      sales_qty: "out",
      stock_recon_out: "out",
    };

    if (qty_colors[column.fieldname] && value) {
      if (qty_colors[column.fieldname] === "in") {
        value = `<span style="color: green;">${value}</span>`;
      } else if (qty_colors[column.fieldname] === "out") {
        value = `<span style="color: red;">${value}</span>`;
      }
    }

    // Stock variance
    if (column.fieldname === "stock_variance" && value) {
      if (data.stock_variance < 0) {
        value = `<span style="color:red;font-weight:bold">${value}</span>`;
      } else if (data.stock_variance > 0) {
        value = `<span style="color:green;font-weight:bold">${value}</span>`;
      }
    }

    // Sales variance
    if (column.fieldname === "sales_variance" && value) {
      if (data.sales_variance < 0) {
        value = `<span style="color:red;font-weight:bold">${value}</span>`;
      } else if (data.sales_variance > 0) {
        value = `<span style="color:green;font-weight:bold">${value}</span>`;
      }
    }

    return value;
  },
};

erpnext.utils.add_inventory_dimensions("Stock Movement", 8);
