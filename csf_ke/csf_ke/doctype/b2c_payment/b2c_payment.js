// Copyright (c) 2023, Navari Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("B2C Payment", {
  validate: function (frm) {
    if (frm.doc.partyb) {
      if (!validatePhoneNumber(frm.doc.partyb)) {
        // Validate if the receiver's mobile number is valid
        frappe.msgprint("The Receiver (mobile number) entered is incorrect.");
        frappe.validated = false;
      }
    }

    if (frm.doc.amount < 10) {
      frappe.msgprint(
        "Amount entered is less than the least acceptable amount of Kshs. 1"
      );
      frappe.validated = false;
    }
  },
  refresh: function (frm) {
    if (!frm.doc.__islocal) {
      frm.add_custom_button("Initiate Payment", async function () {
        frappe.call({
          method:
            "csf_ke.csf_ke.doctype.b2c_payment.b2c_payment.initiate_payment",
          args: {
            // Create request with a partial payload
            partial_payload: {
              OriginatorConversationID: frm.doc.originatorconversationid,
              CommandID: frm.doc.commandid,
              Amount: frm.doc.amount,
              PartyB: frm.doc.partyb,
              Remarks: frm.doc.remarks,
              Occassion: frm.doc.occassion,
            },
          },
          callback: function (response) {
            frappe.msgprint(response);
          },
        });
      });
    }

    if (!frm.doc.originatorconversationid) {
      frm.set_value("originatorconversationid", generateUUIDv4());
    }
  },
});

function generateUUIDv4() {
  // Generates a uuid4 string conforming to RFC standards
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

function validatePhoneNumber(input) {
  // Validates the receiver phone numbers
  if (input.startsWith("2547")) {
    const pattern = /^2547\d{8}$/;
    return pattern.test(input);
  } else {
    const pattern = /^(25410|25411)\d{7}$/;
    return pattern.test(input);
  }
}
