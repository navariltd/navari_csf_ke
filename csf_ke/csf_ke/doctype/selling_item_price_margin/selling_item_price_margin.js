// Copyright (c) 2024, Navari Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Selling Item Price Margin", {
  refresh(frm) {},

  before_save(frm) {
    adjust_margin_field_type(frm);
  },

  before_submit(frm) {
    adjust_margin_field_type(frm);
  },
  update_existing_price_list: function (frm) {
    if (frm.doc.update_existing_price_list) {
      frm.set_value("new_selling_price_list", 0);
    } else {
      frm.set_value("new_selling_price_list", 1);
    }
  },
  new_selling_price_list: function (frm) {
    if (frm.doc.new_selling_price_list) {
      frm.set_value("update_existing_price_list", 0);
    } else {
      frm.set_value("update_existing_price_list", 1);
    }
  },
  margin_type: function (frm) {
    adjust_margin_field_type(frm);
  },

  onload: function (frm) {
    frm.set_query("selling_price", function () {
      return {
        filters: {
          selling: 1,
          currency: frm.doc.currency,
        },
      };
    });
    frm.set_query("buying_price", function () {
      return {
        filters: {
          buying: 1,
          currency: frm.doc.currency,
        },
      };
    });
  },
});

function adjust_margin_field_type(frm) {
  if (frm.doc.margin_type === "Amount") {
    frm.set_df_property("margin_percentage_or_amount", "fieldtype", "Currency");
  } else if (frm.doc.margin_type === "Percentage") {
    frm.set_df_property("margin_percentage_or_amount", "fieldtype", "Percent");
  }
  frm.refresh_field("margin_percentage_or_amount");
}
