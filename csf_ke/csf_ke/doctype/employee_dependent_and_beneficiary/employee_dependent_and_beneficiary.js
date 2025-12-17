// Copyright (c) 2024, Navari Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Dependent and Beneficiary", {
  refresh: function (frm) {
    calculate_and_set_age(frm);
  },
  dob: function (frm) {
    calculate_and_set_age(frm);
  },
  employee: function (frm) {
    fetch_and_set_employee_name(frm);
  },
  first_name: function (frm) {
    update_full_name(frm);
  },
  middle_name: function (frm) {
    update_full_name(frm);
  },
  last_name: function (frm) {
    update_full_name(frm);
  },
});

function calculate_and_set_age(frm) {
  if (frm.doc.dob) {
    const dob = frappe.datetime.str_to_obj(frm.doc.dob);
    const today = new Date();
    let age = today.getFullYear() - dob.getFullYear();

    const hasBirthdayPassed =
      today.getMonth() > dob.getMonth() ||
      (today.getMonth() === dob.getMonth() && today.getDate() >= dob.getDate());

    if (!hasBirthdayPassed) {
      age -= 1;
    }
    frm.set_value("age", age);
  } else {
    frm.set_value("age", null);
  }
}

function fetch_and_set_employee_name(frm) {
  if (frm.doc.employee) {
    frappe.db.get_value("Employee", frm.doc.employee, "employee_name", (r) => {
      if (r && r.employee_name) {
        frm.set_value("employee_name", r.employee_name);
      } else {
        frm.set_value("employee_name", null);
      }
    });
  } else {
    frm.set_value("employee_name", null);
  }
}

function update_full_name(frm) {
  if (frm.doc.first_name || frm.doc.middle_name || frm.doc.last_name) {
    frm.set_value(
      "full_name",
      `${frm.doc.first_name || ""} ${frm.doc.middle_name || ""} ${
        frm.doc.last_name || ""
      }`.trim(),
    );
  } else {
    frm.set_value("full_name", "");
  }
}
