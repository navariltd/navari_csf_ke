# Copyright (c) 2026, Navari Ltd and contributors
# For license information, please see license.txt
"""Kenya Sales Reconciliation doctype with embedded reconciliation logic.

This module contains both the doctype class and all whitelisted API endpoints
for running reconciliations and managing saved reconciliation records.
"""

import base64
import csv
import io
import json
import re
import zlib
from collections import defaultdict
from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document

from csf_ke.csf_ke.report.kenya_sales_tax_report.kenya_sales_tax_report import (
	KenyaSalesTaxReport,
)


class KenyaSalesReconciliation(Document):
	pass


# ---------------------------------------------------------------------------
# Whitelisted API endpoints
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_system_report_data(
	company: str,
	from_date: str,
	to_date: str,
	is_return: str | None = None,
	tax_template: str | None = None,
):
	"""Fetch the Kenya Sales Tax Report data for a given date range."""
	filters = {
		"company": company,
		"from_date": from_date,
		"to_date": to_date,
	}
	if is_return:
		filters["is_return"] = is_return
	if tax_template:
		filters["tax_template"] = tax_template

	report = KenyaSalesTaxReport(filters)
	_, data, _, _, _ = report.run()
	return data


@frappe.whitelist()
def parse_csv_file(file_urls: str | list[str]):
	"""Parse one or more uploaded CSV files and return normalized row dictionaries.

	Each row is normalized to a common structure with the SCU invoice number as
	the primary matching key and file metadata attached.

	Args:
	    file_urls: JSON-encoded list of file URLs (private files).

	Returns:
	    dict with ``rows`` (list of normalized dicts) and ``errors``.
	"""
	urls = frappe.parse_json(file_urls) if isinstance(file_urls, str) else file_urls
	if not urls:
		frappe.throw(_("No files provided"))

	all_rows = []
	errors = []

	for file_url in urls:
		file_doc = frappe.get_doc("File", {"file_url": file_url})
		if not file_doc:
			errors.append({"file": file_url, "error": _("File not found")})
			continue

		content = file_doc.get_content()
		if not content:
			errors.append({"file": file_doc.file_name, "error": _("File is empty")})
			continue

		try:
			rows = _parse_csv_content(content)
			for row in rows:
				row["file_url"] = file_url
				row["file_name"] = file_doc.file_name or file_url.split("/")[-1]
			all_rows.extend(rows)
		except Exception as e:
			errors.append({"file": file_doc.file_name, "error": str(e)})

	return {"rows": all_rows, "errors": errors}


@frappe.whitelist()
def reconcile(
	company: str,
	from_date: str,
	to_date: str,
	file_urls: str | list[str],
	is_return: str | None = None,
	tax_template: str | None = None,
	save_doc: bool | str | None = None,
	doc_name: str | None = None,
):
	"""Reconcile system sales tax report data against uploaded CSV data.

	Args:
	    company: Company name filter.
	    from_date: Report start date.
	    to_date: Report end date.
	    file_urls: JSON-encoded list of file URLs.
	    is_return: Optional "Is Return" / "Normal Sales Invoice" filter.
	    tax_template: Optional Item Tax Template filter.
	    save_doc: Whether to save the reconciliation as a doctype record.
	    doc_name: Optional existing doctype name to update.

	Returns:
	    dict with ``system_rows``, ``upload_rows``, ``only_in_system``,
	    ``only_in_upload``, ``matched``, ``file_errors`` and ``doc_name``.
	"""
	# Get system report rows
	system_rows = get_system_report_data(company, from_date, to_date, is_return, tax_template)
	system_rows = _normalize_system_rows(system_rows)

	# Get uploaded rows
	parsed = parse_csv_file(file_urls)
	upload_rows = parsed["rows"]
	file_errors = parsed["errors"]

	# Build lookup maps keyed by normalized SCU invoice number
	system_map = _build_index(system_rows)
	upload_map = _build_index(upload_rows)

	matched = []
	only_in_system = []
	only_in_upload = []

	matched_system_keys = set()
	matched_upload_keys = set()

	# Match by exact SCU invoice number first
	for scu_key, sys_rows in system_map.items():
		if scu_key in upload_map:
			up_rows = upload_map[scu_key]
			for sr in sys_rows:
				for ur in up_rows:
					matched.append(_merge_row(sr, ur, "matched"))
			matched_system_keys.add(scu_key)
			matched_upload_keys.add(scu_key)

	# System rows not found in upload
	for scu_key, sys_rows in system_map.items():
		if scu_key not in matched_system_keys:
			for sr in sys_rows:
				only_in_system.append(_mark_missing(sr, "system"))

	# Upload rows not found in system
	for scu_key, up_rows in upload_map.items():
		if scu_key not in matched_upload_keys:
			for ur in up_rows:
				only_in_upload.append(_mark_missing(ur, "upload"))

	result = {
		"system_rows": system_rows,
		"upload_rows": upload_rows,
		"matched": matched,
		"only_in_system": only_in_system,
		"only_in_upload": only_in_upload,
		"file_errors": file_errors,
	}

	if save_doc:
		doc_name = save_reconciliation_doc(
			company=company,
			from_date=from_date,
			to_date=to_date,
			is_return=is_return,
			tax_template=tax_template,
			file_urls=frappe.parse_json(file_urls) if isinstance(file_urls, str) else file_urls,
			result=result,
			doc_name=doc_name,
		)
		result["doc_name"] = doc_name

	return result


