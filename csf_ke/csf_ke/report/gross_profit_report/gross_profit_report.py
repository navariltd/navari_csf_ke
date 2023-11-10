# Copyright (c) 2023, Navari Limited and contributors
# For license information, please see license.txt

# import frappe

import frappe  # Assuming you are using Frappe framework
from frappe.utils import add_days, flt
from frappe.utils import flt, add_days
from frappe.utils import add_days
from frappe import qb
from frappe import get_all, get_value
from frappe import get_all, qb
from frappe.utils import flt

from frappe import _
import frappe
from frappe.utils import flt, getdate, comma_and, cstr
from erpnext.stock.utils import get_incoming_rate


# ... (Previous code remains the same)

def execute(filters=None):
    columns, data = [], []
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data


def fetch_conversion_factors(data, include_uom):
    conversion_factors = {}

    # Example: populate conversion factors based on your data
    for row in data:
        item_code = row.get("item_code")
        conversion_factor = get_conversion_factor(
            item_code, include_uom)  # Implement this function
        conversion_factors[item_code] = conversion_factor

    return conversion_factors


def get_columns(filters):
    columns = [
        {
            "label": "Item Code",
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 120
        },
        {
            "label": "Item Group",
            "fieldname": "item_group",
            "fieldtype": "Link",
            "options": "Item Group",
            "width": 120,
            "hidden": 1,

        },
        {
            "label": "Default UOM",
            "fieldname": "default_uom",
            "fieldtype": "Link",
            "options": "UOM",
            "width": 120,
            "hidden": 1,

        },
        {
            "label": "UOM Required",
            "fieldname": "uom_required",
            "fieldtype": "Data",
            "width": 100,
            "hidden": 1,

        },
        {
            "label": "Qty",
            "fieldname": "qty",
            "fieldtype": "Float",
            "width": 100
        },
    ]

    if filters.get("uom"):
        columns.append(
            {
                "label": f"Qty ({filters.get('uom')})",
                "fieldname": "qty_uom",
                "fieldtype": "Float",
                "width": 120,
                'indicator': 'Green',
            }
        )

    columns += [

        {
            "label": "Average Selling Rate",
            "fieldname": "average_selling_rate",
            "fieldtype": "Currency",
            "width": 120,

        },
        {
            "label": "Valuation Rate",
            "fieldname": "valuation_rate",
            "fieldtype": "Currency",
            "width": 120,


        },
        {
            "label": "Selling Amount",
            "fieldname": "selling_amount",
            "fieldtype": "Currency",
            "width": 120,

        },
        {
            "label": "Buying Amount",
            "fieldname": "buying_amount",
            "fieldtype": "Currency",
            "width": 120,


        },

        {
            "label": "Gross Profit",
            "fieldname": "gross_profit",
            "fieldtype": "Currency",
            "width": 120,


        },
        {
            "label": "Gross Profit Percentage",
            "fieldname": "gross_profit_percentage",
            "fieldtype": "Percent",
            "width": 120,


        },
    ]

    return columns


def calculate_gross_profit(buying_amount, selling_amount):

    buying_amount = float(buying_amount) if buying_amount is not None else 0.0
    selling_amount = float(
        selling_amount) if selling_amount is not None else 0.0
    return selling_amount - buying_amount


def calculate_gross_profit_percentage(gross_profit, selling_amount):
    gross_profit = float(gross_profit) if gross_profit is not None else 0.0
    selling_amount = float(
        selling_amount) if selling_amount is not None else 0.0

    if selling_amount != 0.0:
        return (gross_profit / selling_amount) * 100
    else:
        return 0  # Avoid division by zero


