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
      default: frappe.datetime.month_start(), // Set to the first date of the current month
      reqd: 1,
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      default: frappe.datetime.month_end(), // Set to the last date of the current month
      reqd: 1,
    },
    {
      fieldname: "sales_invoice",
      label: __("Sales Invoice"),
      fieldtype: "Link",
      options: "Sales Invoice",
    },
    {
      fieldname: "item_group",
      label: __("Item Group"),
      fieldtype: "Link",
      options: "Item Group",
    },
    // {
    //   fieldname: "sales_person",
    //   label: __("Sales Person"),
    //   fieldtype: "Link",
    //   options: "Sales Person",
    //   hidden: 1,
    // },
    // Add the following filters for item, item group, warehouse, and UOM
    {
      fieldname: "item",
      label: __("Item"),
      fieldtype: "Link",
      options: "Item",
    },
    {
      fieldname: "warehouse",
      label: __("Warehouse"),
      fieldtype: "Link",
      options: "Warehouse",
    },
    {
      fieldname: "uom",
      label: __("Include UOM"),
      fieldtype: "Link",
      options: "UOM",
    },
  ],
};
