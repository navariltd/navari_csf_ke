// Copyright (c) 2023, Navari Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("B2C Payment", {
  refresh: function (frm) {
    frm.add_custom_button("Initiate Payment", async function () {
      frappe.call({
        method:
          "csf_ke.csf_ke.doctype.b2c_payment.b2c_payment.initiate_payment",
        callback: function (response) {
          // console.log(response);
        },
      });
    });
    frm.set_value("originatorconversationid", generateUUIDv4());
  },
});

function generateUUIDv4() {
  let uuid = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(
    /[xy]/g,
    function (c) {
      let r = (Math.random() * 16) | 0,
        v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    }
  );
  return uuid;
}
