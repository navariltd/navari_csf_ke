# Copyright (c) 2023, Navari Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import math
    
def execute(filters=None):
    if filters.from_date > filters.to_date:
        frappe.throw(_('From Date cannot be greater than To Date'))
         
    return _execute(filters)

def _execute(filters):
    company, from_date, to_date, display_values, stock_request_from, item = filters.get('company'), filters.get('from_date'), filters.get('to_date'), filters.get('values'), filters.get('stock_request_from'), filters.get('item')
    data = []
    columns = [
        {
			'fieldname': 'warehouse',
			'label': _('Warehouse/Branch'),
			'fieldtype': 'Link',
			'options': 'Warehouse',
            'width': '200px'
		}
    ]

    conditions = " AND sor.docstatus = 1 "
    if(company):
        conditions += f" AND sor.company = '{company}'"

    warehouses = ''

    if stock_request_from == 'Branch Stock Request':
        warehouses = frappe.db.get_all('Warehouse', filters = { 'warehouse_type': 'SubRegion' }, fields = [ 'name', 'is_group', 'warehouse_type' ])
    elif stock_request_from == 'Region Stock Allocation':
        warehouses = frappe.db.get_all('Warehouse', filters = { 'warehouse_type': 'Region' }, fields = [ 'name', 'is_group', 'warehouse_type' ])

    stock_order_reviews = frappe.db.sql(f"""
        SELECT sor.name as "name"
        FROM `tabStock Order Review` as sor
        WHERE (sor.transaction_date BETWEEN '{from_date}' AND '{to_date}') {conditions}
    """, as_list = True)

    stock_order_review_items = []

    if stock_order_reviews:
        for stock_order_review in stock_order_reviews:
            review_items = frappe.db.get_all('Stock Order Review Item', 
                               filters = {
                                    'parent': stock_order_review[0]
                               },
                               fields = ['warehouse', 'item_code', 'allocated_qty', 'qty']            
                            )
            if(review_items):
                stock_order_review_items += review_items

    items = { item } if item else set([stock_order_review_item['item_code'] for stock_order_review_item in stock_order_review_items])

    if display_values == 'Branch Target Quantity':
        columns += [
            {
                'fieldname': 'branch_target_qty',
                'label': _('Branch Target Qty'),
                'fieldtype': 'Int'
            }
        ]
    else :    
        for item in items:
            columns += [
                {
                    'fieldname': item,
                    'label': _(item),
                    'fieldtype': 'Data',
                    'width': '200px'
                }
            ]
    
    # Parent warehouses, the very top.
    for warehouse in warehouses:
        warehouse['indent'] = 0

    for warehouse in warehouses:
        if warehouse['indent'] > 0:
            warehouse['totals_warehouse'] = frappe.db.get_value('Warehouse', warehouse['name'], 'parent_warehouse')

        if warehouse['is_group']:
            data.append({ 'warehouse': warehouse['name'], 'indent': warehouse['indent'], 'totals_warehouse': warehouse.get('totals_warehouse') })
            insert_index = warehouses.index(warehouse) + 1 
            # warehouse has children. Get children.
            temp_warehouses = frappe.db.get_all('Warehouse', filters = { 'parent_warehouse': warehouse['name'], 'warehouse_type': ['in', ['Branch', 'Region', 'SubRegion', 'LC']] }, fields = [ 'name', 'is_group'])
            for temp_warehouse in temp_warehouses:
                temp_warehouse['indent'] = warehouse['indent'] + 1
            # append children immediately after parent warehouse. Useful when building tree later.
            warehouses[ insert_index:insert_index ] = temp_warehouses
        else:
            data.append({ 'warehouse': warehouse['name'], 'indent': warehouse['indent'], 'totals_warehouse': warehouse.get('totals_warehouse') })

    if display_values == 'Branch Target Quantity':
        for row in data:
            target_qty = get_branch_target_qty(row['warehouse'])
            target_qty = math.ceil(target_qty / 25)
            row['branch_target_qty'] = target_qty

            totals_row = list(filter(lambda item: item['warehouse'] == row['totals_warehouse'], data))
            # long as there is a parent warehouse, keep totaling
            while totals_row:
                totals_row = totals_row[0]
                totals_row['branch_target_qty'] += row['branch_target_qty']
                totals_row = list(filter(lambda item: item['warehouse'] == totals_row['totals_warehouse'], data))
    elif display_values == 'Actual Quantity At LC':
        for row in data:
            default_lc_warehouse = frappe.db.get_value('Warehouse', row['warehouse'], 'default_lc_warehouse')
            for item in items:
                actual_qty_at_lc = frappe.db.sql(f"SELECT SUM(actual_qty) FROM tabBin WHERE item_code = '{item}' AND warehouse = '{default_lc_warehouse}'", as_list=True)[0][0]
                actual_qty_at_lc = math.ceil(actual_qty_at_lc / 25) if actual_qty_at_lc else 0
                row[item] = actual_qty_at_lc
    elif display_values == 'Allocated Quantity':
        for row in data:
            for item in items:
                row[item] = 0
                for stock_item in stock_order_review_items:
                    if row['warehouse'] == stock_item['warehouse'] and item == stock_item['item_code']:
                        row[item] += stock_item['allocated_qty']
                        totals_row = list(filter(lambda item: item['warehouse'] == row['totals_warehouse'], data))
                        while totals_row:
                            totals_row = totals_row[0]
                            totals_row[item] += stock_item['allocated_qty']
                            totals_row = list(filter(lambda item: item['warehouse'] == totals_row['totals_warehouse'], data))
    elif display_values == 'Requested Quantity':
        for row in data:
            for item in items:
                row[item] = 0
                for stock_item in stock_order_review_items:
                    if row['warehouse'] == stock_item['warehouse'] and item == stock_item['item_code']:
                        row[item] += stock_item['qty']
                        totals_row = list(filter(lambda item: item['warehouse'] == row['totals_warehouse'], data))
                        while totals_row:
                            totals_row = totals_row[0]
                            totals_row[item] += stock_item['qty']
                            totals_row = list(filter(lambda item: item['warehouse'] == totals_row['totals_warehouse'], data))

    return columns, data

# Branch Target Quantity
def get_branch_target_qty(branch_name):
    result = frappe.db.get_all('Branch Target Item', 
                filters = { 'target_warehouse': branch_name },
                pluck = 'target_qty'
            )
    
    return result[0] if result else 0
