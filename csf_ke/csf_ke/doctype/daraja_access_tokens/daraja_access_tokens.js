// Copyright (c) 2023, Navari Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Daraja Access Tokens", {
  validate: function (frm) {
    if (frm.doc.expiry_time && frm.doc.token_fetch_time) {
      expiryTime = new Date(frm.doc.expiry_time);
      fetchTime = new Date(frm.doc.token_fetch_time);

      if (expiryTime <= fetchTime) {
        frappe.msgprint({
          message: __(
            "Token Expiry Time cannot be earlier than or the same as Token Fetch Time"
          ),
          indicator: "red",
          title: "Validation Error",
        });
        frappe.validated = false;
      }
    }
  },
});
