import * as React from "react";
import { App } from "./App";
import { createRoot } from "react-dom/client";


class KenyaSalesTaxReco {
	constructor({ page, wrapper }) {
		this.$wrapper = $(wrapper);
		this.page = page;

		this.init();
	}

	init() {
		this.setup_app();
	}

	setup_app() {
		// create and mount the react app
		const root = createRoot(this.$wrapper.get(0));
		root.render(<App />);
		this.$kenya_sales_tax_reco = root;
	}
}

frappe.provide("frappe.ui");
frappe.ui.KenyaSalesTaxReco = KenyaSalesTaxReco;
export default KenyaSalesTaxReco;