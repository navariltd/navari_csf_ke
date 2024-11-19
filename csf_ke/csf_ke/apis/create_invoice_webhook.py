import frappe 
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from frappe import _
from frappe.utils import nowdate

def get_or_create_customer(customer_name):
    """Check if customer exists; if not, create it."""
    customer = frappe.db.exists("Customer", customer_name)
    if not customer:
        customer = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": customer_name,
            "customer_type": "Company",
            "customer_group": "All customer Group",
            "territory": "All Territories"
        })
        customer.insert(ignore_permissions=True)
        return customer.name
    return customer_name

def get_or_create_supplier(supplier_name):
    """Check if customer exists; if not, create it."""
    supplier = frappe.db.exists("Supplier", supplier_name)
    if not supplier:
        supplier = frappe.get_doc({
            "doctype": "Supplier",
            "supplier_name": supplier_name,
            "supplier_type": "Company",
            "supplier_group": "All Supplier Groups",
        })
        supplier.insert(ignore_permissions=True)
        return supplier.name
    return supplier_name

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

def get_or_create_tax_template(template_name, company, doctype):
    """
    Check if tax template exists with the correct conditions; if not, create it.

    Args:
        template_name (str): The title of the tax template.
        company (str): The name of the company.
        doctype (str): The parent doctype (e.g., "Sales Invoice" or "Purchase Invoice").
    
    Returns:
        str: The name of the existing or newly created tax template.
    """
    # Determine which template and child table to use based on the parent doctype
    if doctype == "Sales Invoice":
        tax_template_doctype = "Sales Taxes and Charges Template"
        tax_child_table = "Sales Taxes and Charges"
        default_account_field = "default_income_account"
    elif doctype == "Purchase Invoice":
        tax_template_doctype = "Purchase Taxes and Charges Template"
        tax_child_table = "Purchase Taxes and Charges"
        default_account_field = "default_expense_account"
    else:
        frappe.throw("Invalid doctype. Use 'Sales Invoice' or 'Purchase Invoice'.")

    # Check if a matching tax template already exists
    tax_template = frappe.db.get_value(
        tax_template_doctype, 
        {"title": ["like", f"%{template_name}%"]}, 
        "name"
    )
    
    if tax_template:
        # Verify if the tax exists within the child table
        tax_exists = frappe.db.exists(
            tax_child_table,
            {
                "parent": tax_template,
                "rate": 16.0,
                "included_in_print_rate": 0  # For "Inclusive of Tax"
            }
        )
        if tax_exists:
            return tax_template

    # Get the default account for the company
    account_head = frappe.db.get_value("Company", company, default_account_field)
    if not account_head:
        frappe.throw(f"{default_account_field.replace('_', ' ').title()} is not set in the Company settings.")

    # Create a new tax template
    tax_template_doc = frappe.get_doc({
        "doctype": tax_template_doctype,
        "title": template_name,
        "company": company,
        "taxes": [{
            "charge_type": "On Net Total",
            "description": f"VAT @ 16.0",
            "account_head": account_head,
            "rate": 16.0,
            "included_in_print_rate": 0
        }]
    })
    tax_template_doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return tax_template_doc.name


'''Has awkward behavour because i have also to manually insert the sales an taxes charges for it to calculate tax. SO lets opt just to use sales and taxes charges'''
@frappe.whitelist(allow_guest=True)
def get_or_create_item_tax_template(template_name, tax_rate, company):
    """
    Check if an Item Tax Template exists; if not, create it.
    
    Args:
        template_name (str): The name of the Item Tax Template.
        tax_rate (float): The tax rate to apply.
        company (str): The company for which the template is created.
    
    Returns:
        str: The name of the Item Tax Template.
    """
    item_tax_template = frappe.db.exists("Item Tax Template", {"title": template_name})
    vat_account = frappe.db.get_value(
    "Account",
    {
        "company": company,
        "account_name": ["like", "%VAT%"],
        "is_group": False  
    },
    "name"
)

    if not item_tax_template:
        item_tax_template_doc = frappe.get_doc({
            "doctype": "Item Tax Template",
            "title": template_name,
            "taxes": [{
                "tax_type": vat_account,
                "tax_rate": tax_rate
            }]
        })
        item_tax_template_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return item_tax_template_doc.name
    
    template_name = frappe.db.get_value("Item Tax Template", {"title": template_name}, "name")
    return template_name


def get_or_create_mode_of_payment(mode_name, company):
    """Check if mode of payment exists; if not, create it with an account."""
    mode = frappe.db.exists("Mode of Payment", mode_name)

    # Get the default account for the mode of payment
    mode_of_payment_account = frappe.db.get_value(
        "Account",
        {
            "company": company,
            "account_name": ["like", "%Cash%"],
            "is_group": False  
        },
        "name"
    )

    if not mode:
        mode = frappe.get_doc({
            "doctype": "Mode of Payment",
            "mode_of_payment": mode_name,
            "type": "Phone",  
            "accounts": [{
                "company": company,
                "default_account": mode_of_payment_account
            }]
        })
        mode.insert(ignore_permissions=True)
        frappe.db.commit()
        return mode.name

    mode_doc = frappe.get_doc("Mode of Payment", mode_name)

    return mode_name


