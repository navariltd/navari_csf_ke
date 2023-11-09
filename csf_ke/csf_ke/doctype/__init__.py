import frappe
from frappe.utils import logger

logger.set_log_level("DEBUG")
api_logger = frappe.logger("api", allow_site=True, file_count=50)
