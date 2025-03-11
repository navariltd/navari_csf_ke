// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Customer Addresses"] = {
  filters: [
    {
      fieldname: "account_manager",
      label: "Account Manager",
      fieldtype: "Link",
      options: "User",
      reqd: 0,
    },
    {
      fieldname: "customer_name",
      label: "Customer",
      fieldtype: "Link",
      options: "Customer",
      reqd: 0,
    },
    {
      fieldname: "customer_group",
      label: "Customer Group",
      fieldtype: "Link",
      options: "Customer Group",
      reqd: 0,
    },
  ],
};
