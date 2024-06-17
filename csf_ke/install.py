import json
import os

import click
import frappe
from frappe.core.doctype.data_import.data_import import import_doc


def load_custom_fixtures() -> None:
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
        {"doctype": "Salary Component"},
        {"doctype": "Salary Structure"},
    ]

    for fixture in fixtures:
        doctype = fixture.get("doctype")
        fixture_filters = fixture.get("filters", None)

        # os.chdir("..")
        path = os.path.join(
            os.getcwd()[:-6],
            f"apps/csf_ke/csf_ke/fixtures/{'_'.join(doctype.lower().split(' '))}.json",
        )
        click.secho(f"Path: {path}", fg="yellow")

        existing_records = frappe.get_all(doctype, fixture_filters)
        if not existing_records:
            click.secho(f"Adding records for {doctype}", fg="green")

            import_doc(path)

        else:
            click.secho(f"{doctype} record exists", fg="red")
            continue
