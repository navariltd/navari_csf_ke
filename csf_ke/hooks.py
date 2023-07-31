from . import __version__ as app_version

app_name = "csf_ke"
app_title = "CSF KE"
app_publisher = "Navari Limited"
app_description = "Country Specific Functionality for Kenya"
app_icon = "drag"
app_color = "grey"
app_email = "info@navari.co.ke"
app_license = "GNU General Public License (v3)"


fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [
            [
                "name",
                "in",
                (
                   	"Employee-national_id",
					"Employee-nhif_no",
					"Employee-nssf_no",
					"Employee-tax_id",
                    "Salary Component-p9a_tax_deduction_card_type",								
                ),
            ]
        ],
    },
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/csf_ke/css/csf_ke.css"
# app_include_js = "/assets/csf_ke/js/csf_ke.js"

# include js, css files in header of web template
# web_include_css = "/assets/csf_ke/css/csf_ke.css"
# web_include_js = "/assets/csf_ke/js/csf_ke.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "csf_ke/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "csf_ke.install.before_install"
# after_install = "csf_ke.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "csf_ke.uninstall.before_uninstall"
# after_uninstall = "csf_ke.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "csf_ke.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"csf_ke.tasks.all"
# 	],
# 	"daily": [
# 		"csf_ke.tasks.daily"
# 	],
# 	"hourly": [
# 		"csf_ke.tasks.hourly"
# 	],
# 	"weekly": [
# 		"csf_ke.tasks.weekly"
# 	]
# 	"monthly": [
# 		"csf_ke.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "csf_ke.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "csf_ke.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "csf_ke.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

user_data_fields = [
	{
		"doctype": "{doctype_1}",
		"filter_by": "{filter_by}",
		"redact_fields": ["{field_1}", "{field_2}"],
		"partial": 1,
	},
	{
		"doctype": "{doctype_2}",
		"filter_by": "{filter_by}",
		"partial": 1,
	},
	{
		"doctype": "{doctype_3}",
		"strict": False,
	},
	{
		"doctype": "{doctype_4}"
	}
]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"csf_ke.auth.validate"
# ]

