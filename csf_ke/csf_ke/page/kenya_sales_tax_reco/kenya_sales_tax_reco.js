frappe.pages["kenya-sales-tax-reco"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Kenya Sales Tax Reconciliation"),
		single_column: true,
	});
};

frappe.pages["kenya-sales-tax-reco"].on_page_show = function (wrapper) {
	load_desk_page(wrapper);
};

function load_desk_page(wrapper) {
	let $parent = $(wrapper).find(".layout-main-section");
	$parent.empty();

	frappe.require("kenya_sales_tax_reco.bundle.jsx").then(() => {
		frappe.kenya_sales_tax_reco = new frappe.ui.KenyaSalesTaxReco({
			wrapper: $parent,
			page: wrapper.page,
			route_options: frappe.route_options || {},
		});
	});
}

frappe.require("/assets/csf_ke/css/kenya_sales_tax_reco.css");