def get_data(filters):
    data = []
    query = get_query(filters)

    primary_data = frappe.db.sql(query, as_dict=True)
    item_dict = {}

    for item in primary_data:
        item_code = item.get('item_code')

        qty = item.get('qty')

        # Filters date
        from_date = filters.get("from_date")
        to_date = filters.get("to_date")

        # Calculate the quantity in the chosen UOM
        chosen_uom = filters.get('uom')
        item['qty_uom'] = calculate_qty_in_chosen_uom(
            item_code, item['qty'], chosen_uom, item['uom_required'], item["default_uom"])

        # valuation change
        buying_amount = get_valuation_change_sum(
            item_code, from_date, to_date)
        item['buying_amount'] = buying_amount

        selling_amount = item.get('selling_amount', 0)
        item['gross_profit'] = selling_amount - buying_amount
        item['gross_profit_percentage'] = calculate_gross_profit_percentage(
            item['gross_profit'], selling_amount)

        # Include the valuation rate
        # item['valuation_rate'] = get_valuation_rate_from_sle(
        #     item_code, from_date, to_date)
        if qty == 0:
            # Handle the case where qty is zero (e.g., set valuation_rate to 0 or handle it as appropriate)
            item['valuation_rate'] = 0
        else:
            item['valuation_rate'] = buying_amount / qty

        if item_code not in item_dict:
            item_dict[item_code] = item
        else:
            item_dict[item_code]['qty'] += item['qty']

        data.append(item)

    return data


def calculate_qty_in_chosen_uom(item_code, qty, chosen_uom, sales_invoice_uom, default_uom):

    if chosen_uom != default_uom:
        conversion_factor = get_conversion_factor(item_code, default_uom)
        if chosen_uom == "Bag" and sales_invoice_uom == "Bag":
            # If the chosen unit of measure is Kgs, calculate the quantity from the existing quantity

            calculated_qty = qty
        if chosen_uom == "Kg" and default_uom == "Bag":
            calculated_qty = qty / 0.04
        elif conversion_factor:

            # If there is a conversion factor, use it to calculate the quantity
            calculated_qty = qty / conversion_factor
    else:
        calculated_qty = qty

    return calculated_qty


def get_conversion_factor(item_code, default_uom):
   # Get the conversion factor from the UOM Conversion Detail table
    conversion_factor = frappe.get_value("UOM Conversion Detail",
                                         {"parent": item_code, "uom": default_uom},
                                         "conversion_factor")

    if not conversion_factor:
        conversion_factor = 1.0  # If no conversion factor is found, default to 1

    return conversion_factor


def get_query(filters):
    sql_query = """
    SELECT
        si_item.item_code AS item_code,
        si_item.item_group AS item_group,
        si_item.stock_uom AS default_uom,
        si_item.uom AS uom_required,
        
        CAST(SUM(si_item.stock_qty) AS DECIMAL(10, 2)) AS qty,

        SUM(si_item.base_amount) AS selling_amount,
        
        SUM(si_item.base_amount)/SUM(si_item.stock_qty) AS average_selling_rate
        
    FROM
        `tabSales Invoice Item` si_item
    INNER JOIN
        `tabSales Invoice` si ON si_item.parent = si.name
   
    WHERE
        si.docstatus = 1 AND si.status != 'Cancelled' AND si.return_against IS NULL AND si_item.item_code IS NOT NULL
"""

    # Add dynamic conditions based on the selected filters
    conditions = []

    if filters.get("company"):
        conditions.append(f"si.company = '{filters.get('company')}'")

    if filters.get("from_date"):
        conditions.append(f"si.posting_date >= '{filters.get('from_date')}'")

    if filters.get("to_date"):
        conditions.append(f"si.posting_date <= '{filters.get('to_date')}'")

    if filters.get("sales_invoice"):
        conditions.append(f"si.name = '{filters.get('sales_invoice')}'")

    if filters.get("item_group"):
        conditions.append(
            f"si_item.item_group = '{filters.get('item_group')}'")

    # Add the following conditions for item, warehouse, and UOM filters
    if filters.get("item"):
        conditions.append(f"si_item.item_code = '{filters.get('item')}'")

    if filters.get("warehouse"):
        conditions.append(f"si_item.warehouse = '{filters.get('warehouse')}'")

    if conditions:
        sql_query += " AND " + " AND ".join(conditions)

    sql_query += """
        GROUP BY
            si_item.item_code, si_item.item_group, si_item.stock_uom, si_item.uom
    """
    return sql_query


