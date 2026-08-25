# Copyright (c) 2026, Navari Limited and contributors
# For license information, please see license.txt
"""Page backend that delegates all reconciliation logic to the doctype module."""

# All reconciliation logic lives in:
#   csf_ke.csf_ke.doctype.kenya_sales_reconciliation.kenya_sales_reconciliation
#
# This page module provides re-exported aliases so existing whitelisted API
# method paths remain backwards compatible, and imports the doctype module so
# the scripts are loaded when the page is used.

from csf_ke.csf_ke.doctype.kenya_sales_reconciliation.kenya_sales_reconciliation import (
	get_reconciliation_doc,
	get_system_report_data,
	list_reconciliation_docs,
	parse_csv_file,
	reconcile,
	save_reconciliation_doc,
)

__all__ = [
	"get_reconciliation_doc",
	"get_system_report_data",
	"list_reconciliation_docs",
	"parse_csv_file",
	"reconcile",
	"save_reconciliation_doc",
]
