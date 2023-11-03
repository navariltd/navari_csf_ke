// Copyright (c) 2023, Navari Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("MPesa B2C Settings", {
  validate: function (frm) {
    if (
      frm.doc.results_url &&
      frm.doc.queue_timeout_url &&
      frm.doc.authorization_url &&
      frm.doc.payment_url
    ) {
      let message = "";
      if (
        validateURL(frm.doc.results_url) &&
        validateURL(frm.doc.queue_timeout_url) &&
        validateURL(frm.doc.authorization_url) &&
        validateURL(frm.doc.payment_url)
      ) {
        message = `The Results URL: ${frm.doc.results_url} and Queue TimeOut URL: ${frm.doc.queue_timeout_url} will be used to handle responses from Safaricom.`;
        frappe.msgprint(message);
      } else {
        message = "The URLs Registered are not valid. Please review them";
        frappe.msgprint(message);
        frappe.validated = false;
      }
    }
  },
});

function validateURL(url) {
  // validates the input parameter to a valid URL.
  // url: string, returnType: boolean
  const pattern = new RegExp(
    "^((https?|ftp|file):\\/\\/)?" +
      "((([a-zA-Z\\d]([a-zA-Z\\d-]*[a-zA-Z\\d])*)\\.)+[a-zA-Z]{2,}|" +
      "((\\d{1,3}\\.){3}\\d{1,3}))" +
      "(\\:\\d+)?(\\/[-a-zA-Z\\d%_.~+]*)*" +
      "(\\?[;&a-z\\d%_.~+=-]*)?" +
      "(\\#[-a-z\\d_]*)?$",
    "i"
  );
  return pattern.test(url);
}
