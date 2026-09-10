// Copyright (c) 2026, Navari Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("eTims Queue Manager", {
  refresh(frm) {
    frm.add_custom_button(
      __("Process Queue"),
      () => {
        frappe.call({
          method: "process_queue",
          doc: frm.doc,
          callback: () => frm.reload_doc(),
        });
      },
      __("eTims Actions"),
    );

    frm.add_custom_button(
      __("Sync Queue"),
      () => {
        frappe.call({
          method: "sync_queue",
          doc: frm.doc,
          callback: () => frm.reload_doc(),
        });
      },
      __("eTims Actions"),
    );

    frm.add_custom_button(
      __("Clear All Jobs"),
      () => {
        frappe.confirm(
          __(
            "Clear the current job pointers and delete ALL eTims Job Queue records?",
          ),
          () => {
            frappe.call({
              method: "clear_all_jobs",
              doc: frm.doc,
              freeze: true,
              freeze_message: __("Clearing queue..."),
              callback: () => frm.reload_doc(),
            });
          },
        );
      },
      __("eTims Actions"),
    );
  },
});
