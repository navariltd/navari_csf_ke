frappe.ui.form.on("Company", {
	refresh(frm) {
		toggle_withholding_fields(frm, "tax");
		toggle_withholding_fields(frm, "vat");
	},

	withholding_tax_party_wise(frm) {
		enforce_withholding_mode(frm, "tax", "party_wise");
		toggle_withholding_fields(frm, "tax");
	},

	withholding_tax_no_party(frm) {
		enforce_withholding_mode(frm, "tax", "no_party");
		toggle_withholding_fields(frm, "tax");
	},

	withholding_vat_party_wise(frm) {
		enforce_withholding_mode(frm, "vat", "party_wise");
		toggle_withholding_fields(frm, "vat");
	},

	withholding_vat_no_party(frm) {
		enforce_withholding_mode(frm, "vat", "no_party");
		toggle_withholding_fields(frm, "vat");
	},

	validate(frm) {
		validate_withholding_mode(frm, "tax");
		validate_withholding_mode(frm, "vat");
	},
});

function enforce_withholding_mode(frm, kind, selected_mode) {
	const selected_fieldname = `withholding_${kind}_${selected_mode}`;
	const other_mode = selected_mode === "party_wise" ? "no_party" : "party_wise";
	const other_fieldname = `withholding_${kind}_${other_mode}`;

	if (frm.doc[selected_fieldname]) {
		frm.set_value(other_fieldname, 0);
	}
}

function toggle_withholding_fields(frm, kind) {
	const party_wise = Boolean(frm.doc[`withholding_${kind}_party_wise`]);
	const no_party = Boolean(frm.doc[`withholding_${kind}_no_party`]);

	[
		`withholding_${kind}_party_accounts_section`,
		`withholding_${kind}_party_wise_payable_account`,
		`withholding_${kind}_party_wise_receivable_account`,
	].forEach((fieldname) => {
		frm.toggle_display(fieldname, party_wise);
	});

	[
		`withholding_${kind}_no_party_section`,
		`withholding_${kind}_no_party_payable_account`,
		`withholding_${kind}_no_party_receivable_account`,
	].forEach((fieldname) => {
		frm.toggle_display(fieldname, no_party);
	});
}

function validate_withholding_mode(frm, kind) {
	const has_account = Boolean(
		frm.doc[`withholding_${kind}_party_wise_payable_account`] ||
		frm.doc[`withholding_${kind}_no_party_payable_account`] ||
		frm.doc[`withholding_${kind}_party_wise_receivable_account`] ||
		frm.doc[`withholding_${kind}_no_party_receivable_account`]
	);

	const party_wise = Boolean(frm.doc[`withholding_${kind}_party_wise`]);
	const no_party = Boolean(frm.doc[`withholding_${kind}_no_party`]);

	if (!has_account) {
		return;
	}

	if ((party_wise && no_party) || (!party_wise && !no_party)) {
		frappe.throw(
			__("Please choose exactly one option for Withholding {0}: Party Wise or No Party.", [
				kind.toUpperCase(),
			])
		);
	}
}
