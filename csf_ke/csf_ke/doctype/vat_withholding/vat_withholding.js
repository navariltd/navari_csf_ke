// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("VAT Withholding", {
    before_submit(frm) {

        if (frm.doc.vat_withholding_amount === frm.doc.outstanding_amount && !frm.doc.allocate_payment) {
            
            return new Promise((resolve) => {
                frappe.confirm(
                    __("The Withholding Amount ({0}) equals the Outstanding Amount ({1}). Would you like to allocate payment to the Journal Entry for Sales Invoice {2}?", 
                        [frm.doc.vat_withholding_amount, frm.doc.outstanding_amount, frm.doc.voucher_no]),
                    () => {

                        frm.set_value("allocate_payment", 1);
                        frm.save('Submit');
                        frm.refresh();
                        
                    },
                    () => {
                        frm.save('Submit');
                        frm.refresh();
                    }
                );
            });
        }
    }
});