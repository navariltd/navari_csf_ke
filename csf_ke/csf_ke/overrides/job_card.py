
import frappe

from datetime import timedelta
import frappe

def before_submit(doc, method=None):
    allow_default_time_log = allow_default_time_logs()
    if not allow_default_time_log:
        return
    now = frappe.utils.now_datetime()
    one_hour_ago = now - timedelta(hours=1)

    if not doc.time_logs:
        doc.append("time_logs", {
            "from_time": one_hour_ago,
            "to_time": now
        })
        frappe.msgprint("No Time Logs found. Added a new Time Log from 1 hour ago to now.")
    else:
        for log in doc.time_logs:
            if not log.from_time and not log.to_time:
                log.to_time = now
                log.from_time = one_hour_ago
                frappe.msgprint("Empty Time Log found. Set from_time and to_time to 1 hour before now.")


def allow_default_time_logs():
    return frappe.get_single("Manufacturing Settings").custom_allow_default_time_logs
