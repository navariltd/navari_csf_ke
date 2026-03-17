frappe.provide("csf_ke.deposit_utils");

csf_ke.deposit_utils.get_deposits = function(frm, is_button_clicked = true) {
    frappe.call({
        method: "csf_ke.custom.deposit_utils.get_deposits",
        args: { doc: frm.doc },
        callback: function(r) {
            // Clear existing deductions
            frm.clear_table("deposits");
            if (r.message.length > 0) {
                let deductions = r.message;
                let allocated_amount = 0;

                // Add new deductions
                deductions.forEach(function(d) {
                    let c = frm.add_child("deposits");
                    c.reference_name = d.reference_name;
                    c.reference_row = d.reference_row;
                    c.remarks = d.remarks;
                    c.deposit_amount = d.deposit_amount;
                    c.allocated_amount = d.allocated_amount;

                    // Keep track of the total allocated amount
                    allocated_amount += d.allocated_amount;
                });

                // Show alert only if not triggered by button click
                if (!is_button_clicked) {
                    let formatted_amount = new Intl.NumberFormat().format(allocated_amount);
                    frappe.show_alert({
                        message: __(
                            "Deposit amount <b>{0}</b> will be allocated when you save this invoice.",
                            [formatted_amount]
                        ),
                        indicator: "green"
                    }, 10);
                }
            }

            // Refresh the child table
            frm.refresh_field("deposits");
            frm.dirty();
        }
    });
};

csf_ke.deposit_utils.add_create_deposit_button = function(frm) {
    // Add a custom button "Create Deposit Invoice"
    if (!frm.is_new() && frm.doc.docstatus === 1 && !frm.doc.deposit_invoice) {
        frm.add_custom_button(__("Create Deposit Invoice"), function() {
            // Open a dialog to ask for % deposit and amount deposit
            let is_updating = false; // Flag to prevent infinite loops

            const dialog = new frappe.ui.Dialog({
                title: __("Create Deposit Invoice"),
                fields: [
                    {
                        label: __("Deposit Percentage"),
                        fieldname: "deposit_percentage",
                        fieldtype: "Percent",
                        reqd: 1,
                        default: frm.doc.percent_deposit
                    },
                    {
                        label: __("Deposit Amount"),
                        fieldname: "deposit_amount",
                        fieldtype: "Currency",
                        reqd: 1,
                        default: (frm.doc.total || 0) * frm.doc.percent_deposit / 100
                    }
                ],
                primary_action_label: __("Create"),
                primary_action: function(values) {
                    if (!values.deposit_amount) {
                        frappe.msgprint({
                            title: __("Warning"),
                            indicator: "orange",
                            message: __("Deposit Percentage/Amount are required")
                        });
                        return;
                    }
                    // Use frappe.model.open_mapped_doc to create the Purchase Invoice
                    frappe.model.open_mapped_doc({
                        method: "csf_ke.custom.deposit_utils.create_deposit_invoice",
                        frm: frm,
                        args: {
                            doctype: frm.doc.doctype,
                            deposit_amount: values.deposit_amount,
                        }
                    });
                    dialog.hide();
                }
            });

            // Add event listeners to update fields dynamically
            dialog.fields_dict.deposit_percentage.$input.on("input", function() {
                if (is_updating) return;
                is_updating = true;

                const percent = parseFloat(dialog.get_value("deposit_percentage") || 0);
                const total = frm.doc.total || 0;

                if (percent > 100) {
                    frappe.msgprint({
                        title: __("Warning"),
                        indicator: "orange",
                        message: __("Deposit Percentage cannot exceed 100%.")
                    });
                    dialog.set_value("deposit_percentage", 100);
                }

                const amount = (total * percent) / 100;
                dialog.set_value("deposit_amount", amount);
                is_updating = false;
            });

            dialog.fields_dict.deposit_amount.$input.on("input", function() {
                if (is_updating) return;
                is_updating = true;

                const amount = parseFloat(dialog.get_value("deposit_amount") || 0);
                const total = frm.doc.total || 0;
                const percent = total > 0 ? (amount / total) * 100 : 0;

                if (percent > 100) {
                    frappe.msgprint({
                        title: __("Warning"),
                        indicator: "orange",
                        message: __("Deposit Percentage cannot exceed 100%.")
                    });
                    dialog.set_value("deposit_percentage", 100);
                    dialog.set_value("deposit_amount", total);
                } else {
                    dialog.set_value("deposit_percentage", percent);
                }

                is_updating = false;
            });

            dialog.show();
        }).addClass(frm.doc.has_deposit ? "btn-primary" : "btn-secondary");;
    }
};


csf_ke.deposit_utils.get_deposit_item = function(frm) {
    // For deposit invoice, add 1 line itema as Deposit Item
    if (frm.doc.is_deposit_invoice) {
        frm.doc.items = [];
        frappe.call({
            method: "csf_ke.custom.item.get_deposit_item",
            args: {
                company: frm.doc.company
            },
            callback: function(r) {
                if (r.message) {
                    cost_center = frm.doc.doctype == "Sales Invoice" ? r.message.selling_cost_center : r.message.buying_cost_center;
                    frm.set_value("cost_center", cost_center);
                    frm.add_child("items", {
                        item_code: r.message.item_code,
                        item_name: r.message.item_name,
                        uom: r.message.uom,
                        qty: 1,
                        is_deposit_item: 1,
                        income_account: r.message.sales_deposit_account,
                        expense_account: r.message.purchase_deposit_account,
                    });
                    frm.refresh_field("items");
                } else {
                    frappe.msgprint(__("No deposit items found!"));
                }
            }
        });
    } else {
        // Optional: Remove the deposit item if unchecked
        frm.doc.items = frm.doc.items.filter(item => item.is_deposit_item !== 1);
        frm.refresh_field("items");
    }
};