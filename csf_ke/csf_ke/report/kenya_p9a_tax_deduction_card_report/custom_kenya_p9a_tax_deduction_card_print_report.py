import frappe
from frappe.utils.pdf import get_pdf
import json


@frappe.whitelist()
def print_report(report_name, filters=None):
    try:
        filters = json.loads(filters or "{}")

        report = frappe.get_doc("Report", report_name)
        columns, data = report.get_data(filters=filters, as_dict=True)
        data.remove(data[-1])

        totals = calculate_totals(data)

        data.append(totals)

        html = frappe.render_template(
            "csf_ke/report/kenya_p9a_tax_deduction_card_report/kenya_p9a_tax_deduction_card_report.html",
            {
                "title": report.report_name,
                "filters": filters,
                "columns": columns,
                "data": data,
            },
        )

        pdf = get_pdf(
            html,
            options={
                "page-size": "A3",
                "orientation": "Landscape",
                "margin-top": "10mm",
                "margin-bottom": "10mm",
                "margin-left": "10mm",
                "margin-right": "10mm",
            },
        )

        frappe.local.response.filename = f"{report_name}.pdf"
        frappe.local.response.filecontent = pdf
        frappe.local.response.type = "pdf"
        frappe.local.response.mime_type = "application/pdf"

    except Exception as e:
        frappe.throw(f"Error generating PDF: {str(e)}")

def calculate_totals(data):
    if not data:
        return {}

    totals = {}
    totals["month"] = "Total"

    fields = [key for key in data[0].keys() if key != "month"]

    for key in fields:
        totals[key] = sum(
            float(row.get(key) or 0) for row in data if isinstance(row.get(key), (int, float, str))
        )

    return totals
