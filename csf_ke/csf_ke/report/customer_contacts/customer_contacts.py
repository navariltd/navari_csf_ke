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
        .left_join(User)
        .on(User.name == Customer.account_manager)
        .left_join(DynamicLink)
        .on((DynamicLink.link_name == Customer.name) & (DynamicLink.link_doctype == "Customer"))
        .left_join(Contact)
        .on(Contact.name == DynamicLink.parent)
        .select(
            User.full_name.as_("Account Manager"),
            Customer.name.as_("Customer Name"),
            Contact.name.as_("Contact ID"),
            Contact.first_name.as_("Contact First Name"),
            Contact.last_name.as_("Contact Last Name"),
        )
    )
    
    if filters.get("account_manager"):
        query = query.where(User.name == filters["account_manager"])
    
    if filters.get("customer_name"):
        query = query.where(Customer.name.like(f"%{filters['customer_name']}%"))
    
    query = query.orderby(User.full_name).orderby(Customer.name).orderby(Contact.name, order=frappe.qb.asc)

    data = query.run(as_dict=True)
    
    final_data = []
    for row in data:
        contact_id = row.get("Contact ID")
        contact_email, contact_phone = "", ""
        
        if contact_id:
            emails = frappe.get_all("Contact Email", filters={"parent": contact_id}, pluck="email_id")
            phones = frappe.get_all("Contact Phone", filters={"parent": contact_id}, pluck="phone")
            contact_email = ", ".join(emails) if emails else ""
            contact_phone = ", ".join(phones) if phones else ""
        
        final_data.append({
            "Account Manager": row.get("Account Manager") or "",
            "Customer Name": row.get("Customer Name"),
            "Contact First Name": row.get("Contact First Name") or "",
            "Contact Last Name": row.get("Contact Last Name") or "",
            "Contact Email": contact_email,
            "Contact Phone": contact_phone
        })
    
    seen = set()
    deduped_data = []
    for row in final_data:
        key = (
            row["Account Manager"],
            row["Customer Name"],
            row["Contact First Name"],
            row["Contact Last Name"],
            row["Contact Email"],
            row["Contact Phone"]
        )
        if key not in seen:
            seen.add(key)
            deduped_data.append(row)
    
    grouped = defaultdict(list)
    for row in deduped_data:
        grouped[row["Customer Name"]].append(row)
    
    final_filtered_data = []
    for customer, rows in grouped.items():
        rows_with_contact = [r for r in rows if (r["Contact First Name"] or r["Contact Last Name"] or r["Contact Email"] or r["Contact Phone"])]
        if rows_with_contact:
            final_filtered_data.extend(rows_with_contact)
        else:
            final_filtered_data.append(rows[0])
    
    def sort_key(row):
        manager_sort = 0 if row["Account Manager"] else 1
        contact_exists = bool(
            row["Contact First Name"] or row["Contact Last Name"] or row["Contact Email"] or row["Contact Phone"]
        )
        contact_sort = 0 if contact_exists else 1
        return (manager_sort, row["Account Manager"], row["Customer Name"], contact_sort, row["Contact First Name"], row["Contact Last Name"])
    
    final_filtered_data.sort(key=sort_key)
    
    columns = [
        {"fieldname": "Customer Name", "label": "Customer Name", "fieldtype": "Data", "width": 250},
        {"fieldname": "Contact First Name", "label": "Contact First Name", "fieldtype": "Data", "width": 150},
        {"fieldname": "Contact Last Name", "label": "Contact Last Name", "fieldtype": "Data", "width": 150},
        {"fieldname": "Contact Email", "label": "Contact Email(s)", "fieldtype": "Data", "width": 350},
        {"fieldname": "Contact Phone", "label": "Contact Phone(s)", "fieldtype": "Data", "width": 300},
    ]
    
    return columns, final_filtered_data
