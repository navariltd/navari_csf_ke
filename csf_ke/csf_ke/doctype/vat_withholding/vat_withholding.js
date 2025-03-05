// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("VAT Withholding", {
	before_submit(frm) {
        if (frm.doc.vat_withholding_amount === frm.doc.outstanding_amount && !frm.doc.allocate_payment) {
            if (!frm.__confirmed_allocation) {
                frappe.confirm(
                    __("Would you like to allocate payment to the Journal Entry for this VAT Withholding?"),
                    () => {
                        frm.set_value("allocate_payment", 1);
                        frm.__confirmed_allocation = true;
                        frm.savesubmit();
                    },
                    () => {
                        frm.__confirmed_allocation = true;
                        frm.savesubmit();
                    }
                );
            }
            
            frappe.validated = false;
        }
	}
});