@frappe.whitelist()
def save_reconciliation_doc(
	company: str,
	from_date: str,
	to_date: str,
	file_urls: str | list[str],
	result: dict | str,
	is_return: str | None = None,
	tax_template: str | None = None,
	doc_name: str | None = None,
):
	"""Save/update a Kenya Sales Reconciliation doctype record.

	Args:
	    company: Company name.
	    from_date: Start date.
	    to_date: End date.
	    file_urls: JSON-encoded list of file URLs.
	    result: Dict containing the reconciliation results.
	    is_return: Optional is_return filter.
	    tax_template: Optional tax template filter.
	    doc_name: Optional existing doctype name to update.

	Returns:
	    The doctype name that was saved/updated.
	"""
	urls = frappe.parse_json(file_urls) if isinstance(file_urls, str) else file_urls
	if not urls:
		frappe.throw(_("File URLs are required"))

	doc = None
	if doc_name:
		doc = frappe.get_doc("Kenya Sales Reconciliation", doc_name)
		doc.flags.ignore_permissions = True
	else:
		doc = frappe.new_doc("Kenya Sales Reconciliation")
		doc.flags.ignore_permissions = True

	doc.company = company
	doc.from_date = from_date
	doc.to_date = to_date
	doc.is_return = is_return or ""
	doc.tax_template = tax_template or ""
	doc.results_json = _compress_json(result)
	doc.last_run = frappe.utils.now_datetime()

	# Update child table with file details
	doc.csv_files = []
	for url in urls:
		file_doc = frappe.get_doc("File", {"file_url": url})
		if file_doc:
			file_size_kb = round((file_doc.file_size or 0) / 1024) if file_doc.file_size else 0
			doc.append(
				"csv_files",
				{
					"file_url": url,
					"file_name": file_doc.file_name or url.split("/")[-1],
					"file_size": file_size_kb,
				},
			)

	doc.save(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def get_reconciliation_doc(doc_name: str):
	"""Fetch a saved Kenya Sales Reconciliation doctype record.

	Args:
	    doc_name: The doctype name.

	Returns:
	    Dict with filters, file URLs, results, and raw file error data.
	"""
	doc = frappe.get_doc("Kenya Sales Reconciliation", doc_name)
	results = {}
	try:
		results = _decompress_json(doc.results_json or "{}")
	except (ValueError, TypeError):
		results = {}

	file_urls = [row.file_url for row in (doc.csv_files or [])]

	return {
		"doc_name": doc.name,
		"company": doc.company,
		"from_date": str(doc.from_date) if doc.from_date else "",
		"to_date": str(doc.to_date) if doc.to_date else "",
		"is_return": doc.is_return or "",
		"tax_template": doc.tax_template or "",
		"last_run": str(doc.last_run) if doc.last_run else "",
		"file_urls": file_urls,
		"results": results,
	}


@frappe.whitelist()
def list_reconciliation_docs(limit=20):
	"""List recent Kenya Sales Reconciliation doctype records.

	Args:
	    limit: Maximum number of records to fetch.

	Returns:
	    List of dicts with key metadata for each record.
	"""
	docs = frappe.get_all(
		"Kenya Sales Reconciliation",
		fields=["name", "company", "from_date", "to_date", "last_run", "creation", "modified"],
		order_by="creation desc",
		limit=limit,
	)
	return docs


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compress_json(data):
	"""Compress a dict/JSON payload into a compact base64 string for storage."""
	if not data:
		return "{}"
	json_str = json.dumps(data, default=str)
	compressed = zlib.compress(json_str.encode("utf-8"))
	return "z:" + base64.b64encode(compressed).decode("ascii")


def _decompress_json(value):
	"""Decompress a stored zlib/base64 JSON string back into a Python dict."""
	if not value:
		return {}
	if value.startswith("z:"):
		try:
			raw = base64.b64decode(value[2:])
			decompressed = zlib.decompress(raw).decode("utf-8")
			return json.loads(decompressed)
		except Exception:
			# Fall back to plain JSON (legacy records stored un-compressed)
			return json.loads(value[2:])
	return json.loads(value)


def _normalize_system_rows(rows):
	"""Normalize Kenya Sales Tax Report output into common reconciliation structure."""
	normalized = []
	for row in rows or []:
		if row.get("is_group_header"):
			continue

		scu_number = row.get("etr_invoice_number") or ""
		scu_number = _clean_scu_number(scu_number)

		normalized.append(
			{
				"source": "system",
				"pin_of_purchaser": row.get("pin_of_purchaser", ""),
				"name_of_purchaser": row.get("name_of_purchaser", ""),
				"invoice_date": _normalize_date(row.get("cu_invoice_date") or row.get("invoice_date")),
				"invoice_name": row.get("invoice_name", ""),
				"etr_serial_number": row.get("etr_serial_number", ""),
				"etr_invoice_number": scu_number,
				"cu_link": row.get("cu_link", ""),
				"cu_invoice_date": _normalize_date(row.get("cu_invoice_date")),
				"taxable_value": row.get("taxable_value", 0),
				"amount_of_vat": row.get("amount_of_vat", 0),
				"return_cu_invoice_number": row.get("return_cu_invoice_number", ""),
				"return_cu_invoice_date": _normalize_date(row.get("return_cu_invoice_date")),
			}
		)
	return normalized


def _parse_csv_content(content):
	"""Parse raw CSV text, auto-detecting column positions from data rows."""
	decoded = _decode(content)
	reader = csv.reader(io.StringIO(decoded))
	raw_rows = [r for r in reader if any(cell.strip() for cell in r)]

	if not raw_rows:
		return []

	schema = _detect_schema(raw_rows[:20])
	if not schema:
		raise frappe.ValidationError(_("Could not identify CSV column layout from data rows."))

	rows = []
	for raw_row in raw_rows:
		row = _map_row(raw_row, schema)
		if row:
			rows.append(row)

	return rows


def _decode(content):
	"""Try decoding bytes content with a few common encodings."""
	if isinstance(content, bytes):
		for enc in ("utf-8-sig", "utf-8", "latin-1"):
			try:
				return content.decode(enc)
			except UnicodeDecodeError:
				continue
		return content.decode("utf-8", errors="replace")
	return content


def _detect_schema(sample_rows):
	r"""Detect which column index holds which logical field.

	Samples up to 20 data rows and aggregates column position evidence:
	  - PIN: ^[A-Z]\d{9}[A-Z]$
	  - Name: text that isn't a PIN / date / scu id / amount / keyword
	  - SCU ID: ^[A-Z]{2,5}\d{6,}$ (e.g. KRACU0300002994)
	  - SCU Invoice Number: contains '/' with SCU prefix (e.g. |KRACU0300002994/318229)
	  - Date: date-like pattern (e.g. 1/7/2026 or 13/07/2026)
	  - Amount: numeric (int/float, including negatives)

	Returns:
	    dict with column index assignments, or None if the SCU invoice
	    number column cannot be identified.
	"""
	pin_votes = {}
	name_votes = {}
	scu_id_votes = {}
	scu_inv_votes = {}
	date_votes = {}
	amount_votes = {}

	name_exclusions = {"local", "etims/tims sales", "etims/tims", ""}

	for row in sample_rows:
		for i, cell in enumerate(row):
			cell = cell.strip()

			# SCU Invoice Number pattern: may be primary SCU or return reference
			if re.search(r"[A-Z]{2,5}\d{6,}/\d+", cell.replace("|", "")):
				scu_inv_votes[i] = scu_inv_votes.get(i, 0) + 1
				continue

			# PIN: Kenya KRA PIN pattern (letter + 9 digits + letter)
			if re.match(r"^[A-Z]\d{9}[A-Z]$", cell):
				pin_votes[i] = pin_votes.get(i, 0) + 1
				continue

			# SCU ID: starts with KRACU or similar
			if re.match(r"^[A-Z]{2,5}\d{6,}$", cell):
				scu_id_votes[i] = scu_id_votes.get(i, 0) + 1
				continue

			# Date: d/m/yyyy or dd/mm/yyyy
			if re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}$", cell):
				date_votes[i] = date_votes.get(i, 0) + 1
				continue

			# Amount: numeric (including negatives and decimals)
			if re.match(r"^-?\d+([.,]\d+)?$", cell):
				amount_votes[i] = amount_votes.get(i, 0) + 1
				continue

			# Name: readable text that isn't a keyword or empty
			if (
				re.match(r"^[A-Za-z][A-Za-z0-9 .&'()\-]+$", cell)
				and len(cell) > 2
				and cell.lower() not in name_exclusions
			):
				name_votes[i] = name_votes.get(i, 0) + 1
				continue

	pin_idx = _best_vote(pin_votes)
	name_idx = _best_vote(name_votes)
	scu_id_idx = _best_vote(scu_id_votes)
	date_idx = _best_vote(date_votes)
	amount_idx = _best_vote(amount_votes)

	# Disambiguate SCU invoice vs return invoice columns.
	# Primary SCU invoice column appears in most rows; return invoices
	# appear only in return transactions, so they have fewer votes.
	if scu_inv_votes:
		scu_inv_idx = _best_vote(scu_inv_votes)
		remaining_inv_votes = {k: v for k, v in scu_inv_votes.items() if k != scu_inv_idx}
		return_idx = _best_vote(remaining_inv_votes)
	else:
		scu_inv_idx = None
		return_idx = None

	# Return date: second most-voted date column (exclude the primary date column)
	if date_idx is not None:
		second_date_votes = {k: v for k, v in date_votes.items() if k != date_idx}
		return_date_idx = _best_vote(second_date_votes)
	else:
		return_date_idx = None

	schema = {
		"pin_idx": pin_idx,
		"name_idx": name_idx,
		"scu_id_idx": scu_id_idx,
		"scu_inv_idx": scu_inv_idx,
		"date_idx": date_idx,
		"amount_idx": amount_idx,
		"return_idx": return_idx,
		"return_date_idx": return_date_idx,
	}
	# Require at least the SCU invoice number to identify data
	if scu_inv_idx is None:
		return None
	return schema


