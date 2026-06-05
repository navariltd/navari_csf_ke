frappe.ui.form.on("Customer", {
  refresh: function (frm) {
    let grid = frm.get_field("etims_id_mapping").grid;
    grid.cannot_add_rows = true;
    grid.cannot_delete_rows = true;
    grid.only_sortable();
    frm.refresh_field("etims_id_mapping");
    set_kra_pin_required(frm);
  },

  customer_group: function (frm) {
    set_kra_pin_required(frm);
  },
});

function set_kra_pin_required(frm) {
  if (!frm.doc.customer_group) return;

  frappe.call({
    method: "frappe.client.get_value",
    args: {
      doctype: "Customer Group",
      filters: { name: frm.doc.customer_group },
      fieldname: "custom_is_kra_pin_mandatory_in",
    },
    callback: function (r) {
      if (r.message && r.message.custom_is_kra_pin_mandatory_in) {
        let kra_required_in = r.message.custom_is_kra_pin_mandatory_in;

        let is_mandatory = ["Customer", "All"].includes(kra_required_in);

        frm.set_df_property("tax_id", "reqd", is_mandatory);
      }
    },
  });
}
