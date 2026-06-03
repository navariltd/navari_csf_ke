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
        frappe.confirm(__("Delete ALL eTims Job Queue records?"), () => {
          frappe.call({
            method: "frappe.client.get_list",
            args: {
              doctype: "eTims Job Queue",
              fields: ["name"],
              limit_page_length: 0,
            },
            callback: (r) => {
              const jobs = r.message || [];

              Promise.all(
                jobs.map((j) =>
                  frappe.call({
                    method: "frappe.client.delete",
                    args: {
                      doctype: "eTims Job Queue",
                      name: j.name,
                    },
                  }),
                ),
              ).then(() => frm.reload_doc());
            },
          });
        });
      },
      __("eTims Actions"),
    );
  },
});
