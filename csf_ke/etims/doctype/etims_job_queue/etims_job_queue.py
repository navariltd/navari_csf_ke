from __future__ import annotations

import json
from collections.abc import Callable
from datetime import timedelta

import frappe
import frappe.defaults
from frappe.model.document import Document
from frappe.utils import now_datetime

from ...utils import (
	clean_url_params,
)


class eTimsJobQueue(Document):
	#: Fallback duplicate-detection window in seconds when the Queue Manager
	#: has not configured ``duplicate_detection_window`` (defaults to 5 min).
	DEFAULT_DUPLICATE_WINDOW_SECONDS = 300

	def validate(self) -> None:
		if self.url:
			self.url = clean_url_params(self.url)

	def before_insert(self) -> None:
		self._reject_duplicate()

	def _get_duplicate_window_seconds(self) -> int:
		"""
		Return the duplicate-detection window in seconds.

		Reads the ``duplicate_detection_window`` (Duration field, stored in
		seconds) from the ``eTims Queue Manager`` singleton.  Falls back to
		:attr:`DEFAULT_DUPLICATE_WINDOW_SECONDS` when the field is not set.

		Returns:
		    Window duration in seconds.
		"""
		queue_manager = frappe.get_single("eTims Queue Manager")
		window = queue_manager.get("duplicate_detection_window")
		return int(window) if window else self.DEFAULT_DUPLICATE_WINDOW_SECONDS

	def _reject_duplicate(self) -> None:
		"""
		Block insertion if an identical job already exists in the queue.

		A job is considered a duplicate when all of the following fields match
		an existing record created within the
		duplicate-detection window (configured on the ``eTims Queue Manager``,
		defaulting to 5 minutes):

		    * ``request_method``
		    * ``route_key``
		    * ``handler_function``
		    * ``company``
		    * ``settings_name``
		    * ``request_data``
		    * ``page``

		``request_data`` is compared semantically (JSON decoded) so that
		key ordering or whitespace differences in the serialised payload do
		not produce false negatives.
		"""
		window_seconds = self._get_duplicate_window_seconds()
		cutoff = now_datetime() - timedelta(seconds=window_seconds)

		filters = {}
		for field in (
			"request_method",
			"route_key",
			"handler_function",
			"company",
			"settings_name",
			"page",
		):
			value = self.get(field)
			if value is not None:
				filters[field] = value

		filters["creation"] = (">", cutoff)

		current_data = self._normalize_json(self.request_data)

		similar_jobs = frappe.get_all(
			"eTims Job Queue",
			filters=filters,
			fields=["name", "request_data"],
		)

		for job in similar_jobs:
			if self._normalize_json(job.request_data) == current_data:
				similar_job_name = job.name
				message = (
					frappe._("Duplicate eTims Job blocked within a {0} second window.\n").format(
						window_seconds
					)
					+ frappe._("Similar existing job: {0}").format(similar_job_name)
					+ f"\n\n{frappe._('New job data')}:\n"
					+ json.dumps(self.as_dict(), indent=2, default=str)
				)
				frappe.log_error(
					message=message,
					title=frappe._("Duplicate eTims Job Queue - Similar Job: {0}").format(similar_job_name),
				)
				raise frappe.ValidationError(message)

	@staticmethod
	def _normalize_json(value) -> object:
		"""Parse a JSON string into a comparable Python object."""
		if isinstance(value, str):
			try:
				return json.loads(value)
			except (TypeError, ValueError):
				return value
		return value

	def after_insert(self) -> None:
		"""
		Notify the queue manager that a new job has arrived.

		The manager will start processing immediately if the queue is idle, or
		simply record the job as pending if another job is already running.
		"""
		frappe.get_single("eTims Queue Manager").on_new_job()

	def update_status(
		self,
		status: str,
		error_message: str | None = None,
		integration_request: str | None = None,
	) -> None:
		"""
		Persist a new status on this job document and, when the job reaches a
		terminal state, advance the queue manager to the next pending job.

		Args:
		    status: One of ``"Pending"``, ``"Processing"``, ``"Success"``,
		            ``"Failed"``.
		    error_message: Optional error detail to append to ``error_message``
		                   field (max 5 000 chars, cumulative).
		    integration_request: Optional name of an ``Integration Request``
		                          document to link.
		"""
		update_fields: dict = {"status": status}

		if status == "Processing":
			update_fields["last_attempt"] = now_datetime()
		elif status in ("Success", "Failed"):
			update_fields["completion_time"] = now_datetime()
			if status == "Failed":
				update_fields["last_attempt"] = now_datetime()

		if error_message:
			existing = self.error_message or ""
			combined = (f"{existing}\n{error_message}").strip() if existing else error_message
			update_fields["error_message"] = combined[:5000]

		if integration_request:
			update_fields["integration_request"] = integration_request

		self.db_set(update_fields, commit=True)

		if status in ("Success", "Failed"):
			frappe.get_single("eTims Queue Manager").advance_queue()

	def enqueue_next_page(self, next_url: str) -> None:
		"""
		Schedule the creation of a follow-up job for the next pagination page.

		The new job inherits all configuration from this job but targets the
		URL returned in the ``next`` field of the API response.  Insertion is
		deferred to a background job (``enqueue_after_commit=True``) so the
		current transaction is fully committed before the manager sees the new
		entry.

		Args:
		    next_url: The full URL for the next page as returned by the remote
		              API (e.g. ``"https://api.example.com/items/?page=2"``).
		"""
		job_data = {
			"route_key": self.route_key,
			"request_data": self.request_data,
			"handler_function": self.handler_function,
			"error_callback": self.error_callback,
			"request_method": self.request_method,
			"reference_doctype": self.reference_doctype,
			"reference_docname": self.reference_docname,
			"settings_name": self.settings_name,
			"company": self.company,
			"status": "Pending",
			"is_page": 1,
			"page_size": self.page_size or 100,
			"url": next_url,
		}
		frappe.enqueue(
			_bg_insert_next_page_job,
			job_data=job_data,
			queue="default",
			is_async=True,
			enqueue_after_commit=True,
		)

	def _resolve_callable(self, path: str | None) -> Callable | None:
		"""
		Resolve a dotted-path string to a Python callable.

		Args:
		    path: Dotted module path such as
		          ``"myapp.handlers.on_invoice_success"``, or ``None``.

		Returns:
		    The callable object, or ``None`` if *path* is falsy or does not
		    resolve to a callable.
		"""
		if not path:
			return None
		obj = frappe.get_attr(path)
		return obj if callable(obj) else None


def _bg_insert_next_page_job(job_data: dict) -> None:
	"""
	Background-job entry point that inserts a new ``eTims Job Queue`` document
	for the next pagination page.

	Deferring the insert to a background job ensures the current transaction
	is committed before a new job is enqueued, preventing the manager from
	seeing a half-committed state.

	Args:
	    job_data: Dict containing all fields required to create the new job
	              document (mirrors the ``eTims Job Queue`` doctype fields).
	"""
	frappe.get_doc({"doctype": "eTims Job Queue", **job_data}).insert(ignore_permissions=True)
	frappe.db.commit()
