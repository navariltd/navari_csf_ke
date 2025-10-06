// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("VAT Withholding", {
  before_save(frm) {
    if (
      frm.doc.vat_withholding_amount &&
      frm.doc.outstanding_amount &&
      frm.doc.vat_withholding_amount === frm.doc.outstanding_amount &&
      !frm.doc.allocate_payment
    ) {
      frm.set_value("allocate_payment", 1);
    }
  },

  company(frm) {
    frm.set_query("voucher_no", function () {
      return {
        filters: {
          docstatus: 1,
          company: frm.doc.company,
        },
      };
    });
  },

  invoice_no(frm) {
    if (!frm.doc.invoice_no) return;

    frappe.show_alert({
      message: "Fetching invoice details...",
      indicator: "blue",
    });

    try {
      const result = frm.call("set_missing_values").then((result) => {
        if (result.message) {
          frappe.show_alert({
            message: "Invoice details populated successfully",
            indicator: "green",
          });
          frm.refresh();
        } else {
          frappe.show_alert({
            message: "No matching invoice found",
            indicator: "orange",
          });
        }
      });
    } catch (err) {
      console.error(err);
      frappe.show_alert({
        message: "Error fetching invoice data",
        indicator: "red",
      });
    }
  },
});
