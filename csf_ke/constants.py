DEPOSIT_CUSTOM_FIELDS =  {
    "Item": [
		{
			"depends_on": "eval:!doc.is_stock_item",
			"fieldname": "is_deposit_item",
			"fieldtype": "Check",
			"insert_after": "is_stock_item",
			"label": "Is Deposit Item"
		},
	],
    "Sales Order": [
		{
			"fieldname": "section_break_o8q38",
			"fieldtype": "Section Break",
			"insert_after": "payment_schedule",
            "label": "Deposit",
		}, 
		{
			"description": "If checked, the 1st invoice from this order should be a deposit invoice.",
			"fieldname": "has_deposit",
			"fieldtype": "Check",
			"insert_after": "section_break_o8q38",
			"label": "Deposit on 1st Invoice",
			"allow_on_submit": 1
		},
		{
			"fieldname": "deposit_invoice",
			"fieldtype": "Data",
			"insert_after": "has_deposit",
			"label": "Deposit Invoice",
			"no_copy": 1,
			"read_only": 1
		},
		{
			"fieldname": "column_break_euapx",
			"fieldtype": "Column Break",
			"insert_after": "deposit_invoice"
		},
		{
			"fieldname": "percent_deposit",
			"fieldtype": "Percent",
			"insert_after": "column_break_euapx",
			"label": "Percent Deposit",
		},
		{
			"fieldname": "deposit_deduction_method",
			"fieldtype": "Select",
			"label": "Deposit Deduction Method",
			"options": "Percent\nFull Amount",
			"description": "Deposit deduction (return of deposit) on following invoice(s).",
			"insert_after": "percent_deposit",
		}
	],
    "Purchase Order": [
		{
			"fieldname": "section_break_o8q38",
			"fieldtype": "Section Break",
			"insert_after": "payment_schedule",
            "label": "Deposit",
		}, 
		{
			"description": "If checked, the 1st invoice from this order should be a deposit invoice.",
			"fieldname": "has_deposit",
			"fieldtype": "Check",
			"insert_after": "section_break_o8q38",
			"label": "Deposit on 1st Invoice",
			"allow_on_submit": 1
		},
		{
			"fieldname": "deposit_invoice",
			"fieldtype": "Data",
			"insert_after": "has_deposit",
			"label": "Deposit Invoice",
			"no_copy": 1,
			"read_only": 1
		},
		{
			"fieldname": "column_break_euapx",
			"fieldtype": "Column Break",
			"insert_after": "deposit_invoice"
		},
		{
			"fieldname": "percent_deposit",
			"fieldtype": "Percent",
			"insert_after": "column_break_euapx",
			"label": "Percent Deposit",
		},
		{
			"fieldname": "deposit_deduction_method",
			"fieldtype": "Select",
			"label": "Deposit Deduction Method",
			"options": "Percent\nFull Amount",
			"description": "Deposit deduction (return of deposit) on following invoice(s).",
			"insert_after": "percent_deposit",
		}
	],
    "Sales Invoice": [
		{
			"depends_on": "",
			"fieldname": "is_deposit_invoice",
			"fieldtype": "Check",
			"insert_after": "company_tax_id",
			"label": "Is Deposit Invoice",
			"read_only": 0
		},
		{
			"collapsible": 1,
			"collapsible_depends_on": "deposits",
			"depends_on": "eval:!doc.is_deposit_invoice",
			"fieldname": "deposit_deductions",
			"fieldtype": "Section Break",
			"insert_after": "advances",
			"label": "Deposit Deductions"
		},
		{
			"fieldname": "use_untied_deposit",
			"fieldtype": "Check",
			"insert_after": "deposit_deductions",
			"label": "Include Untied Deposits",
			"description": "Untied Deposits are deposits that are not linked to any order.",
		},
		{
			"fieldname": "manual_deposit_allocation",
			"fieldtype": "Check",
			"insert_after": "use_untied_deposit",
			"label": "Manual Deposit Allocation",
			"read_only": 0,
			"description": "Allow user to manually allowcate deposit amount to deduct.",
		},
		{
			"fieldname": "deposits",
			"fieldtype": "Table",
			"insert_after": "manual_deposit_allocation",
			"label": "Deposits",
			"options": "Sales Invoice Deposit",
			"read_only_depends_on": "eval:!doc.manual_deposit_allocation",
		}
	],
    "Sales Invoice Item": [
		{
			"fetch_from": "item_code.is_deposit_item",
			"fieldname": "is_deposit_item",
			"fieldtype": "Check",
			"insert_after": "item_code",
			"label": "Is Deposit Item",
			"read_only": 1
		},
	],
    "Purchase Invoice": [
		{
			"depends_on": "",
			"fieldname": "is_deposit_invoice",
			"fieldtype": "Check",
			"insert_after": "company",
			"label": "Is Deposit Invoice",
			"read_only": 0
		},
		{
			"collapsible": 1,
			"collapsible_depends_on": "deposits",
			"depends_on": "eval:!doc.is_deposit_invoice",
			"fieldname": "deposit_deductions",
			"fieldtype": "Section Break",
			"insert_after": "advance_tax",
			"label": "Deposit Deductions"
		},
		{
			"fieldname": "use_untied_deposit",
			"fieldtype": "Check",
			"insert_after": "deposit_deductions",
			"label": "Include Untied Deposits",
			"description": "Untied Deposits are deposits that are not linked to any order.",
		},
		{
			"fieldname": "manual_deposit_allocation",
			"fieldtype": "Check",
			"insert_after": "use_untied_deposit",
			"label": "Manual Deposit Allocation",
			"read_only": 0,
			"description": "Allow user to manually allowcate deposit amount to deduct.",
		},
		{
			"fieldname": "deposits",
			"fieldtype": "Table",
			"insert_after": "manual_deposit_allocation",
			"label": "Deposits",
			"options": "Purchase Invoice Deposit",
			"read_only_depends_on": "eval:!doc.manual_deposit_allocation",
		}
	],
    "Purchase Invoice Item": [
		{
			"fetch_from": "item_code.is_deposit_item",
			"fieldname": "is_deposit_item",
			"fieldtype": "Check",
			"insert_after": "item_code",
			"label": "Is Deposit Item",
			"read_only": 1
		},
	],
    "Item Default": [
		{
			"depends_on": "eval:parent.is_deposit_item",
			"fieldname": "purchase_deposit_account",
			"fieldtype": "Link",
			"insert_after": "column_break_r6eft",
			"label": "Purchase Deposit Account",
			"link_filters": "[[\"Account\",\"root_type\",\"=\",\"Asset\"]]",
			"options": "Account"
		},
		{
			"depends_on": "eval:parent.is_deposit_item",
			"fieldname": "sales_deposit_account",
			"fieldtype": "Link",
			"insert_after": "deposit_defaults",
			"label": "Sales Deposit Account",
			"link_filters": "[[\"Account\",\"root_type\",\"=\",\"Liability\"]]",
			"options": "Account"
		},
		{
			"fieldname": "deposit_defaults",
			"fieldtype": "Section Break",
			"insert_after": "deferred_revenue_account",
			"label": "Deposit Defaults"
		},
		{
			"fieldname": "column_break_deposit_account",
			"fieldtype": "Column Break",
			"insert_after": "sales_deposit_account"
		},
	],
}