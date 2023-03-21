// Copyright (c) 2023, Navari Limited and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Stock Order Review Report"] = {
    "filters": [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd: 1
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.defaults.get_user_default("year_start_date"),
            reqd: 1
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.defaults.get_user_default("year_end_date"),
            reqd: 1
        },
        {
            fieldname: "stock_request_from",
            label: __("Stock Request From"),
            fieldtype: "Select",
            options: ["Branch Stock Request", "Region Stock Allocation"],
            default: "Branch Stock Request",
        },
        {
            fieldname: "warehouse",
            label: __("Warehouse"),
            fieldtype: "Link",
            options: "Warehouse",
            reqd: 0
        },
        {
            fieldname: "item",
            label: __("Item"),
            fieldtype: "Link",
            options: "Item",
            reqd: 0
        }
    ],

    onload: function(report) {
        let warehouse_field = report.get_filter('warehouse');

        warehouse_field.get_query = function() {
            let filters = [];
            filters.push(["Warehouse", "is_group", "=", 1])

            let stock_request_from_value = get_stock_request_from_value()
            if (stock_request_from_value === "Branch Stock Request") {
                filters.push(["Warehouse", "warehouse_type", "=", "SubRegion"])
            } else {
                filters.push(["Warehouse", "warehouse_type", "=", "Region"])
            }
            return {
                filters: filters
            }
        }

        function get_stock_request_from_value() {
            let stock_request_from_field = report.get_filter('stock_request_from');
            return stock_request_from_field ? stock_request_from_field.value : null
        }
    }
};
