frappe.ui.form.on("Sales Order", {
  refresh: function (frm) {
    csf_ke.deposit_utils.add_create_deposit_button(frm);
  },
});