def get_default_income_or_expense_account(company, doctype):
    """Fetch the default income account for the given company."""
    income_account = None
    if doctype=="Sales Invoice":
        income_account = frappe.db.get_value("Company", company, "default_income_account")
    else:
        income_account = frappe.db.get_value("Company", company, "default_expense_account")
    if not income_account:
        frappe.throw(f"Default income account is not set for {company}")
    return income_account

    
@frappe.whitelist(allow_guest=True)
def create_invoice_with_tax(doctype, transaction_id, trans_amount, team, default_currency, rate):
    """Main function to create Sales Invoice with necessary checks and resources."""
    company = frappe.db.get_single_value("Global Defaults", "default_company")
    
    item_code = get_or_create_item("Frappe Cloud")
    tax_template = get_or_create_tax_template("VAT 16%", company, doctype)
    
    '''Uncomment if you gonna go back to item tax template'''
    # tax_template = get_or_create_item_tax_template("VAT 16%", 16.0, company)
    income_or_expense_account = get_default_income_or_expense_account(company, doctype)
    mode_of_payment = get_or_create_mode_of_payment("Mpesa Express", company)
    
    invoice_name=None
    entity_doc_name=None
    if doctype == "Sales Invoice":
        customer_name = get_or_create_customer(team)
        entity_doc_name='Sales'
        invoice_name=create_sales_invoice(customer_name, mode_of_payment,trans_amount, tax_template, item_code, rate, company, transaction_id)
    else:
        supplier_name = get_or_create_supplier(team)
        entity_doc_name='Purchase'
        invoice_name=create_purchase_invoice(supplier_name,mode_of_payment, trans_amount, tax_template, item_code, rate, company, transaction_id)

     # Generate PDF download URL
    pdf_download_url = frappe.utils.get_url(
        f"/api/method/frappe.utils.print_format.download_pdf?doctype={entity_doc_name}%20Invoice&name={invoice_name}&format=Sales%20Invoice%20Press&no_letterhead=0&letterhead=Default"
    )
    return pdf_download_url

def create_sales_invoice(customer_name, mode_of_payment,trans_amount, tax_template, item_code, rate, company, transaction_id):
    """Create a Sales Invoice with the given details."""
    income_account = frappe.db.get_value("Company", company, "default_income_account")
    sales_invoice = frappe.get_doc({
        "doctype": "Sales Invoice",
        "customer": customer_name,
        "posting_date": frappe.utils.now(),
        "company": company,
        "is_pos": 1,
        "items": [{
            "item_code": item_code,
            "description": "Payment via MPesa",
            "qty": 1,
            "rate": float(rate),
            "uom": "Nos",
            "income_account": income_account,
            "item_tax_template": tax_template
        }],
        "payments": [{
            "mode_of_payment": mode_of_payment,
            "amount": float(trans_amount),
            "payment_reference": transaction_id
     }],
        "status": "Paid",
        "taxes_and_charges": tax_template
    }
    )
    sales_invoice.insert(ignore_permissions=True)
    sales_invoice.submit()
    frappe.db.commit()
    return sales_invoice.name
    
def create_purchase_invoice(supplier_name, mode_of_payment, trans_amount, tax_template, item_code, rate, company, transaction_id):
    """Create a Purchase Invoice with the given details."""
    expense_account = frappe.db.get_value("Company", company, "default_expense_account")
    purchase_invoice = frappe.get_doc({
        "doctype": "Purchase Invoice",
        "supplier": supplier_name,
        "posting_date": frappe.utils.now(),
        "company": company,
        "items": [{
            "item_code": item_code,
            "description": "Payment via MPesa",
            "qty": 1,
            "rate": float(rate),
            "uom": "Nos",
            "expense_account": expense_account,
        }],
        "payments": [{
            "mode_of_payment": mode_of_payment,
             "amount": float(trans_amount),
            "payment_reference": transaction_id
     }],
        "status": "Paid",
        "taxes_and_charges": tax_template
    }
    )
    purchase_invoice.insert(ignore_permissions=True)
    purchase_invoice.submit()
    create_payment_entry_from_invoice(purchase_invoice.name, mode_of_payment, 1300)
    frappe.db.commit()
    return purchase_invoice.name


def create_payment_entry_from_invoice(invoice_name, mode_of_payment, trans_amount, bank_account=None):
    """
    Creates a Payment Entry based on the provided Purchase Invoice.
    
    :param invoice_name: Name of the Purchase Invoice
    :param mode_of_payment: Payment method (e.g., 'Cash', 'Bank', 'MPesa')
    :param trans_amount: Transaction amount to be paid
    :param bank_account: Bank account for the payment (optional)
    :return: Payment Entry Name (ID)
    """
    purchase_invoice = frappe.get_doc("Purchase Invoice", invoice_name)
    
    if purchase_invoice.outstanding_amount == 0:
        frappe.throw(_("The Purchase Invoice does not have any outstanding amount to pay."))
    
    bank_account = bank_account
    
    payment_entry = get_payment_entry(
        purchase_invoice.doctype, purchase_invoice.name, bank_account=bank_account
    )
    
    payment_entry.reference_no = purchase_invoice.get("order_code") or purchase_invoice.name
    payment_entry.posting_date = nowdate()
    payment_entry.reference_date = nowdate()
    
    payment_entry.mode_of_payment = mode_of_payment
    payment_entry.paid_amount = trans_amount
    payment_entry.received_amount = trans_amount
    
    payment_entry.insert(ignore_permissions=True)
    
    payment_entry.submit()

