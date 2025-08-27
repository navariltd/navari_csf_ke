# Copyright (c) 2022, Navari Limited and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import os
from pypika.functions import Coalesce
import csv
import re
from datetime import datetime

def execute(filters=None):
    return KenyaSalesTaxReport(filters).run()

class KenyaSalesTaxReport(object):
    def __init__(self, filters=None):
        self.filters = frappe._dict(filters or {})
        self.registered_customers_total_sales = 0
        self.registered_customers_total_vat = 0
        self.unregistered_customers_total_sales = 0
        self.unregistered_customers_total_vat = 0

    def run(self):
        columns = self.get_columns()
        data = self.get_data()
        report_summary = self.get_report_summary()

        return columns, data, None, None, report_summary
 
    def get_columns(self):
        columns =  [
                {
                    "label": _("PIN of purchaser"),
                    "fieldname": "pin_of_purchaser",
                    "fieldtype": "Data",
                    "width": 160
                },
                {
                    "label": _("Name of purchaser"),
                    "fieldname": "name_of_purchaser",
                    "fieldtype": "Data",
                    "width": 240
                },
                {
                    "label":_("Invoice Date"),
                    "fieldname": "invoice_date",
                    "fieldtype": "Date",
                    "width": 160
                },
                {
                    "label": _("Invoice Number"),
                    "fieldname": "invoice_name",
                    "fieldtype": "Link",
                    "options": "Sales Invoice",
                    "width": 200
                },
                {
                    "label": _("ETR Serial Number"),
                    "fieldname": "etr_serial_number",
                    "fieldtype": "Data",
                    "width": 200
                },
                {
                    "label": _("ETR Invoice Number"),
                    "fieldname": "etr_invoice_number",
                    "fieldtype": "Data",
                    "width": 200
                },
                {
                    "fieldname": _("cu_link"),
                    "label": "CU Link",
                    "fieldtype": "Data",
                    "width": 200
                },
                {
                    "label": _("CU Invoice Date"),
                    "fieldname": "cu_invoice_date",
                    "fieldtype": "Date",
                    "width": 200
                   },
                {
                    "label": _("Taxable Value(Ksh)"),
                    "fieldname": "taxable_value",
                    "fieldtype": "Currency",
                    "width": 160
                },
                {
                    "label": _("Amount of VAT(Ksh)"),
                    "fieldname": "amount_of_vat",
                    "fieldtype": "Currency",
                    "width": 160
                },
                {
                    "label": _("Return CU Invoice Number"),
                    "fieldname": "return_cu_invoice_number",
                    "fieldtype": "Data",
                    "width": 200
                },
                {
                    "label": _("Return CU Invoice Date"),
                    "fieldname": "return_cu_invoice_date",
                    "fieldtype": "Date",
                    "width": 160
                }
        ]

        if self.filters.is_return == "Is Return":
            columns += [
                {
                    "label": _("Return Against"),
                    "fieldname": "return_against",
                    "fieldtype": "Link",
                    "options": "Sales Invoice",
                    "width": 200
                }
            ]

        return columns
    
    def get_sales_invoices(self):
        company = self.filters.company
        from_date = self.filters.from_date
        to_date = self.filters.to_date
        is_return = self.filters.is_return

        sale_invoice_doc = frappe.qb.DocType('Sales Invoice')
        customer_doc = frappe.qb.DocType('Customer')

        sales_invoice_query = (
            frappe.qb.from_(sale_invoice_doc)
            .inner_join(customer_doc)
            .on(sale_invoice_doc.customer == customer_doc.name)
            .select(
                Coalesce(customer_doc.tax_id, "").as_('pin_of_purchaser'),
                sale_invoice_doc.customer_name.as_('name_of_purchaser'),
                sale_invoice_doc.etr_serial_number.as_('etr_serial_number'),
                sale_invoice_doc.etr_invoice_number.as_('etr_invoice_number'),
                sale_invoice_doc.cu_link.as_('cu_link'),
                sale_invoice_doc.cu_invoice_date.as_('cu_invoice_date'),
                sale_invoice_doc.posting_date.as_('invoice_date'),
                sale_invoice_doc.name.as_('invoice_name'),
                sale_invoice_doc.base_grand_total.as_('invoice_total_sales'),
                sale_invoice_doc.return_against.as_('return_against')
            )
            .where(sale_invoice_doc.docstatus == 1)
        )

        if company:
            sales_invoice_query = sales_invoice_query.where(sale_invoice_doc.company == company)
        if from_date:
            sales_invoice_query = sales_invoice_query.where(sale_invoice_doc.posting_date >= from_date)
        if to_date:
            sales_invoice_query = sales_invoice_query.where(sale_invoice_doc.posting_date <= to_date)        
        if is_return == "Is Return":
            sales_invoice_query = sales_invoice_query.where(sale_invoice_doc.is_return == 1)
        elif is_return == "Normal Sales Invoice":
            sales_invoice_query = sales_invoice_query.where(sale_invoice_doc.is_return == 0)

        # Add ORDER BY for consistent results and index usage
        sales_invoice_query = sales_invoice_query.orderby(
            sale_invoice_doc.posting_date, sale_invoice_doc.name
        )

        sales_invoices = sales_invoice_query.run(as_dict=True)
        
        # Batch fetch return invoice details
        return_against_invoices = [
            inv['return_against'] for inv in sales_invoices 
            if inv.get('return_against')
        ]
        
        if return_against_invoices:
            return_invoice_details = frappe.db.get_all(
                'Sales Invoice',
                filters={'name': ['in', return_against_invoices]},
                fields=['name', 'etr_invoice_number', 'cu_invoice_date']
            )
            
            return_details_map = {
                detail['name']: detail for detail in return_invoice_details
            }
            
            # Update invoices with return details
            for invoice in sales_invoices:
                if (invoice.get('return_against') and 
                    invoice['return_against'] in return_details_map):
                    details = return_details_map[invoice['return_against']]
                    invoice['return_cu_invoice_number'] = details.get('etr_invoice_number')
                    invoice['return_cu_invoice_date'] = details.get('cu_invoice_date')

        return sales_invoices

    def get_sales_invoice_items(self, sales_invoice_name, tax_template=None):
        sales_invoice_item_doc = frappe.qb.DocType('Sales Invoice Item')
        sales_invoice_items_query = frappe.qb.from_(sales_invoice_item_doc) \
            .select(
                sales_invoice_item_doc.amount.as_('amount'),
                sales_invoice_item_doc.base_net_amount.as_('taxable_value'),
                sales_invoice_item_doc.item_tax_template.as_('item_tax_template')
            ) \
            .where(sales_invoice_item_doc.parent == sales_invoice_name)

        if tax_template:
            sales_invoice_items_query = sales_invoice_items_query.where(sales_invoice_item_doc.item_tax_template == tax_template)

        items_or_services = sales_invoice_items_query.run(as_dict=True)
        return items_or_services

    def get_data(self):
        if self.filters.from_date > self.filters.to_date:
            frappe.throw(_("To Date cannot be before From Date. {}").format(self.filters.to_date))
        report_details = []

        sales_invoices = self.get_sales_invoices()

        for sales_invoice in sales_invoices:
            report_details.append(sales_invoice)

            items_or_services = self.get_sales_invoice_items(sales_invoice.invoice_name, self.filters.tax_template)

            total_taxable_value = 0
            total_vat = 0

            for item_or_service in items_or_services:
                tax_rate = frappe.db.get_value('Item Tax Template Detail',
                                            {'parent': item_or_service['item_tax_template']},
                                            ['tax_rate'])
                item_or_service['amount_of_vat'] = 0 if not tax_rate else item_or_service['taxable_value'] * (tax_rate / 100)

                total_taxable_value += item_or_service['taxable_value']
                total_vat += item_or_service['amount_of_vat']
                item_or_service['indent'] = 1

            sales_invoice['taxable_value'] = total_taxable_value
            sales_invoice['amount_of_vat'] = total_vat

        report_details = list(filter(lambda report_entry: report_entry['taxable_value'], report_details))

        for report_entry in report_details:
            if report_entry['pin_of_purchaser']:
                self.registered_customers_total_sales += report_entry['invoice_total_sales']
                self.registered_customers_total_vat += report_entry['amount_of_vat']
            else:
                self.unregistered_customers_total_sales += report_entry['invoice_total_sales']
                self.unregistered_customers_total_vat += report_entry['amount_of_vat']

        return report_details


    def get_report_summary(self):
        return [{
            "value": self.registered_customers_total_sales,
            "indicator": "Green",
            "label": _("Registered customers total sales"),
            "datatype": "Currency",
            "currency": "KES"
        }, {
            "value": self.registered_customers_total_vat,
            "indicator": "Green",
            "label": _("Registered customers total VAT"),
            "datatype": "Currency",
            "currency": "KES"
        }, {
            "value": self.unregistered_customers_total_sales,
            "indicator": "Green",
            "label": _("Unregistered customers total sales"),
            "datatype": "Currency",
            "currency": "KES"
        }, {
            "value": self.unregistered_customers_total_vat,
            "indicator": "Green",
            "label": _("Unregistered customers total VAT"),
            "datatype": "Currency",
            "currency": "KES"
        }]

