# Copyright (c) 2026, Navari Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.permissions import get_valid_perms

logger = frappe.logger("user_permission_migration", allow_site=True, file_count=50)


class UserPermissionMigrationTool(Document):
	@frappe.whitelist()
	def run_permission_migration(self):
		self.status = "Running"
		self.save(ignore_permissions=True)

		frappe.enqueue(
			"csf_ke.csf_ke.doctype.user_permission_migration_tool.user_permission_migration_tool.permission_migration_job",
			docname=self.name,
			queue="long",
			timeout=15000,
		)

		return "Job Started"


def permission_migration_job(docname):
	doc = frappe.get_single("User Permission Migration Tool")

	logger.info(f"Starting permission migration for tool {docname}")

	try:
		if doc.run_for_all_users:
			users = frappe.get_all(
				"User",
				filters={"enabled": 1, "user_type": "System User"},
				pluck="name",
			)
		else:
			users = [doc.user]

		for user in users:
			logger.info(f"Processing user: {user}")

			propagate_user_permissions(user)

			logger.info(f"Finished user: {user}")

		doc.status = "Completed"
		doc.save(ignore_permissions=True)

		logger.info("Migration completed successfully")

	except Exception:
		doc.status = "Failed"
		doc.save(ignore_permissions=True)

		logger.error(frappe.get_traceback())


def propagate_user_permissions(user):
	"""
	Convert global user permissions (apply_to_all_doctypes=1)
	into scoped permissions using applicable_for.

	Company permissions are ignored and left global.
	"""

	# get all user permissions
	permissions = frappe.get_all(
		"User Permission",
		filters={"user": user},
		fields=[
			"name",
			"allow",
			"for_value",
			"apply_to_all_doctypes",
		],
	)

	# get all doctypes user has access to
	user_doctypes = {
		p["parent"]
		for p in get_valid_perms(user=user)
		if p.get("permlevel") == 0 and (p.get("read") or p.get("write") or p.get("create"))
	}

	# metadata cache (avoid repeated meta loading)
	meta_cache = {}

	def get_meta(dt):
		if dt in meta_cache:
			return meta_cache[dt]

		if not frappe.db.exists("DocType", dt):
			meta_cache[dt] = None
			return None

		try:
			meta_cache[dt] = frappe.get_meta(dt)
		except Exception:
			meta_cache[dt] = None

		return meta_cache[dt]

	for perm in permissions:
		master = perm["allow"]
		value = perm["for_value"]

		# ignore company permissions entirely
		if master == "Company":
			continue

		# only handle global permissions
		if not perm["apply_to_all_doctypes"]:
			continue

		# master meta
		master_meta = get_meta(master)

		# only propagate masters belonging to a company
		if not master_meta.has_field("company"):
			continue

		created = 0

		for dt in user_doctypes:
			# skip master itself and company
			if dt in {master, "Company"}:
				continue

			meta = get_meta(dt)

			if not meta:
				continue

			# skip child tables and singles
			if meta.istable or meta.issingle:
				continue

			# check if doctype links to master
			has_link = any(df.fieldtype == "Link" and df.options == master for df in meta.fields)

			if not has_link:
				continue

			# check if permission already exists
			exists = frappe.db.exists(
				"User Permission",
				{
					"user": user,
					"allow": master,
					"for_value": value,
					"applicable_for": dt,
				},
			)

			if exists:
				continue

			# create scoped permission
			frappe.get_doc(
				{
					"doctype": "User Permission",
					"user": user,
					"allow": master,
					"for_value": value,
					"apply_to_all_doctypes": 0,
					"applicable_for": dt,
				}
			).insert(ignore_permissions=True)

			logger.info(f"Creating permission: user={user} master={master} value={value} applicable_for={dt}")

			created += 1

		# only delete global permission if we created replacements
		if created > 0:
			frappe.delete_doc(
				"User Permission",
				perm["name"],
				ignore_permissions=True,
			)

			logger.info(f"Deleting global permission {perm['name']} for {master}:{value}")

	frappe.db.commit()  # nosemgrep