def _best_vote(votes):
	"""Return the column index with the highest vote count, or None."""
	if not votes:
		return None
	return max(votes.items(), key=lambda kv: (kv[1], -kv[0]))[0]


def _map_row(raw_row, schema):
	"""Map a CSV row to a normalized dict using the detected schema."""

	def _cell(idx):
		if idx is None or idx >= len(raw_row):
			return ""
		return raw_row[idx].strip()

	scu_number = _clean_scu_number(_cell(schema["scu_inv_idx"]))
	if not scu_number:
		return None

	return_scu_number = (
		_clean_scu_number(_cell(schema.get("return_idx"))) if schema.get("return_idx") is not None else ""
	)

	amount_str = _cell(schema.get("amount_idx"))
	amount = _parse_amount(amount_str)

	return {
		"source": "upload",
		"pin_of_purchaser": _cell(schema.get("pin_idx")),
		"name_of_purchaser": _cell(schema.get("name_idx")),
		"invoice_date": _normalize_date(_cell(schema.get("date_idx"))),
		"etr_serial_number": _cell(schema.get("scu_id_idx")),
		"etr_invoice_number": scu_number,
		"cu_link": "",
		"cu_invoice_date": _normalize_date(_cell(schema.get("date_idx"))),
		"taxable_value": amount,
		"amount_of_vat": 0,
		"return_cu_invoice_number": return_scu_number,
		"return_cu_invoice_date": _normalize_date(_cell(schema.get("return_date_idx")))
		if schema.get("return_date_idx") is not None
		else "",
	}


