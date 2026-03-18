frappe.ui.form.on("Sales Invoice", {
  before_load: function (frm) {
    if (frm.doc.__islocal && frm.doc.amended_from) {
      frm.set_value("tax_invoice_number", "");
      frm.set_value("tax_invoice_date", "");
    }
  },

  onload: function (frm) {
    // Delay for 1 second and then trigger get_deposits
    if (frm.is_new() && !frm.doc.is_deposit_invoice) {
      setTimeout(function () {
        frm.events.get_deposits(frm, false);
      }, 1000);
    }
    // Disable add row on deposits
    frm.set_df_property("deposits", "cannot_add_rows", true); // Hide add row button
    frm.set_df_property("deposits", "cannot_delete_rows", true); // Hide delete button
    frm.set_df_property("deposits", "cannot_delete_all_rows", true); // Hide delete all button
  },

  is_deposit_invoice: function (frm) {
    csf_ke.deposit_utils.get_deposit_item(frm);
  },

  use_untied_deposit: function (frm) {
    frm.events.get_deposits(frm, true);
  },

  get_deposits: function (frm, is_button_clicked = true) {
    csf_ke.deposit_utils.get_deposits(frm, is_button_clicked);
  },
});
