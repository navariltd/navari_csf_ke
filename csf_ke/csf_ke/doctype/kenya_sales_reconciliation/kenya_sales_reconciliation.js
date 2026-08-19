// Copyright (c) 2026, Navari Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Kenya Sales Reconciliation", {
  refresh(frm) {
    frm.add_web_link(
      `/desk/kenya-sales-tax-reco?company=${encodeURIComponent(frm.doc.company)}&from_date=${encodeURIComponent(frm.doc.from_date)}&to_date=${encodeURIComponent(frm.doc.to_date)}&doc_name=${encodeURIComponent(frm.doc.name)}`,
      "View Reconciliation Report",
    );
  },
});
