const doctype = "Supplier";

frappe.ui.form.on(doctype, {
  refresh: async function (frm) {
    let grid = frm.get_field("etims_id_mapping").grid;
    grid.cannot_add_rows = true;
    grid.cannot_delete_rows = true;
    grid.only_sortable();
    frm.refresh_field("etims_id_mapping");
  },
});
