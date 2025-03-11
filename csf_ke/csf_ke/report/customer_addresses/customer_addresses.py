
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
        .inner_join(User)
        .on(User.name == Customer.account_manager)
        .left_join(DynamicLink)
        .on((DynamicLink.link_name == Customer.name) & (DynamicLink.link_doctype == "Customer"))
        .left_join(Address)
        .on(Address.name == DynamicLink.parent)
        .select(
            User.full_name.as_("Account Manager"),
            User.name.as_("Account Manager ID"),
            Customer.name.as_("Customer Name"),
            Customer.customer_group.as_("Customer Group"),
            Address.name.as_("Address ID"),
            Address.address_title.as_("Address Title"),
            Address.address_type.as_("Address Type"),
            Address.address_line1.as_("Address Line 1"),
            Address.address_line2.as_("Address Line 2"),
            Address.city.as_("City"),
            Address.country.as_("Country"),
            Address.email_id.as_("Email ID"),
            Address.phone.as_("Phone"),
        )
        .where(Customer.account_manager.isnotnull())
    )
    
    if filters.get("account_manager"):
        query = query.where(User.name == filters["account_manager"])
    
    if filters.get("customer_name"):
        query = query.where(Customer.name.like(f"%{filters['customer_name']}%"))
        
    if filters.get("customer_group"):
        query = query.where(Customer.customer_group == filters["customer_group"])
    
    query = query.orderby(User.full_name).orderby(Customer.name).orderby(Address.name)

    try:
        data = query.run(as_dict=True)
    except Exception as e:
        frappe.log_error(f"Error fetching report data: {e}")
        return [], []
    
    account_manager_map = defaultdict(lambda: defaultdict(list))
    for row in data:
        customer_name = row["Customer Name"]
        if not row["Address ID"] and any(d["Customer Name"] == customer_name and d["Address ID"] for d in data):
            continue
        
        account_manager = row["Account Manager"]
        account_manager_id = row["Account Manager ID"]
        address_info = {
            "Address Title": row["Address Title"] or "",
            "Address Type": row["Address Type"] or "",
            "Address Line 1": row["Address Line 1"] or "",
            "Address Line 2": row["Address Line 2"] or "",
            "City": row["City"] or "",
            "Country": row["Country"] or "",
            "Email ID": row["Email ID"] or "",
            "Phone": row["Phone"] or "",
        }
        
        account_manager_map[account_manager][customer_name].append((account_manager_id, address_info))
    
    final_data = []
    for account_manager, customers in account_manager_map.items():
        first_customer = next(iter(customers.keys()), "")
        for customer_name, addresses in customers.items():
            first_address = addresses[0][1] if addresses else {}
            account_manager_id = addresses[0][0] if addresses else ""
            
            final_data.append({
                "Account Manager": f'<a href="/app/user/{account_manager_id}">{account_manager}</a>' if customer_name == first_customer else "",
                "Customer Name": customer_name,
                "Address Title": first_address.get("Address Title", ""),
                "Address Type": first_address.get("Address Type", ""),
                "Address Line 1": first_address.get("Address Line 1", ""),
                "Address Line 2": first_address.get("Address Line 2", ""),
                "City": first_address.get("City", ""),
                "Country": first_address.get("Country", ""),
                "Email ID": first_address.get("Email ID", ""),
                "Phone": first_address.get("Phone", ""),
            })
            
            for address in addresses[1:]:
                final_data.append({
                    "Account Manager": "",
                    "Customer Name": "",
                    "Address Title": address[1]["Address Title"],
                    "Address Type": address[1]["Address Type"],
                    "Address Line 1": address[1]["Address Line 1"],
                    "Address Line 2": address[1]["Address Line 2"],
                    "City": address[1]["City"],
                    "Country": address[1]["Country"],
                    "Email ID": address[1]["Email ID"],
                    "Phone": address[1]["Phone"],
                })
    
    columns = [
        {"fieldname": "Account Manager", "label": "Account Manager", "fieldtype": "Data", "width": 250},
        {"fieldname": "Customer Name", "label": "Customer", "fieldtype": "Link", "options": "Customer", "width": 250},
        {"fieldname": "Address Title", "label": "Address Title", "fieldtype": "Data", "width": 200},
        {"fieldname": "Address Type", "label": "Address Type", "fieldtype": "Data", "width": 200},
        {"fieldname": "Address Line 1", "label": "Address Line 1", "fieldtype": "Data", "width": 200},
        {"fieldname": "Address Line 2", "label": "Address Line 2", "fieldtype": "Data", "width": 200},
        {"fieldname": "City", "label": "City", "fieldtype": "Data", "width": 200},
        {"fieldname": "Country", "label": "Country", "fieldtype": "Data", "width": 200},
        {"fieldname": "Email ID", "label": "Email ID", "fieldtype": "Data", "width": 200},
        {"fieldname": "Phone", "label": "Phone", "fieldtype": "Data", "width": 200},
    ]
    
    return columns, final_data
