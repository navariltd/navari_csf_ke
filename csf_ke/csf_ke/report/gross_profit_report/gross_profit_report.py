# Copyright (c) 2023, Navari Limited and contributors
# For license information, please see license.txt

# import frappe

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

        },
        {
            "label": "Default UOM",
            "fieldname": "default_uom",
            "fieldtype": "Link",
            "options": "UOM",
            "width": 120,

        },
        {
            "label": "UOM Required",
            "fieldname": "uom_required",
            "fieldtype": "Data",
            "width": 100,

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


# def get_valuation_change_sum(item_code, from_date, to_date):
#     quantity = 0.0
#     sql_query = """
#         SELECT si.posting_date, si.title, si.update_stock,si.name
#         FROM `tabSales Invoice` AS si
#         WHERE si.name IN (
#             SELECT sii.parent
#             FROM `tabSales Invoice Item` AS sii
#             WHERE sii.item_code = %(item_code)s AND si.docstatus = 1 AND si.is_return = 0
#             AND si.posting_date >= %(from_date)s AND si.posting_date <= %(to_date)s
#         )
#     """

#     sales_invoices = frappe.db.sql(
#         sql_query, {"item_code": item_code, "from_date": from_date, "to_date": to_date}, as_dict=True)

#     # Initialize a list to store the posting dates of Sales Invoices
#     sales_invoice_title = [
#         si.get("title") for si in sales_invoices]

#     filters = {
#         "item_code": item_code,
#         "docstatus": 1,
#         "is_cancelled": 0,
#     }

#     if from_date:
#         filters["posting_date"] = ("<=", from_date)

#     if to_date:
#         if "posting_date" in filters:
#             filters["posting_date"] = (">=", from_date, "<=", to_date)
#         else:
#             filters["posting_date"] = (">=", add_days(to_date, 1))

#     # Get all Delivery Notes within the date range
#     delivery_notes = frappe.get_all(
#         "Delivery Note",
#         filters={
#             "item_code": item_code,
#             "posting_date": [">=", from_date, "<=", to_date],
#         },
#         fields=["title", "posting_date", "name"],
#     )

#     # Filter Delivery Notes based on their posting date matching Sales Invoices
#     filtered_delivery_notes = [dn for dn in delivery_notes if dn.get(
#         "title") in sales_invoice_title]

#     # Extract the names of filtered delivery notes
#     filtered_delivery_note_names = [
#         dn.get("name") for dn in filtered_delivery_notes]

#     filters["voucher_no"] = ["in", filtered_delivery_note_names]
#     # frappe.msgprint(str(filters))
#     # proceed with Stock Ledger Entries for the filtered Delivery Notes
#     sle_entries = frappe.get_all("Stock Ledger Entry",
#                                  filters={
#                                      "voucher_no": ["in", filtered_delivery_note_names], "item_code": item_code, "docstatus": 1, "is_cancelled": 0,
#                                      "posting_date": [">=", from_date]
#                                  },
#                                  or_filters={
#                                      "posting_date": ["<=", to_date]},
#                                  fields=["stock_value_difference as valuation_change", "voucher_no", "voucher_type", "item_code", "posting_date", "name", "actual_qty"])
#     valuation_change_sum = 0.0
#     # frappe.msgprint(str(sle_entries))
#     if sle_entries:
#         for entry in sle_entries:
#             # frappe.msgprint(str(entry.get("posting_date")))
#             valuation_change_sum += flt(entry.get("valuation_change"))
#             quantity += flt(entry.get("actual_qty"))
#     else:
#         pass

#     for si in sales_invoices:
#         update_stock = si.get("update_stock")
#         if update_stock == 1:
#             voucher_name = si.get("name")
#             # frappe.msgprint(str(voucher_name))
#             sle_entries_from_si = frappe.get_all("Stock Ledger Entry",
#                                                  filters={
#                                                      "voucher_no": voucher_name, "item_code": item_code, "docstatus": 1, "is_cancelled": 0},
#                                                  or_filters=[["posting_date", ">=", from_date], [
#                                                      "posting_date", "<=", to_date]],
#                                                  fields=["stock_value_difference as valuation_change", "voucher_no", "voucher_type", "item_code", "posting_date"])
#             if sle_entries_from_si:

#                 for entry in sle_entries_from_si:
#                     # frappe.msgprint(str(entry))
#                     valuation_change_sum += flt(entry.get("valuation_change"))
#                     quantity += flt(entry.get("actual_qty"))
#     # frappe.msgprint(str(valuation_change_sum))

#     valuation_change_sum = abs(valuation_change_sum)
#     return flt(valuation_change_sum)


def get_valuation_change_sum(item_code, from_date, to_date):
    quantity = 0.0
    sql_query = """
        SELECT si.posting_date, si.title, si.update_stock,si.name
        FROM `tabSales Invoice` AS si
        WHERE si.name IN (
            SELECT sii.parent
            FROM `tabSales Invoice Item` AS sii
            WHERE sii.item_code = %(item_code)s AND si.docstatus = 1
            AND si.posting_date >= %(from_date)s AND si.posting_date <= %(to_date)s AND si.return_against IS NULL AND sii.item_code IS NOT NULL
        )
    """

    sales_invoices = frappe.db.sql(
        sql_query, {"item_code": item_code, "from_date": from_date, "to_date": to_date}, as_dict=True)

    # Initialize a list to store the posting dates of Sales Invoices
    sales_invoice_title = [
        si.get("title") for si in sales_invoices]
    filters = {
        "item_code": item_code,
        "docstatus": 1,
        "is_cancelled": 0,
    }

    if from_date:
        filters["posting_date"] = ("<=", from_date)

    if to_date:
        if "posting_date" in filters:
            filters["posting_date"] = (">=", from_date, "<=", to_date)
        else:
            filters["posting_date"] = (">=", add_days(to_date, 1))

    # Get all Delivery Notes within the date range
    delivery_notes = frappe.get_all(
        "Delivery Note",
        filters={
            "item_code": item_code,
            "posting_date": [">=", from_date, "<=", to_date],
        },
        fields=["title", "posting_date", "name"],
    )

    # Filter Delivery Notes based on their posting date matching Sales Invoices
    filtered_delivery_notes = [dn for dn in delivery_notes if dn.get(
        "title") in sales_invoice_title]

    # Extract the names of filtered delivery notes
    filtered_delivery_note_names = [
        dn.get("name") for dn in filtered_delivery_notes]

    filters["voucher_no"] = ["in", filtered_delivery_note_names]
    # frappe.msgprint(str(filters))
    # proceed with Stock Ledger Entries for the filtered Delivery Notes
    sle_entries = frappe.get_all("Stock Ledger Entry",
                                 filters={
                                     "voucher_no": ["in", filtered_delivery_note_names], "item_code": item_code, "docstatus": 1, "is_cancelled": 0,
                                     "posting_date": [">=", from_date]
                                 },
                                 or_filters={
                                     "posting_date": ["<=", to_date]},
                                 fields=["stock_value_difference as valuation_change", "voucher_no", "voucher_type", "item_code", "posting_date", "name", "actual_qty"])
    valuation_change_sum = 0.0
    # frappe.msgprint(str(sle_entries))
    if sle_entries:
        for entry in sle_entries:
            # frappe.msgprint(str(entry.get("posting_date")))
            valuation_change_sum += flt(entry.get("valuation_change"))
            quantity += flt(entry.get("actual_qty"))
    else:
        pass

    for si in sales_invoices:
        update_stock = si.get("update_stock")
        if update_stock == 1:
            voucher_name = si.get("name")
            # frappe.msgprint(str(voucher_name))
            sle_entries_from_si = frappe.get_all("Stock Ledger Entry",
                                                 filters={
                                                     "voucher_no": voucher_name, "item_code": item_code, "docstatus": 1, "is_cancelled": 0},
                                                 or_filters=[["posting_date", ">=", from_date], [
                                                     "posting_date", "<=", to_date]],
                                                 fields=["stock_value_difference as valuation_change", "voucher_no", "voucher_type", "item_code", "posting_date"])
            if sle_entries_from_si:

                for entry in sle_entries_from_si:
                    # frappe.msgprint(str(entry))
                    valuation_change_sum += flt(entry.get("valuation_change"))
                    quantity += flt(entry.get("actual_qty"))
    # frappe.msgprint(str(valuation_change_sum))

    valuation_change_sum = abs(valuation_change_sum)
    return flt(valuation_change_sum)
