# Copyright (c) 2023, Navari Limited and contributors
# For license information, please see license.txt

# import frappe

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
            "hidden": 1
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
    currency_precision = 3

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
            item_code, item['qty'], chosen_uom, item['uom_required'])

        buying_amount = get_buying_amount(item_code, qty, from_date, to_date)
        item['buying_amount'] = buying_amount

        # valuation change
        valuation_change = get_valuation_change_sum(
            item_code, from_date, to_date)
        selling_amount = item.get('selling_amount', 0)
        item['gross_profit'] = selling_amount - buying_amount
        item['gross_profit_percentage'] = calculate_gross_profit_percentage(
            item['gross_profit'], selling_amount)

        # Include the valuation rate
        item['valuation_rate'] = get_valuation_rate_from_sle(
            item_code, from_date, to_date)

        if item_code not in item_dict:
            item_dict[item_code] = item
        else:
            item_dict[item_code]['qty'] += item['qty']

        data.append(item)

    return data


def calculate_qty_in_chosen_uom(item_code, qty, chosen_uom, sales_invoice_uom):
    calculated_qty = qty

    if chosen_uom != sales_invoice_uom:
        conversion_factor = get_conversion_factor(item_code, chosen_uom)

        if chosen_uom == "Kg":
            # If the chosen unit of measure is Kgs, calculate the quantity from the existing quantity

            calculated_qty = qty
        if chosen_uom == "Bag" and sales_invoice_uom == "Kg":
            calculated_qty = qty / 25
        elif conversion_factor:

            # If there is a conversion factor, use it to calculate the quantity
            calculated_qty = qty / conversion_factor

    return calculated_qty


def get_conversion_factor(item_code, chosen_uom):
   # Get the conversion factor from the UOM Conversion Detail table
    conversion_factor = frappe.get_value("UOM Conversion Detail",
                                         {"parent": item_code, "uom": chosen_uom},
                                         "conversion_factor")

    if not conversion_factor:
        conversion_factor = 1.0  # If no conversion factor is found, default to 1

    # print(str(conversion_factor))

    return conversion_factor


