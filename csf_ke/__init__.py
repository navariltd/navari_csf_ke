import frappe
from frappe.utils.user import is_website_user

__version__ = "16.0.1"


def is_frappe_version(version: str, above: bool = False, below: bool = False):
	from frappe.pulse.utils import get_frappe_version

	current_version = get_frappe_version()
	major_version = int(current_version.split(".")[0])
	target_version = int(version.split(".")[0])

	if above:
		return major_version > target_version
	if below:
		return major_version < target_version
	return major_version == target_version


def check_app_permission():
	if frappe.session.user == "Administrator":
		return True

	if is_website_user():
		return False

	return True
