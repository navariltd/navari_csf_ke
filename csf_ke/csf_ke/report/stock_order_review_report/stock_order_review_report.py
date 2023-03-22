# # Copyright (c) 2023, Navari Limited and contributors
# # For license information, please see license.txt

import frappe
from frappe import _
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_stock_balance_for

    
def execute(filters=None):
    if filters.from_date > filters.to_date:
        frappe.throw(_('From Date cannot be greater than To Date'))
         
    return _execute(filters)

def _execute(filters):
    company, from_date, to_date, warehouse, item = filters.get('company'), filters.get('from_date'), filters.get('to_date'), filters.get('warehouse'), filters.get('item')
    warehouses = [warehouse['name'] for warehouse in get_warehouses(warehouse)]
    
    conditions = " AND 1=1 "
    if(company):
        conditions += f" AND sor.company = '{company}'"
    
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
                               fields = ['warehouse', 'item_code', 'allocated_qty', 'qty', 'branch_target_qty', 'actual_qty_at_lc', 'default_lc_warehouse']            
                            )
            if(review_items):
                stock_order_review_items += review_items

    items = { item } if item else set([stock_order_review_item['item_code'] for stock_order_review_item in stock_order_review_items])
    
    columns = [
        {
			'fieldname': 'warehouse',
			'label': _('Warehouse/Branch'),
			'fieldtype': 'Link',
			'options': 'Warehouse',
            'width': '200px'
		},
        {
            'fieldname': 'item_name',
            'label': 'Item',
            'fieldtype': 'Data',
            'options': 'bold',
            'width': '200px'
        },
		{
			'fieldname': 'qty',
			'label': _('Requested Qty'),
			'fieldtype': 'Int'
		},
		{
			'fieldname': 'allocated_qty',
			'label': _('Allocated Qty'),
			'fieldtype': 'Int'
		},
		{
			'fieldname': 'branch_target_qty',
			'label': _('Branch Target Qty'),
			'fieldtype': 'Float'
		},
        {
			'fieldname': 'actual_qty_at_lc',
            'label': _('Actual Qty At LC'),
            'fieldtype': 'Float'
		}
    ]

    data = []

    for item in items:
        data.append({"item_name": f"<b>{item}</b>"})
        seen_items = {}
        for stock_order_review_item in stock_order_review_items:
            if stock_order_review_item["warehouse"] in warehouses:
                if stock_order_review_item["item_code"] == item:
                    if not seen_items.get(stock_order_review_item['warehouse']):
                        seen_items[stock_order_review_item['warehouse']] = stock_order_review_item
                    else:
                        seen_items.get(stock_order_review_item['warehouse'])['qty'] += stock_order_review_item['qty']
                        seen_items.get(stock_order_review_item['warehouse'])['allocated_qty'] += stock_order_review_item['allocated_qty']
                        seen_items.get(stock_order_review_item['warehouse'])['branch_target_qty'] = 0
                        seen_items.get(stock_order_review_item['warehouse'])['actual_qty_at_lc'] = 0
        if(seen_items):
            for seen_item in seen_items:
                seen_items[seen_item]['branch_target_qty'] =  get_branch_target_qty(seen_item)
                item_code = seen_items[seen_item]['item_code']
                warehouse = seen_items[seen_item]['default_lc_warehouse']
                seen_items[seen_item]['actual_qty_at_lc'] = frappe.db.sql(f"SELECT SUM(actual_qty) FROM tabBin WHERE item_code = '{item_code}' AND warehouse = '{warehouse}'", as_list=True)[0][0]
                data += [seen_items[seen_item]]
        data.append({"separator": True})
    
    return columns, data

def get_warehouses(warehouse):
    warehouse_obj =  { 'name': warehouse, 'parent_warehouse': frappe.db.get_value('Warehouse', warehouse, 'parent_warehouse') }
    
    def get_final_warehouse_list(warehouse_list):
        final_warehouse_list = []
          
        def check_is_group(warehouse):
            return frappe.db.get_value('Warehouse', warehouse, 'is_group')
          
        for warehouse in warehouse_list:
            if not check_is_group(warehouse['name']):
                final_warehouse_list.append(warehouse)
            else:
                fetched_warehouses = frappe.db.get_all('Warehouse', 
                                            filters = {
                                                'parent_warehouse': warehouse['name']
                                            }
                                    )
                warehouse_list.extend(fetched_warehouses) 
        return final_warehouse_list

    final_warehouse_list = get_final_warehouse_list([ warehouse_obj ])

    return final_warehouse_list

def get_branch_target_qty(branch_name):
    result = frappe.db.get_all('Branch Target Item', 
                filters = { 'target_warehouse': branch_name },
                pluck = 'target_qty'
            )
    return result[0]