def get_query(filters):
    sql_query = """
    SELECT
        si_item.item_code AS item_code,
        si_item.item_group AS item_group,
        si_item.stock_uom AS default_uom,
        si_item.uom AS uom_required,
        
        SUM(si_item.stock_qty) AS qty,
        SUM(si_item.base_amount) AS selling_amount,
        
        SUM(si_item.base_amount)/SUM(si_item.stock_qty) AS average_selling_rate
        
    FROM
        `tabSales Invoice Item` si_item
    INNER JOIN
        `tabSales Invoice` si ON si_item.parent = si.name
   
    WHERE
        si.docstatus = 1
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


def get_buying_amount(item_code, qty, from_date, to_date):
    # Get the valuation rate from the ledger using the item_code
    valuation_rate = get_valuation_rate_from_sle(item_code, from_date, to_date)

    # Calculate the buying amount by multiplying valuation rate and quantity
    buying_amount = valuation_rate * qty

    return buying_amount


# def get_valuation_rate_from_sle(item_code):
#     sle_entries = frappe.get_all("Stock Ledger Entry",
#                                  filters={"item_code": item_code},
#                                  fields=["valuation_rate"],
#                                  order_by="posting_date DESC",
#                                  limit_page_length=1)

#     valuation_rate = sle_entries[0].get(
#         "valuation_rate") if sle_entries else 0.0
#     return flt(valuation_rate)


def get_last_purchase_rate(item_code):
    purchase_invoice = frappe.qb.DocType("Purchase Invoice")
    purchase_invoice_item = frappe.qb.DocType("Purchase Invoice Item")

    query = (
        frappe.qb.from_(purchase_invoice_item)
        .inner_join(purchase_invoice)
        .on(purchase_invoice.name == purchase_invoice_item.parent)
        .select(purchase_invoice_item.base_rate / purchase_invoice_item.conversion_factor)
        .where(purchase_invoice.docstatus == 1)
        # .where(purchase_invoice.posting_date <= self.filters.to_date)
        .where(purchase_invoice_item.item_code == item_code)
    )

    query.orderby(purchase_invoice.posting_date, order=frappe.qb.desc)
    query.limit(1)
    last_purchase_rate = query.run()

    return flt(last_purchase_rate[0][0]) if last_purchase_rate else 0.0


def get_valuation_rate_from_sle(item_code, from_date, to_date):
    filters = {
        "item_code": item_code,
        "docstatus": 1,  # To filter for completed documents
        "is_cancelled": 0,
        "voucher_type": "Delivery Note"

    }

    if from_date:
        filters["posting_date"] = (">=", from_date)

    if to_date:
        if "posting_date" in filters:
            filters["posting_date"] = (">=", from_date, "<=", to_date)
        else:
            filters["posting_date"] = ("<=", add_days(to_date, 1))

    sle_entries = frappe.get_all("Stock Ledger Entry",
                                 filters=filters,
                                 fields=["valuation_rate", "voucher_no", "voucher_type"])

    approved_valuation_rates = []

    for entry in sle_entries:
        voucher_no = entry.get("voucher_no")
        voucher_type = entry.get("voucher_type")

        if voucher_no and voucher_type:
            voucher_status = frappe.get_value(
                voucher_type, voucher_no, "docstatus")
            if voucher_status == 1:
                valuation_rate = flt(entry.get("valuation_rate"))
                if valuation_rate != 0.0:
                    approved_valuation_rates.append(valuation_rate)

    if approved_valuation_rates:

        average_valuation_rate = sum(
            approved_valuation_rates) / len(approved_valuation_rates)
        return flt(average_valuation_rate)
    else:
        return 0.0


def get_valuation_change_sum(item_code, from_date, to_date):

    sql_query = """
        SELECT si.posting_date
        FROM `tabSales Invoice` AS si
        WHERE si.name IN (
            SELECT sii.parent
            FROM `tabSales Invoice Item` AS sii
            WHERE sii.item_code = %(item_code)s AND si.docstatus = 1
            AND si.posting_date >= %(from_date)s AND si.posting_date <= %(to_date)s
        )
    """

    sales_invoices = frappe.db.sql(
        sql_query, {"item_code": item_code, "from_date": from_date, "to_date": to_date}, as_dict=True)

    # frappe.msgprint(str(sales_invoices))
    for sales_invoice in sales_invoices:
        sales_invoice_posting_date = sales_invoice.get("posting_date")
        # add logic here to compare the Sales Invoice posting date with other criteria as needed.
        # frappe.msgprint(str(sales_invoice_posting_date))
    filters = {
        "item_code": item_code,
        "docstatus": 1,
        "is_cancelled": 0,
    }

    if from_date:
        filters["posting_date"] = (">=", from_date)

    if to_date:
        if "posting_date" in filters:
            filters["posting_date"] = (">=", from_date, "<=", to_date)
        else:
            filters["posting_date"] = ("<=", add_days(to_date, 1))

    sle_entries = frappe.get_all("Stock Ledger Entry",
                                 filters=filters,
                                 fields=["stock_value_difference as valuation_change", "voucher_no", "voucher_type", "item_code"])
    valuation_change_sum = 0.0

    for entry in sle_entries:
        voucher_no = entry.get("voucher_no")
        new_item_code = entry.get("item_code")
        delivery_note = frappe.db.get_all(
            "Delivery Note", filters={"name": voucher_no}, fields=["posting_date"])
        # frappe.msgprint(str(new_item_code))

        valuation_change = flt(entry.get("valuation_change"))
        if valuation_change != 0.0:
            valuation_change_sum += valuation_change

    # frappe.msgprint(str(item_code) + ":" + str(valuation_change_sum))
    return flt(valuation_change_sum)


# def get_valuation_rate_from_sle(item_code, from_date, to_date):
#     filters = {
#         "item_code": item_code,
#         "docstatus": 1, "is_cancelled": 0,
#     }

#     if from_date:
#         filters["posting_date"] = (">=", from_date)

#     if to_date:
#         if "posting_date" in filters:
#             filters["posting_date"] = (">=", from_date, "<=", to_date)
#         else:
#             filters["posting_date"] = ("<=", add_days(to_date, 1))

#     sle_entries = frappe.get_all("Stock Ledger Entry",
#                                  filters=filters,
#                                  fields=["valuation_rate"])
#     # frappe.msgprint(str(item_code)+str(sle_entries))
#     # frappe.msgprint(str(len(sle_entries)))
#     valuation_rates = [flt(entry.get("valuation_rate"))
#                        for entry in sle_entries if entry.get("valuation_rate") != 0.0]

#     if valuation_rates:
#         frappe.msgprint(str(sum(valuation_rates)))
#         average_valuation_rate = sum(valuation_rates) / len(valuation_rates)
#         return flt(average_valuation_rate)
#     else:
#         return 0.0
