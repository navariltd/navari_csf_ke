// Copyright (c) 2026, Navari Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("eTims Job Queue", {
  refresh(frm) {
    if (frm.doc.status == "Failed" || frm.doc.status == "Pending") {
      frm.add_custom_button(__("Execute Request"), () => {
        frm.call({
          doc: frm.doc,
          method: "run_queue",
          freeze: true,
          freeze_message: __("Executing Request"),
          callback: function () {
            frm.reload_doc();
          },
        });
      });
    }
  },
});
