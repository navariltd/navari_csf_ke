# Copyright (c) 2023, Navari Limited and contributors
# For license information, please see license.txt

# import frappe

from frappe import get_all, get_value
from frappe import get_all, qb
from frappe.utils import flt

from frappe import _
import frappe
from frappe.utils import flt, getdate, comma_and, cstr


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

# ... (Rest of the code remains the same)


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
            "width": 120
        },
        {
            "label": "Default UOM",
            "fieldname": "default_uom",
            "fieldtype": "Link",
            "options": "UOM",
            "width": 120
        },
        {
            "label": "UOM Required",
            "fieldname": "uom_required",
            "fieldtype": "Data",
            "width": 100
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
            "width": 120
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


def calculate_gross_profit_percentage(gross_profit, buying_amount):
    gross_profit = float(gross_profit) if gross_profit is not None else 0.0
    buying_amount = float(buying_amount) if buying_amount is not None else 0.0

    if buying_amount != 0.0:
        return (gross_profit / buying_amount) * 100
    else:
        return 100.0  # Avoid division by zero


def get_data(filters):
    data = []
    query = get_query(filters)
    currency_precision = 3

    primary_data = frappe.db.sql(query, as_dict=True)
    item_dict = {}

    for item in primary_data:
        item_code = item.get('item_code')

        # Calculate the quantity in the chosen UOM
        chosen_uom = filters.get('item_group')
        frappe.msgprint(str(chosen_uom))
        item['qty_uom'] = calculate_qty_in_chosen_uom(
            item_code, item['qty'], chosen_uom, item['default_uom'])

        # Recalculate the buying amount using the updated quantity
        buying_amount = calculate_buying_amount(
            item_code, filters)
        item['buying_amount'] = buying_amount

        selling_amount = item.get('selling_amount', 0)
        item['gross_profit'] = selling_amount - buying_amount
        item['gross_profit_percentage'] = calculate_gross_profit_percentage(
            item['gross_profit'], buying_amount)

        if item_code not in item_dict:
            item_dict[item_code] = item
        else:
            item_dict[item_code]['qty'] += item['qty']

        data.append(item)
        # frappe.msgprint("Rada"+str(data))

    return data


def calculate_qty_in_chosen_uom(item_code, qty, chosen_uom, sales_invoice_uom):
    if chosen_uom == sales_invoice_uom:
        # If the chosen UOM matches the UOM of the sales invoice, return the existing quantity

        return qty
    else:
        frappe.msgprint("Nothing")
        # Use the UOM conversion data to calculate the quantity in the chosen UOM
        conversion_factor = get_conversion_factor(item_code, chosen_uom)

        if chosen_uom == "Kg":
            # If the chosen unit of measure is Kgs, return the existing quantity
            return qty
        elif chosen_uom == "Bag":
            # If the chosen unit of measure is Bags, multiply by 0.04 to get Kgs
            return qty * 0.04
        elif conversion_factor:
            # If there is a conversion factor, use it to calculate the quantity
            return qty * conversion_factor
        else:
            # If no conversion factor is found, just return the quantity as it is
            return qty


def get_conversion_factor(item_code, chosen_uom):
   # Get the conversion factor from the UOM Conversion Detail table
    conversion_factor = frappe.get_value("UOM Conversion Detail",
                                         {"parent": item_code, "uom": chosen_uom},
                                         "conversion_factor")

    if not conversion_factor:
        conversion_factor = 1.0  # If no conversion factor is found, default to 1

    # frappe.msgprint(str(conversion_factor))

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

    if filters.get("uom"):
        conditions.append(f"si_item.uom = '{filters.get('uom')}'")

    if conditions:
        sql_query += " AND " + " AND ".join(conditions)

    sql_query += """
        GROUP BY
            si_item.item_code, si_item.item_group, si_item.stock_uom, si_item.uom
    """
    return sql_query

# Calculate buying_amount based on various factors


def calculate_buying_amount(item_code, filters):
    buying_amount = 0.0
    is_stock_item = frappe.get_value('Item', item_code, 'is_stock_item')
    last_purchase_rate = 0  # Initialize to 0 by default

    if is_stock_item:
        last_purchase_rate = get_last_purchase_rate(
            item_code, filters.get('to_date'))

    if last_purchase_rate:
        # If a valid last_purchase_rate is available, use this method
        sle = get_stock_ledger_entries(item_code, filters)
        for entry in sle:
            qty = entry.get('actual_qty', 0)  # Handle None as 0
            buying_amount += qty * last_purchase_rate
    else:
        # If last_purchase_rate is not available, use the alternative method
        sle = get_stock_ledger_entries(item_code, filters)
        for entry in sle:
            buying_amount += calculate_buying_amount_from_sle(entry, item_code)

    return buying_amount


def get_stock_ledger_entries(item_code, filters):
    sle = frappe.get_all('Stock Ledger Entry', filters={
        'item_code': item_code,

        'posting_date': ['>=', filters.get('from_date')],
        'posting_date': ['<=', filters.get('to_date')]
    }, fields=['actual_qty'])

    return sle


def get_last_purchase_rate(item_code, to_date):
    purchase_invoice_item = qb.DocType("Purchase Invoice Item")
    purchase_invoice = qb.DocType("Purchase Invoice")

    query = (
        qb.from_(purchase_invoice_item)
        .inner_join(purchase_invoice)
        .on(purchase_invoice_item.parent == purchase_invoice.name)
        .select(purchase_invoice_item.base_rate / purchase_invoice_item.conversion_factor)
        .where(purchase_invoice.docstatus == 1)
        .where(purchase_invoice.posting_date <= to_date)
        .where(purchase_invoice_item.item_code == item_code)
        .orderby(purchase_invoice.posting_date, order=qb.desc)
        .limit(1)
    )

    last_purchase_rate = query.run()
    return flt(last_purchase_rate[0][0]) if last_purchase_rate else 0


def calculate_buying_amount_from_sle(sle, item_code):
    previous_stock_value = 0.0
    sle_stock_value = 0.0 if sle.stock_value is None else sle.stock_value
    sle_qty = 0.0 if sle.qty is None else sle.qty
    sle_actual_qty = 0.0 if sle.actual_qty is None else sle.actual_qty

    # Calculate the previous stock value if available
    previous_sle = get_previous_sle(sle, item_code)
    if previous_sle:
        previous_stock_value = previous_sle.get('stock_value', 0.0)

    if sle_actual_qty != 0:
        buying_amount = abs(previous_stock_value -
                            sle_stock_value) * sle_qty / abs(sle_actual_qty)
    else:
        buying_amount = sle_qty * \
            get_average_buying_rate(item_code, sle.posting_date)

    return buying_amount


def get_previous_sle(current_sle, item_code):
    # retrieve the previous entry
    previous_sle = frappe.get_all("Stock Ledger Entry",
                                  filters={
                                      "item_code": item_code,
                                      "posting_date": ("<", current_sle.get("posting_date")),
                                      # Adjust this condition based on your needs
                                      "stock_value": (">", 0)
                                  },
                                  fields=["stock_value", "actual_qty"],
                                  order_by="posting_date desc",
                                  limit_page_length=1
                                  )

    if previous_sle:
        return previous_sle[0]
    else:
        return {'stock_value': 0.0, 'actual_qty': 0.0}


def get_average_buying_rate(item_code, posting_date):
    # calculate the average rate
    average_rate = get_value("Stock Ledger Entry",
                             filters={
                                 "item_code": item_code,
                                 "posting_date": ("<=", posting_date)
                             },
                             fieldname=["avg(valuation_rate)"])

    return 0.0 if average_rate is None else average_rate[0][0]
