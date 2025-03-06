# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.query_builder import DocType
from collections import defaultdict

def execute(filters=None):
    filters = frappe._dict(filters or {})
    
    Customer = DocType("Customer")
    Address = DocType("Address")
    DynamicLink = DocType("Dynamic Link")
    User = DocType("User")
    
    query = (
        frappe.qb.from_(Customer)
        .left_join(User)
        .on(User.name == Customer.account_manager)
        .left_join(DynamicLink)
        .on((DynamicLink.link_name == Customer.name) & (DynamicLink.link_doctype == "Customer"))
        .left_join(Address)
        .on(Address.name == DynamicLink.parent)
        .select(
            User.full_name.as_("Account Manager"),
            Customer.name.as_("Customer Name"),
            Address.address_title.as_("Address Title"),
            Address.address_type.as_("Address Type"),
            Address.address_line1.as_("Address Line 1"),
            Address.address_line2.as_("Address Line 2"),
            Address.city.as_("City"),
            Address.country.as_("Country"),
            Address.email_id.as_("Email ID"),
            Address.phone.as_("Phone"),
        )
    )
    
    if filters.get("account_manager"):
        query = query.where(User.name == filters["account_manager"])
    
    if filters.get("customer_name"):
        query = query.where(Customer.name.like(f"%{filters['customer_name']}%"))
    
    query = query.orderby(User.full_name).orderby(Customer.name).orderby(Address.address_title, order=frappe.qb.asc)
    
    data = query.run(as_dict=True)
    
    final_data = []
    for row in data:
        final_data.append({
            "Account Manager": row.get("Account Manager") or "",
            "Customer Name": row.get("Customer Name"),
            "Address Title": row.get("Address Title") or "",
            "Address Type": row.get("Address Type") or "",
            "Address Line 1": row.get("Address Line 1") or "",
            "Address Line 2": row.get("Address Line 2") or "",
            "City": row.get("City") or "",
            "Country": row.get("Country") or "",
            "Email ID": row.get("Email ID") or "",
            "Phone": row.get("Phone") or "",
        })
    
    seen = set()
    deduped_data = []
    for row in final_data:
        key = (
            row["Account Manager"],
            row["Customer Name"],
            row["Address Title"],
            row["Address Type"],
            row["Address Line 1"],
            row["Address Line 2"],
            row["City"],
            row["Country"],
            row["Email ID"],
            row["Phone"]
        )
        if key not in seen:
            seen.add(key)
            deduped_data.append(row)
    
    grouped = defaultdict(list)
    for row in deduped_data:
        grouped[row["Customer Name"]].append(row)
    
    final_filtered_data = []
    for customer, rows in grouped.items():
        rows_with_address = [r for r in rows if any([
            r["Address Title"],
            r["Address Type"],
            r["Address Line 1"],
            r["Address Line 2"],
            r["City"],
            r["Country"],
            r["Email ID"],
            r["Phone"],
        ])]
        if rows_with_address:
            final_filtered_data.extend(rows_with_address)
        else:
            final_filtered_data.append(rows[0])
    
    def sort_key(row):
        manager_sort = 0 if row["Account Manager"] else 1
        address_exists = any([
            row["Address Title"],
            row["Address Type"],
            row["Address Line 1"],
            row["Address Line 2"],
            row["City"],
            row["Country"],
            row["Email ID"],
            row["Phone"],
        ])
        address_sort = 0 if address_exists else 1
        return (manager_sort, row["Account Manager"], row["Customer Name"], address_sort, row["Address Title"])
    
    final_filtered_data.sort(key=sort_key)
    
    columns = [
        {"fieldname": "Customer Name", "label": "Customer Name", "fieldtype": "Data", "width": 250},
        {"fieldname": "Address Title", "label": "Address Title", "fieldtype": "Data", "width": 200},
        {"fieldname": "Address Type", "label": "Address Type", "fieldtype": "Data", "width": 200},
        {"fieldname": "Address Line 1", "label": "Address Line 1", "fieldtype": "Data", "width": 200},
        {"fieldname": "Address Line 2", "label": "Address Line 2", "fieldtype": "Data", "width": 200},
        {"fieldname": "City", "label": "City", "fieldtype": "Data", "width": 200},
        {"fieldname": "Country", "label": "Country", "fieldtype": "Data", "width": 200},
        {"fieldname": "Email ID", "label": "Email ID", "fieldtype": "Data", "width": 200},
        {"fieldname": "Phone", "label": "Phone", "fieldtype": "Data", "width": 200},
        {"fieldname": "Account Manager", "label": "Account Manager", "fieldtype": "Data", "width": 250},
    ]
    
    return columns, final_filtered_data
