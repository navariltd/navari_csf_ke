import click
from frappe.custom.doctype.custom_field.custom_field import \
    create_custom_fields

from csf_ke.constants import DEPOSIT_CUSTOM_FIELDS


def after_install():
	try:
		print("Setting up CSF_KE...")
		make_custom_fields()
		click.secho("Thank you for installing CSF_KE!", fg="green")
	except Exception as e:
		BUG_REPORT_URL = "https://github.com/navariltd/csf_ke/issues/new"
		click.secho(
			"Installation for CSF_KE app failed due to an error."
			" Please try re-installing the app or"
			f" report the issue on {BUG_REPORT_URL} if not resolved.",
			fg="bright_red",
		)
		raise e



def make_custom_fields():
	print("Setup custom fields for erpnext...")

	create_custom_fields(DEPOSIT_CUSTOM_FIELDS, ignore_validate=True)
	