@frappe.whitelist()
def download_custom_csv_format(company, from_date=None, to_date=None):
    
    if not company:
        frappe.throw(_("Company is required"))
    if not from_date:
        frappe.throw(_("From Date is required"))
    if not to_date:
        frappe.throw(_("To Date is required"))
    
    from_date_str = from_date.strftime("%y-%m-%d") if isinstance(from_date, datetime) else from_date
    to_date_str = to_date.strftime("%y-%m-%d") if isinstance(to_date, datetime) else to_date

    private_path = frappe.utils.get_site_path('private', 'files')
    os.makedirs(private_path, exist_ok=True)

    tax_templates = [
        "VAT 16%",
        "Exempt",
        "Zero-Rated"
    ]
    
    csv_files = {}

    for template_name in tax_templates:
        
        pattern = re.compile(rf"{re.escape(template_name)}[\s\-_]*[\d\%]*", re.IGNORECASE)

        all_tax_templates = frappe.get_all('Item Tax Template', fields=['name'])

        for template in all_tax_templates:
            match = pattern.match(template['name'])
            if match:
                # Sanitize the company and template names for the file name
                company_abbr = frappe.db.get_value("Company", company, "abbr") or ""
                sanitized_template_name = re.sub(r"[^\w]+", "_", template_name).lower()

                # Generate a valid file name
                csv_file_name = (
                    f"sales_{sanitized_template_name[:6]}_{company_abbr}_{from_date_str}_to_{to_date_str}.csv".strip("_")
                )

                full_file_path = os.path.join(private_path, csv_file_name)
                file_url = f"/private/files/{csv_file_name}"
                
                sales_invoices = KenyaSalesTaxReport({
                    "company": company,
                    "from_date": from_date,
                    "to_date": to_date,
                    "tax_template": template['name']
                }).get_data()

                if sales_invoices:

                    with open(full_file_path, 'w', newline='') as csvfile:
                        writer = csv.writer(csvfile)

                        for invoice in sales_invoices:
                            if invoice.get('pin_of_purchaser'):                                
                                writer.writerow([
                                    invoice.get('pin_of_purchaser', ''),
                                    invoice.get('name_of_purchaser', ''),
                                    invoice.get('etr_serial_number', ''),
                                    invoice.get('invoice_date', '').strftime("%d/%m/%Y"),
                                    f"|{(invoice.get('etr_invoice_number', ''))}",
                                    invoice.get('invoice_name', ''),
                                    invoice.get('taxable_value', ''),
                                    '',
                                    f"|{invoice.get('return_cu_invoice_number', '')}" if invoice.return_against else '',
                                    invoice.get('return_cu_invoice_date').strftime("%d/%m/%Y") if invoice.return_against and invoice.get('return_cu_invoice_date') else '',
                                ])
                    
                    file_record = frappe.get_doc({
                        "doctype": "File",
                        "file_name": csv_file_name,
                        "file_url": file_url,
                        "attached_to_name": company,
                        "attached_to_doctype": "Sales Invoice",
                        "file_size": os.path.getsize(full_file_path),
                        "is_private": 1,
                        "file_type": "CSV",
                    })
                    file_record.insert()

                    csv_files[company_abbr] = file_url

    return csv_files