def _build_index(rows):
	"""Build a dict keyed by normalized SCU invoice number, with list values."""
	index = defaultdict(list)
	for row in rows:
		key = row.get("etr_invoice_number", "")
		if key:
			index[key].append(row)
	return index


def _merge_row(system_row, upload_row, status):
	"""Merge a matched system + upload row into a display row."""
	merged = dict(system_row)
	merged.update(
		{
			"status": status,
			"upload_pin": upload_row.get("pin_of_purchaser", ""),
			"upload_name": upload_row.get("name_of_purchaser", ""),
			"upload_date": upload_row.get("cu_invoice_date", ""),
			"upload_amount": upload_row.get("taxable_value", 0),
			"system_pin": system_row.get("pin_of_purchaser", ""),
			"system_name": system_row.get("name_of_purchaser", ""),
			"system_date": system_row.get("cu_invoice_date", ""),
			"system_amount": system_row.get("taxable_value", 0),
		}
	)
	return merged


def _mark_missing(row, source):
	"""Mark a row as missing from the opposite side."""
	row = dict(row)
	row["status"] = f"only_in_{source}"
	return row


def _clean_scu_number(value):
	"""Normalize SCU invoice number by removing leading '|' and whitespace."""
	if not value:
		return ""
	value = str(value).strip()
	if value.startswith("|"):
		value = value[1:]
	return value.strip()


def _normalize_date(value):
	"""Convert various date representations to a display string (YYYY-MM-DD)."""
	if not value:
		return ""
	if isinstance(value, datetime):
		return value.strftime("%Y-%m-%d")
	if hasattr(value, "strftime"):
		return value.strftime("%Y-%m-%d")
	if isinstance(value, str):
		value = value.strip()
		if not value:
			return ""
		for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
			try:
				return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
			except ValueError:
				continue
	return str(value)


def _parse_amount(value):
	"""Parse an amount string that may include commas / currency symbols."""
	if not value:
		return 0.0
	value = str(value).strip().replace(",", "")
	try:
		return float(value)
	except ValueError:
		return 0.0
