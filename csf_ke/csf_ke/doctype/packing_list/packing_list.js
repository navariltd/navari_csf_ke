// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Packing List", {
  get_sales_invoices_and_items: function (frm) {
    frappe.call({
      method: "get_submitted_sales_invoices_and_items",
      doc: frm.doc,
      callback: function (r) {
        refresh_field("sales_invoices");
        refresh_field("pl_items");
      },
    });
  },

  before_save: function (frm) {
    frappe.call({
      method: "get_items",
      freeze: true,
      doc: frm.doc,
      callback: function () {
        refresh_field("pl_items");
      },
    });
  },
});
