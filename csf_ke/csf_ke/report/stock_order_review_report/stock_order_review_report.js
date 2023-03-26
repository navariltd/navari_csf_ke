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
            fieldname: "item",
            label: __("Item"),
            fieldtype: "Link",
            options: "Item",
            reqd: 0
        }
    ]
};
