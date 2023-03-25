# # Copyright (c) 2023, Navari Limited and contributors
# # For license information, please see license.txt

import frappe
from frappe import _
    
def execute(filters=None):
    if filters.from_date > filters.to_date:
        frappe.throw(_('From Date cannot be greater than To Date'))

    return _execute(filters)

def _execute(filters):
    company, from_date, to_date, stock_request_from, item = filters.get('company'), filters.get('from_date'), filters.get('to_date'), filters.get('stock_request_from'), filters.get('item')
    # use to keep track of branches and count for each item's  branch_target_qty/actual_qty_at_lc/allocated_qty/qty(ordered qty)
    seen = {}

    data = []

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
            'width': '200px'
        },
        {
            'label': "",
            'width': '100px'
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

    conditions = " AND 1=1 "
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
                               fields = ['warehouse', 'item_code', 'allocated_qty', 'qty', 'default_lc_warehouse']     
                            # , ,        
                            )
            if(review_items):
                stock_order_review_items += review_items

    
    # Parent warehouses, the very top. Indent zero, makes them top on the tree
    for warehouse in warehouses:
        warehouse['indent'] = 0

    # add child warehouses, indent respoctive of position from parent warehouse.
    for warehouse in warehouses:
        if warehouse['indent'] > 0:
            warehouse['totals_warehouse'] = frappe.db.get_value('Warehouse', warehouse['name'], 'parent_warehouse')

        if warehouse['is_group']:
            data.append({ 'warehouse': warehouse['name'], 'indent': warehouse['indent'], 'totals_warehouse': warehouse.get('totals_warehouse'), 'allocated_qty': 0, 'qty': 0, 'actual_qty_at_lc': 0, 'branch_target_qty': 0 })
            insert_index = warehouses.index(warehouse) + 1 
            # warehouse has children. Get children.
            temp_warehouses = frappe.db.get_all('Warehouse', filters = { 'parent_warehouse': warehouse['name'], 'warehouse_type': ['in', ['Branch', 'Region', 'SubRegion', 'LC']] }, fields = [ 'name', 'is_group'])
            for temp_warehouse in temp_warehouses:
                temp_warehouse['indent'] = warehouse['indent'] + 1
            # append children immediately after parent warehouse. Useful when building tree later.
            warehouses[ insert_index:insert_index ] = temp_warehouses
        else:
            data.append({ 'warehouse': warehouse['name'], 'indent': warehouse['indent'], 'totals_warehouse': warehouse.get('totals_warehouse'), 'allocated_qty': 0, 'qty': 0, 'actual_qty_at_lc': 0, 'branch_target_qty': 0 })

    warehouse_names = list(map(lambda warehouse: warehouse['name'], warehouses))
    for warehouse in warehouse_names:
        for stock_item in stock_order_review_items:
            if stock_item['warehouse'] == warehouse:
                item_code = stock_item['item_code']
                default_lc_warehouse = stock_item['default_lc_warehouse']
                if seen.get(warehouse):
                    if seen.get(warehouse).get(item_code):
                        seen[warehouse][item_code]['allocated_qty'] += stock_item['allocated_qty']
                        seen[warehouse][item_code]['qty'] += stock_item['qty']
                    else:
                        seen[warehouse][item_code] = {}
                        seen[warehouse][item_code]['allocated_qty'] = stock_item['allocated_qty']
                        seen[warehouse][item_code]['qty'] = stock_item['qty']
                        seen[warehouse][item_code]['branch_target_qty'] = get_branch_target_qty(warehouse)
                        seen[warehouse][item_code]['actual_qty_at_lc'] = frappe.db.sql(f"SELECT SUM(actual_qty) FROM tabBin WHERE item_code = '{item_code}' AND warehouse = '{default_lc_warehouse}'", as_list=True)[0][0]
                else:
                    seen[warehouse] = {}
                    seen[warehouse][item_code] = {}
                    seen[warehouse][item_code]['allocated_qty'] = stock_item['allocated_qty']
                    seen[warehouse][item_code]['qty'] = stock_item['qty']
                    seen[warehouse][item_code]['branch_target_qty'] = get_branch_target_qty(warehouse)
                    seen[warehouse][item_code]['actual_qty_at_lc'] = frappe.db.sql(f"SELECT SUM(actual_qty) FROM tabBin WHERE item_code = '{item_code}' AND warehouse = '{default_lc_warehouse}'", as_list=True)[0][0]

    warehouses_with_orders = list(seen.keys())
    
    for row in data:
        if row['warehouse'] in warehouses_with_orders:
            # pick all items for a particular warehouse
            items = seen.get(row['warehouse'])

            for item_code in items:
                # if we have the user filtering through items
                if item:
                    # item code does not match in this iteration, skip
                    if item_code != item:
                        continue
                    else:
                        # continue with execution flow
                        pass

                # set some additional keys and values to the dict we are going to append to 'data'
                items[item_code]['item_name'] = item_code
                items[item_code]['indent'] = row['indent'] + 1
                items[item_code]['warehouse'] = ''

                # sum ordered qty for the whole branch
                row['qty'] += items[item_code]['qty']

                # sum allocated_qty for the whole branch
                row['allocated_qty'] += items[item_code]['allocated_qty']

                # branch target qry is just the same, no need to keep changing/adding on every loop
                if not row['branch_target_qty']:
                    row['branch_target_qty'] = items[item_code]['branch_target_qty']

                # total qty available at LC, for the ordered items
                actual_qty_at_lc = items[item_code]['actual_qty_at_lc'] if items[item_code]['actual_qty_at_lc'] else 0
                row['actual_qty_at_lc'] += actual_qty_at_lc

                insert_index = data.index(row) + 1
                data.insert(insert_index, items[item_code])

            totals_row = list(filter(lambda x: x['warehouse'] == row['totals_warehouse'], data))
            while totals_row:
                totals_row = totals_row[0]
                totals_row['qty'] += row['qty']
                totals_row['allocated_qty'] += row['allocated_qty']
                totals_row['branch_target_qty'] += row['branch_target_qty']
                totals_row['actual_qty_at_lc'] += row['actual_qty_at_lc']
                totals_row = list(filter(lambda x: x['warehouse'] == totals_row['totals_warehouse'], data))
        
    return columns, data

# Branch Target Quantity
def get_branch_target_qty(branch_name):
    result = frappe.db.get_all('Branch Target Item', 
                filters = { 'target_warehouse': branch_name },
                pluck = 'target_qty'
            )
    
    return result[0] if result else 0


