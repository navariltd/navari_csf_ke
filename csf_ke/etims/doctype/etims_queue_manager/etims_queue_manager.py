from __future__ import annotations

import frappe
from frappe.model.document import Document


class eTimsQueueManager(Document):
	def on_new_job(self) -> None:
		"""
		Called after a new ``eTims Job Queue`` document is inserted.

		Refreshes queue pointers and, **only if the queue is currently idle**,
		enqueues the current job for background execution.  If the queue is
		already running, the new job will be picked up automatically once the
		in-flight job completes.
		"""
		self.reload()
		self._sync_pointers()
		self.start_next_if_idle()

	def advance_queue(self) -> None:
		"""
		Called by ``eTimsJobQueue.update_status`` after a job reaches a
		terminal state (``"Success"`` or ``"Failed"``).

		Refreshes queue pointers and enqueues the next pending job (if any) as
		a background job.
		"""
		self.reload()
		self._sync_pointers()
		self.start_next_if_idle()

	def start_next_if_idle(self) -> None:
		"""
		Enqueue :py:func:`_bg_run_current_job` **only** when no job is
		actively being processed right now.

		The guard reads the **job document's own status** from the DB — not
		the manager's ``queue_status`` field — because the manager field is a
		derived display value that can lag behind reality (e.g. still showing
		``"Processing"`` after a job has already been marked ``"Success"`` but
		before ``_sync_pointers`` ran).

		Decision logic
		--------------
		* No ``current_job`` pointer → nothing to run, return early.
		* ``current_job`` status is ``"Processing"`` in the DB → a worker is
		  already handling it; do nothing and let it call ``advance_queue``
		  when done.
		* ``current_job`` status is ``"Pending"`` → safe to dispatch.
		"""
		self.reload()

		if self.disabled:
			self.db_set("queue_status", "Paused", update_modified=False)
			return

		if not self.current_job:
			self.db_set("queue_status", "Idle", update_modified=False)
			return

		current_job_status = frappe.db.get_value("eTims Job Queue", self.current_job, "status")

		if current_job_status == "Processing":
			return

		if current_job_status != "Pending":
			self._sync_pointers()
			self.reload()
			if not self.current_job:
				return
			current_job_status = frappe.db.get_value("eTims Job Queue", self.current_job, "status")
			if current_job_status != "Pending":
				return

		self.db_set("queue_status", "Processing", update_modified=False)

		frappe.db.commit()

		frappe.enqueue(
			_bg_run_current_job,
			manager_name=self.name,
			queue="default",
			is_async=True,
			job_name=f"etims_queue_{self.current_job}",
			enqueue_after_commit=True,
		)

	@frappe.whitelist()
	def process_queue(self) -> None:
		"""
		Manual trigger available from the doctype form.

		Re-syncs the queue and kicks off the current job if the queue is idle.
		"""
		self._sync_pointers()
		self.start_next_if_idle()

	@frappe.whitelist()
	def clear_all_jobs(self) -> None:
		"""
		Unlink the queue pointers and delete every ``eTims Job Queue`` record.

		Invoked by the **Clear All Jobs** button on the form.

		Order of operations:
		    1. The manager's ``current_job``, ``next_job``, and ``last_job``
		       link fields are unlinked first, so no job is deleted while still
		       referenced.  ``queue_status`` is reset to ``"Idle"``.
		    2. Each ``eTims Job Queue`` record is then deleted individually.

		The transaction is intentionally left uncommitted so the caller controls
		when it is persisted.
		"""
		self.db_set(
			{
				"current_job": None,
				"next_job": None,
				"last_job": None,
				"queue_status": "Idle",
			},
			update_modified=False,
		)

		for job_name in frappe.get_all("eTims Job Queue", pluck="name"):
			frappe.delete_doc(
				"eTims Job Queue",
				job_name,
				ignore_permissions=True,
				force=True,
			)

	def _execute_current_job(self) -> None:
		"""
		Fetch the current job document and call its ``run_queue`` method.

		This is invoked inside a background worker via :py:func:`_bg_run_current_job`.
		Errors are logged but **not** re-raised so that the background job does
		not silently die without advancing the queue.
		"""
		if self.disabled:
			self.db_set("queue_status", "Paused", update_modified=False)
			frappe.db.commit()
			return

		self.reload()

		if not self.current_job:
			self.db_set("queue_status", "Idle", update_modified=False)
			frappe.db.commit()
			return

		job_doc = frappe.get_doc("eTims Job Queue", self.current_job)

		try:
			job_doc.run_queue()
		except Exception:
			frappe.log_error(
				title=f"eTims Queue Manager — job failed: {job_doc.name}",
				message=frappe.get_traceback(),
			)
			self.reload()
			self.advance_queue()

	def _get_all_jobs(self) -> list[dict]:
		"""
		Return all ``eTims Job Queue`` documents ordered by creation time (oldest first).

		Returns:
		    A list of dicts with ``name``, ``status``, and ``creation`` keys.
		"""
		return frappe.get_all(
			"eTims Job Queue",
			fields=["name", "status", "creation"],
			order_by="creation asc",
		)

	def _find_last_completed(self, jobs: list[dict]) -> dict | None:
		"""
		Walk the job list in reverse and return the most-recent job that has
		reached a terminal state (i.e. status is neither ``"Pending"`` nor
		``"Processing"``).

		Args:
		    jobs: Ordered list of job dicts (oldest → newest).

		Returns:
		    The last completed/failed job dict, or ``None`` if every job is
		    still pending or processing.
		"""
		for job in reversed(jobs):
			if job.status not in ("Pending", "Processing"):
				return job
		return None

	def _find_current_job(self, jobs: list[dict]) -> dict | None:
		"""
		Return the **oldest** ``Pending`` or ``Processing`` job that should be
		treated as the active job.

		Args:
		    jobs: Ordered list of job dicts (oldest → newest).

		Returns:
		    The current active job dict, or ``None`` if there are none.
		"""
		for job in jobs:
			if job.status in ("Pending", "Processing"):
				return job
		return None

	def _find_next_job(self, jobs: list[dict], current_name: str | None) -> dict | None:
		"""
		Return the first ``Pending`` job that comes *after* *current_name* in
		creation order.

		Args:
		    jobs: Ordered list of job dicts (oldest → newest).
		    current_name: The ``name`` of the current active job.

		Returns:
		    The next pending job dict, or ``None``.
		"""
		found = False
		for job in jobs:
			if job.name == current_name:
				found = True
				continue
			if found and job.status == "Pending":
				return job
		return None

	def _sync_pointers(self) -> None:
		"""
		Recompute ``current_job``, ``next_job``, ``last_job``, and
		``queue_status`` from the live state of all job documents and persist
		them to the database.

		This is intentionally **read-only with respect to job documents** — it
		only writes to the manager singleton.
		"""
		if self.disabled:
			self.db_set("queue_status", "Paused", update_modified=False)
			return

		jobs = self._get_all_jobs()

		if not jobs:
			self.db_set(
				{
					"current_job": None,
					"next_job": None,
					"last_job": None,
					"queue_status": "Idle",
				},
				update_modified=False,
			)
			return

		last_done = self._find_last_completed(jobs)
		current = self._find_current_job(jobs)
		next_job = self._find_next_job(jobs, current.name if current else None)

		if current:
			live_job_status = frappe.db.get_value("eTims Job Queue", current.name, "status")
			new_status = "Processing" if live_job_status == "Processing" else "Running"
		else:
			new_status = "Idle"

		self.db_set(
			{
				"current_job": current.name if current else None,
				"next_job": next_job.name if next_job else None,
				"last_job": last_done.name if last_done else None,
				"queue_status": new_status,
			},
			update_modified=False,
		)


def _bg_run_current_job(manager_name: str) -> None:
	"""
	Background-job entry point — runs the current job of *manager_name*.

	This function is enqueued via ``frappe.enqueue`` so that queue execution
	never blocks a foreground web request.

	Args:
	    manager_name: The ``name`` field of the ``eTims Queue Manager`` singleton
	                  (always ``"eTims Queue Manager"`` in practice).
	"""
	manager: eTimsQueueManager = frappe.get_doc("eTims Queue Manager", manager_name)
	manager._execute_current_job()
