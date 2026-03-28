// Copyright (c) 2026, Navari Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("User Permission Migration Tool", {
  refresh(frm) {
    frm.add_custom_button("Run Migration", () => {
      frappe.call({
        method: "run_permission_migration",
        doc: frm.doc,
        args: {
          docname: frm.doc.name,
        },
        freeze: true,
        freeze_message: "Starting migration...",
      });
    });
  },
});