def get_sales_invoices(item_code, from_date, to_date):
    # Implement the logic to fetch sales data
    sql_query = """
        SELECT si.posting_date, si.title, si.update_stock, si.name,si.amended_from,
        (SELECT AVG(sii.stock_qty)
         FROM `tabSales Invoice Item` AS sii
         WHERE sii.parent = si.name AND sii.item_code = %(item_code)s) as qty
        FROM `tabSales Invoice` AS si
        WHERE si.name IN (
            SELECT sii.parent
            FROM `tabSales Invoice Item` AS sii
            WHERE sii.item_code = %(item_code)s AND si.docstatus = 1
            AND si.status != 'Cancelled'
            AND si.posting_date >= %(from_date)s AND si.posting_date <= %(to_date)s
            AND si.return_against IS NULL AND sii.item_code IS NOT NULL
        )
    """

    sales_invoices = frappe.db.sql(
        sql_query, {"item_code": item_code, "from_date": from_date, "to_date": to_date}, as_dict=True)

    return sales_invoices


def get_stock_entry_valuation(item_code):
    stock_entry_sql = """
        SELECT (SELECT AVG(sii.valuation_rate)
                FROM `tabStock Reconciliation Item` AS sii
                WHERE sii.parent = st.name AND sii.item_code = %(item_code)s) as valuation_rate
        FROM `tabStock Reconciliation` AS st
        WHERE st.name IN (
            SELECT sii.parent
            FROM `tabStock Reconciliation Item` AS sii
            WHERE sii.item_code = %(item_code)s AND st.docstatus = 1
        )
    """

    valuation_data = frappe.db.sql(
        stock_entry_sql, {"item_code": item_code}, as_dict=True)
    return valuation_data


def get_stock_ledger_entries(voucher_name, item_code, from_date, to_date):
    filters = {
        "voucher_no": voucher_name,
        "item_code": item_code,
        "docstatus": 1,
        "is_cancelled": 0,
        "posting_date": [">=", from_date],
    }

    or_filters = {
        "posting_date": ["<=", to_date],
    }

    fields = [
        "stock_value_difference as valuation_change",
        "voucher_no",
        "voucher_type",
        "item_code",
        "name",
        "posting_date"
    ]

    sle_entries = frappe.get_all(
        "Stock Ledger Entry", filters=filters, or_filters=or_filters, fields=fields)

    return sle_entries


def get_stock_ledger_entries_recalculate(voucher_name, item_code, from_date, to_date):
    filters = {
        "voucher_no": voucher_name,
        "item_code": item_code,
        "docstatus": 1,
        "is_cancelled": 0,
        "recalculate_rate": 0,
        "posting_date": [">=", from_date],
    }

    or_filters = {
        "posting_date": ["<=", to_date],
    }

    fields = [
        "stock_value_difference as valuation_change",
        "voucher_no",
        "voucher_type",
        "item_code",
        "name",
        "posting_date"
    ]

    sle_entries = frappe.get_all(
        "Stock Ledger Entry", filters=filters, or_filters=or_filters, fields=fields)

    return sle_entries


def get_stock_ledger_entries_cancelled_but_amended(voucher_name, item_code, from_date, to_date):
    filters = {
        "voucher_no": voucher_name,
        "item_code": item_code,
        "docstatus": 1,
        "is_cancelled": 1,
        "posting_date": [">=", from_date],
    }

    or_filters = {
        "posting_date": ["<=", to_date],
    }

    fields = [
        "stock_value_difference as valuation_change",
        "voucher_no",
        "voucher_type",
        "item_code",
        "name",
        "posting_date"
    ]

    sle_entries = frappe.get_all(
        "Stock Ledger Entry", filters=filters, or_filters=or_filters, fields=fields)

    return sle_entries


