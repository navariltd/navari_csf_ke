# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.query_builder import DocType
from collections import defaultdict

def execute(filters=None):
    filters = frappe._dict(filters or {})

    Customer = DocType("Customer")
    Contact = DocType("Contact")
    DynamicLink = DocType("Dynamic Link")
    User = DocType("User")

    query = (
        frappe.qb.from_(Customer)
        .inner_join(User)
        .on(User.name == Customer.account_manager)
        .left_join(DynamicLink)
        .on((DynamicLink.link_name == Customer.name) & (DynamicLink.link_doctype == "Customer"))
        .left_join(Contact)
        .on(Contact.name == DynamicLink.parent)
        .select(
            User.full_name.as_("Account Manager"),
            User.name.as_("Account Manager ID"),
            Customer.name.as_("Customer Name"),
            Customer.customer_group.as_("Customer Group"),
            Contact.name.as_("Contact ID"),
            Contact.first_name.as_("Contact First Name"),
            Contact.last_name.as_("Contact Last Name"),
        )
        .where(Customer.account_manager.isnotnull())
    )
    
    if filters.get("account_manager"):
        query = query.where(User.name == filters["account_manager"])
    
    if filters.get("customer_name"):
        query = query.where(Customer.name.like(f"%{filters['customer_name']}%"))
    
    if filters.get("customer_group"):
        query = query.where(Customer.customer_group == filters["customer_group"])
    
    query = query.orderby(User.full_name).orderby(Customer.name).orderby(Contact.name)

    try:
        data = query.run(as_dict=True)
    except Exception as e:
        frappe.log_error(f"Error fetching report data: {e}")
        return [], []
    
    contact_ids = [row["Contact ID"] for row in data if row["Contact ID"]]
    emails = frappe.get_all("Contact Email", filters={"parent": ["in", contact_ids]}, fields=["parent", "email_id"])
    phones = frappe.get_all("Contact Phone", filters={"parent": ["in", contact_ids]}, fields=["parent", "phone"])
    
    email_map = defaultdict(list)
    for email in emails:
        email_map[email["parent"]].append(email["email_id"])
    
    phone_map = defaultdict(list)
    for phone in phones:
        phone_map[phone["parent"]].append(phone["phone"])
    
    account_manager_map = defaultdict(lambda: defaultdict(list))
    for row in data:
        contact_id = row["Contact ID"]
        customer_name = row["Customer Name"]
        if not contact_id and any(d["Customer Name"] == customer_name and d["Contact ID"] for d in data):
            continue
        
        account_manager = row["Account Manager"]
        account_manager_id = row["Account Manager ID"]
        customer_name = row["Customer Name"]
        contact_id = row["Contact ID"]
        
        contact_info = {
            "Contact First Name": row["Contact First Name"] or "",
            "Contact Last Name": row["Contact Last Name"] or "",
            "Contact Email": ", ".join(email_map.get(contact_id, [])),
            "Contact Phone": ", ".join(phone_map.get(contact_id, [])),
        }
        
        account_manager_map[account_manager][customer_name].append(contact_info)
    
    final_data = []
    for account_manager, customers in account_manager_map.items():
        first_customer = next(iter(customers.keys()), "")
        for customer_name, contacts in customers.items():
            first_contact = contacts[0] if contacts else {}
            
            final_data.append({
                "Account Manager": f'<a href="/app/user/{account_manager_id}">{account_manager}</a>' if customer_name == first_customer else "",
                "Customer Name": customer_name,
                "Contact First Name": first_contact.get("Contact First Name", ""),
                "Contact Last Name": first_contact.get("Contact Last Name", ""),
                "Contact Email": first_contact.get("Contact Email", ""),
                "Contact Phone": first_contact.get("Contact Phone", ""),
            })
            
            for contact in contacts[1:]:
                final_data.append({
                    "Account Manager": "",
                    "Customer Name": "",
                    "Contact First Name": contact["Contact First Name"],
                    "Contact Last Name": contact["Contact Last Name"],
                    "Contact Email": contact["Contact Email"],
                    "Contact Phone": contact["Contact Phone"],
                })
    
    columns = [
        {"fieldname": "Account Manager", "label": "Account Manager", "fieldtype": "Data", "width": 250},
        {"fieldname": "Customer Name", "label": "Customer", "fieldtype": "Link", "options": "Customer", "width": 250},
        {"fieldname": "Contact First Name", "label": "Contact First Name", "fieldtype": "Data", "width": 200},
        {"fieldname": "Contact Last Name", "label": "Contact Last Name", "fieldtype": "Data", "width": 200},
        {"fieldname": "Contact Email", "label": "Contact Email(s)", "fieldtype": "Data", "width": 300},
        {"fieldname": "Contact Phone", "label": "Contact Phone(s)", "fieldtype": "Data", "width": 300},
    ]
    
    return columns, final_data
