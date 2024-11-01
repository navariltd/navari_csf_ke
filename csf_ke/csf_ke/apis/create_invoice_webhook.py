import frappe 

def get_or_create_customer(customer_name):
    """Check if customer exists; if not, create it."""
    customer = frappe.db.exists("Customer", customer_name)
    if not customer:
        customer = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": customer_name,
            "customer_type": "Company",
            "customer_group": "All Customer Groups",
            "territory": "All Territories"
        })
        customer.insert(ignore_permissions=True)
        return customer.name
    return customer_name

def get_or_create_item(item_code):
    """Check if item exists; if not, create it."""
    item = frappe.db.exists("Item", item_code)
    if not item:
        item = frappe.get_doc({
            "doctype": "Item",
            "is_stock_item": 0,
            "item_name": item_code,
            "item_code": item_code,
            "item_group": "All Item Groups",
            "stock_uom": "Nos"
        })
        item.insert(ignore_permissions=True)
        return item.name
    return item_code

def get_or_create_tax_template(template_name, company):
    """Check if tax template exists; if not, create it."""
    tax_template = frappe.db.exists("Sales Taxes and Charges Template", {"title": template_name})
    if not tax_template:
        tax_template = frappe.get_doc({
            "doctype": "Sales Taxes and Charges Template",
            "title": template_name,
            "company": company,
            "taxes": [{
                "charge_type": "On Net Total",
                "description": "VAT @ 16.0",
                "account_head": frappe.db.get_value("Company", company, "default_deferred_expense_account"),
                "rate": 16.0
            }]
        })
        tax_template.insert(ignore_permissions=True)
        frappe.db.commit()
        return tax_template.name
    return template_name

def get_or_create_mode_of_payment(mode_name):
    """Check if mode of payment exists; if not, create it."""
    mode = frappe.db.exists("Mode of Payment", mode_name)
    if not mode:
        mode = frappe.get_doc({
            "doctype": "Mode of Payment",
            "mode_of_payment": mode_name,
            "type": "Phone" 
        })
        mode.insert(ignore_permissions=True)
        frappe.db.commit()
        return mode.name
    return mode_name

def get_default_income_account(company):
    """Fetch the default income account for the given company."""
    income_account = frappe.db.get_value("Company", company, "default_income_account")
    if not income_account:
        frappe.throw(f"Default income account is not set for {company}")
    return income_account

def create_sales_invoice_with_tax(transaction_id, trans_amount, team, default_currency, rate):
    """Main function to create Sales Invoice with necessary checks and resources."""
    company = frappe.db.get_single_value("Global Defaults", "default_company")
    

    customer_name = get_or_create_customer(team)
    item_code = get_or_create_item("Frappe Cloud")
    tax_template = get_or_create_tax_template("Sales Tax", company)
    income_account = get_default_income_account(company)
    mode_of_payment = get_or_create_mode_of_payment("Mpesa Express")

    # Prepare Sales Invoice data
    sales_invoice_data = {
        "doctype": "Sales Invoice",
        "customer": customer_name,
        "posting_date": frappe.utils.now(),
        "currency": default_currency,
        "company": company,
        "is_pos": 1,
        "items": [{
            "item_code": item_code,
            "description": "Payment via MPesa",
            "qty": 1,
            "rate": float(rate),
            "uom": "Nos",
            "income_account": income_account,
        }],
        "payments": [{
            "mode_of_payment": mode_of_payment,
            "amount": float(trans_amount),
            "payment_reference": transaction_id
        }],
        "status": "Paid",
        "taxes_and_charges": tax_template
    }

    # Create and submit the Sales Invoice
    sales_invoice = frappe.get_doc(sales_invoice_data)
    sales_invoice.insert(ignore_permissions=True)
    sales_invoice.submit()
    frappe.db.commit()

    # Generate PDF download URL
    pdf_download_url = frappe.utils.get_url(
        f"/api/method/frappe.utils.print_format.download_pdf?doctype=Sales%20Invoice&name={sales_invoice.name}&format=Sales%20Invoice%20Press&no_letterhead=0&letterhead=Default"
    )
    return pdf_download_url