def get_delivery_notes(item_code, from_date, to_date):
    filters = {
        "item_code": item_code,
        "posting_date": [">=", from_date, "<=", to_date],
        "status": ["!=", "Cancelled"]
    }

    fields = ["title", "posting_date", "name"]

    delivery_notes = frappe.get_all(
        "Delivery Note", filters=filters, fields=fields)

    return delivery_notes


def get_valuation_change_sum(item_code, from_date, to_date):

    quantity = 0.0
    used_vouchers = set()
    valuation_change_sum = 0.0
    buying_total = 0.0
    un_used_delivery_note = set()
    used_delivery_note = set()

    sales_invoices = get_sales_invoices(item_code, from_date, to_date)
    # Initialize a list to store the titles of Sales Invoices

    sales_invoice_title = [
        si.get("title") for si in sales_invoices]

    filters = {}

    # Get all Delivery Notes within the date range
    delivery_notes = get_delivery_notes(item_code, from_date, to_date)

    # Filter Delivery Notes based on their posting date matching Sales Invoices
    filtered_delivery_notes = [dn for dn in delivery_notes if dn.get(
        "title") in sales_invoice_title]

    # Extract the names of filtered delivery notes
    filtered_delivery_note_names = [
        dn.get("name") for dn in filtered_delivery_notes]

    filters["voucher_no"] = ["in", filtered_delivery_note_names]
    for delivery_note in filtered_delivery_notes:

        used_vouchers.add(delivery_note.get("title"))

    # proceed with Stock Ledger Entries for the filtered Delivery Notes
    if item_code in ["60er Kali MOP gran - 50Kg", "60er Kali MOP gran B pink- 50Kg"]:
        sle_entries = get_stock_ledger_entries_recalculate(
            filters["voucher_no"], item_code, from_date, to_date)

    else:
        sle_entries = get_stock_ledger_entries(
            filters["voucher_no"], item_code, from_date, to_date)

    if sle_entries:

        for entry in sle_entries:
            dl_used = entry.get("voucher_no")
            used_delivery_note.add(dl_used)
            valuation_change_sum += flt(entry.get("valuation_change"))
            quantity += flt(entry.get("actual_qty"))
    else:
        for dl in filtered_delivery_note_names:
            if dl not in used_delivery_note:
                un_used_delivery_note.add(dl)

    for si in sales_invoices:
        update_stock = si.get("update_stock")
        quantity += si.get("qty")
        amended = si.get("amended_from")

        if update_stock == 1 or amended is not None:
            if amended is not None:
                voucher_name = amended
                sle_entries_from_si_amended = get_stock_ledger_entries_cancelled_but_amended(
                    voucher_name, item_code, from_date, to_date)
                if sle_entries_from_si_amended:
                    for entry in sle_entries_from_si_amended:
                        valuation_change_sum += flt(
                            entry.get("valuation_change"))
                        quantity += flt(entry.get("actual_qty"))
            else:
                voucher_name = si.get("name")
            voucher_title = si.get("title")
            used_vouchers.add(voucher_title)
            sle_entries_from_si = get_stock_ledger_entries(
                voucher_name, item_code, from_date, to_date)

            if sle_entries_from_si:
                for entry in sle_entries_from_si:

                    valuation_change_sum += flt(entry.get("valuation_change"))
                    quantity += flt(entry.get("actual_qty"))

        elif update_stock == 0:

            voucher_name = si.get("name")
            voucher_title_u = si.get("title")
            if voucher_title_u not in used_vouchers:

                stock_entry_valuation = get_stock_entry_valuation(item_code)
                if stock_entry_valuation:

                    for entry in stock_entry_valuation:
                        valuation_rate = entry.get("valuation_rate")
                        buying_total = valuation_rate*quantity

                        valuation_change_sum = abs(
                            valuation_change_sum)
                        valuation_change_sum += buying_total

                else:
                    pass

    valuation_change_sum = abs(valuation_change_sum)
    return flt(valuation_change_sum)
