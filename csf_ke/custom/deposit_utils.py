import json
import frappe
from frappe import _
from frappe.utils import get_link_to_form
from frappe.model.mapper import get_mapped_doc


def get_invoice_order_type(doctype):
    if doctype == "Sales Invoice":
        return "Sales Order", "sales_order", "customer"
    elif doctype == "Purchase Invoice":
        return "Purchase Order", "purchase_order", "supplier"
    else:
        frappe.throw(_("Not an invoice document!"))


def validate_invoice(doc, methods):
    if doc.doctype not in ("Sales Invoice", "Purchase Invoice"):
        frappe.throw(_("Not an invoice document!"))
    
    order_doctype, order_field, _ = get_invoice_order_type(doc.doctype)

    if doc.is_deposit_invoice:
        validate_deposit_invoice(doc, order_doctype, order_field)
    else:
        validate_normal_invoice(doc, order_doctype, order_field)


def validate_deposit_invoice(doc, order_doctype, order_field):
    """
    Validation conditions
    1. Ensure only one line item and it is a deposit
    2. Validate link with SO/PO and amount
    3. Deposit invoice must be the first invoice being created for the same order
    If all the above constraints are passed, and it has docstatus 0 or 1, update deposit invoice back to SO/PO.
    """
    # Condition 1: Ensure only one line item and it is a deposit
    if len(doc.items) != 1 or not frappe.db.get_value("Item", doc.items[0].item_code, "is_deposit_item"):
        frappe.throw(_("Deposit invoice must contain only one deposit line item."))

    # Condition 2: Validate link with SO/PO and amount
    linked_doc = doc.items[0].get(order_field)
    if not linked_doc:
        return
    # if not linked_doc:
    #     frappe.throw(_("Deposit invoice must be linked to a {}.").format(order_doctype))
    linked_doc_amount = frappe.db.get_value(order_doctype, linked_doc, "total")
    if doc.items[0].amount > linked_doc_amount:
        frappe.throw(_("Deposit invoice amount cannot exceed the {}'s amount.").format(order_doctype))

    # Condition 3: Deposit invoice must be the first invoice being created for the same order
    existing_invoices = frappe.get_all(
        doc.doctype,
        filters=[
            [doc.doctype, "name", "!=", doc.name],
            [doc.doctype, "docstatus", "<", 2],
            [doc.doctype, "is_deposit_invoice", "=", 0],
            [f"{doc.doctype} Item", order_field, "=", linked_doc],
        ],
        limit=1,
    )
    if existing_invoices:
        link = get_link_to_form(order_doctype, linked_doc)
        frappe.throw(_("Cannot create deposit invoice for order {}.<br/>Deposit invoice must be the 1st invoice").format(link))

    if doc.docstatus in [0, 1]:
        # Update deposit invoice and percent deposit back to SO/PO
        if not doc.is_return:
            order = frappe.get_cached_doc(order_doctype, linked_doc)
            percent = doc.total / order.total * 100
            order.db_set("deposit_invoice", doc.name, update_modified=False)
            order.db_set("percent_deposit", percent, update_modified=False)
            order.reload()

        # A full refund of the deposit is allowed
        if doc.is_return and doc.return_against:
            deposit_amount = frappe.db.get_value(doc.doctype, doc.return_against, "total")
            return_deposit_amount = doc.total
            balance = deposit_amount + return_deposit_amount
            if balance != 0:
                frappe.throw(_("A full refund of the deposit is allowed."))
            else:
                order = frappe.get_cached_doc(order_doctype, linked_doc)
                order.db_set("deposit_invoice", "", update_modified=False)
                order.db_set("percent_deposit", 0, update_modified=False)
                order.reload()
    
    # Finally, erase link to so_detail, so it won't be used in the invoice
    # This is strangely needed as it was provided during open_mapped_doc to transfer currency
    if order_doctype == "Sales Order":
        doc.items[0].so_detail = ""
    else:
        doc.items[0].po_detail = ""


def validate_normal_invoice(doc, order_doctype, order_field):
    """ 
    1. For normal invoice, if it's order require 1st deposit, ensure they are not the first invoice 
    2. Allocation amount must not exceed the deposit amount.
    3. Ensure total allocated amount does not exceed the deposit balance
    """
    # Ensure this is not the first invoice in case of require deposit
    linked_docs = {item.get(order_field) for item in doc.items if item.get(order_field)}
    for linked_doc in linked_docs:
        order = frappe.get_value(order_doctype, linked_doc, ["has_deposit", "deposit_invoice"], as_dict=True)
        # If the linked order must 1st invoice deposit, but it not yet has it.
        if order["has_deposit"] and not order["deposit_invoice"]:
            link = get_link_to_form(order_doctype, linked_doc)
            frappe.throw(_("The 1st invoice of {} should be a deposit invoice.").format(link))

    # Ensure allocation amount must not exceed the deposit amount
    for d in doc.deposits:
        if d.allocated_amount > d.deposit_amount:
            frappe.throw(_("Allocated amount cannot exceed the deposit amount."))
    
    # Ensure total allocated amount (on ui) does not exceed the deposit balance (from db)
    doc_json = json.dumps(doc.as_dict(), indent=4, sort_keys=True, default=str)
    db_deposit = sum([x["deposit_amount"]for x in get_deposits(doc_json)])
    ui_allocation = sum([x.allocated_amount for x in doc.deposits])
    if ui_allocation > db_deposit:
        frappe.throw(_(
            "The Deposit Deduction in this document is {} but the remaining deposit for deduction is {}. "
            "Please verify Deposit Deduction").format("{:,}".format(ui_allocation), "{:,}".format(db_deposit)
        ))


def cancel_deposit_invoice(doc, method):
    if not doc.is_deposit_invoice:
        return
    order_doctype, order_field, _ = get_invoice_order_type(doc.doctype)
    linked_doc = doc.items[0].get(order_field)
    if not linked_doc:
        return
    order = frappe.get_cached_doc(order_doctype, linked_doc)
    order.db_set("deposit_invoice", "", update_modified=False)
    # Case cancel return deposit
    if doc.is_return and doc.return_against:
        return_against_total = frappe.db.get_value(doc.doctype, doc.return_against, "total")
        percent_deposit = return_against_total / order.total * 100
        order.db_set("deposit_invoice", doc.return_against, update_modified=False)
        order.db_set("percent_deposit", percent_deposit, update_modified=False)
    order.reload()
    # If exist normal invoice, don't allow to cancel deposit invoice
    existing_invoices = frappe.get_all(
        doc.doctype,
        filters=[
            [doc.doctype, "name", "!=", doc.name],
            [doc.doctype, "docstatus", "<", 2],
            [doc.doctype, "is_deposit_invoice", "=", 0],
            [f"{doc.doctype} Item", order_field, "=", linked_doc],
        ],
        limit=1,
    )
    if existing_invoices:
        link = get_link_to_form(order_doctype, linked_doc)
        frappe.throw("Unable to cancel the deposit invoice for order {}.<br/>Please cancel the normal invoice first.".format(link))
    # TODO: please make sure it is not cancelled if it already used as deposit deduction


def apply_deposit_deduction(doc, method):
    """
    If the row of deductions child table in this invoice has allocation_amount
    Get the Sales Invoice Item from row.reference_row
    Copy data in the Sales Invoice Item as another row in this invoice with rate = negative allocation_amount
    """
    if doc.is_deposit_invoice or doc.docstatus != 0:  # Only draft
        return
    
    # Recalc deposit if not manual allocation
    if not doc.manual_deposit_allocation:
        doc_json = json.dumps(doc.as_dict(), indent=4, sort_keys=True, default=str)
        calc_deposits = get_deposits(doc_json)
        doc.deposits = []
        for d in calc_deposits:
            doc.append("deposits", d)

    # Remove any line item with is_deposit_item = 1
    doc.items = [item for item in doc.items if not frappe.db.get_value("Item", item.item_code, "is_deposit_item")]
    next_idx = len(doc.items)
    for d in doc.deposits:
        if d.allocated_amount and d.reference_row:
            # Fetch the Sales Invoice Item using reference_row
            reference_item = frappe.get_doc(f"{doc.doctype} Item", d.reference_row)
            # Copy the reference item and modify necessary fields
            new_item = reference_item.as_dict()
            next_idx += 1
            new_item.update({
                "idx": next_idx,
                "name": None,  # Clear the name to allow insertion as a new row
                "parent": doc.name,
                "parentfield": "items",
                "parenttype": doc.doctype,
                "qty": 1,
                "rate": -d.allocated_amount,
                "amount": -d.allocated_amount,
            })
            doc.append("items", new_item)


@frappe.whitelist()
def create_deposit_invoice(source_name, target_doc=None):
    """
    Create a deposit Invoice from an Order.
    This method is used with frappe.model.open_mapped_doc.
    """

    order_doctype = frappe.flags.args.doctype
    doctype_field = "sales_order" if order_doctype == "Sales Order" else "purchase_order"
    detail_field = "so_detail" if order_doctype == "Sales Order" else "po_detail"
    tax_field = "Sales Taxes and Charges" if order_doctype == "Sales Order" else "Purchase Taxes and Charges"
    invoice_doctype = "Sales Invoice" if order_doctype == "Sales Order" else "Purchase Invoice"
    deposit_account_field = "sales_deposit_account" if order_doctype == "Sales Order" else "purchase_deposit_account"
    cost_center_field = "selling_cost_center" if order_doctype == "Sales Order" else "buying_cost_center"
    account_field = "income_account" if order_doctype == "Sales Order" else "expense_account"

    def set_missing_values(source, target):
        # Set additional fields on the target document
        target.is_deposit_invoice = 1

        # Add the deposit item
        deposit_item = frappe.call(
            "erpnext_thailand.custom.item.get_deposit_item", company=source.company
        )
        if not deposit_item:
            frappe.throw(_("No deposit item is configured for the company {0}.").format(source.company))

        target.append("items", {
            "item_code": deposit_item["item_code"],
            "item_name": deposit_item["item_name"],
            "qty": 1,
            "rate": frappe.flags.args.deposit_amount,
            account_field: deposit_item[deposit_account_field],
            "uom": deposit_item["uom"],
            doctype_field: source.name,
            detail_field: source.items[0].name,  # This is required to get currency passed in
            "cost_center": deposit_item[cost_center_field],
        })

    # Map the Order to a Invoice
    doc = get_mapped_doc(
        order_doctype,
        source_name,
        { 
            order_doctype: {
                "doctype": invoice_doctype,
                "validation": {"docstatus": ["=", 1]}
            },
			tax_field: {
				"doctype": tax_field,
				"reset_value": True,
			},
        },
        target_doc,
        set_missing_values
    )

    return doc


@frappe.whitelist()
def get_deposits(doc):
    invoice = json.loads(doc)
    deductions = get_tied_to_order_deposits(invoice)
    if invoice.get("use_untied_deposit"):
        deductions += get_untied_deposits(invoice)
    return deductions


def get_tied_to_order_deposits(invoice):
    """ Find orders related to this invoice and their deposit invoices"""
    invoice_doctype = invoice["doctype"]
    order_doctype, order_field, _ = get_invoice_order_type(invoice_doctype)

    # Collect all linked orders from the invoice items
    orders = {
        item.get(order_field)
        for item in invoice.get("items", [])
        if item.get(order_field)
    }

    deductions = []
    for order_name in orders:
        order = frappe.get_cached_doc(order_doctype, order_name)

        # Fetch all deposit invoices linked to the order (not included return deposit invoice)
        return_against_deposit_invoices = frappe.get_all(
            invoice_doctype,
            filters={
                "docstatus": 1,
                "is_deposit_invoice": 1,
                "is_return": 1,
                order_field: order.name,
            },
            pluck="return_against",
        )
        deposit_invoices = frappe.get_all(
            invoice_doctype,
            filters={
                "docstatus": 1,
                "is_deposit_invoice": 1,
                "is_return": 0,
                "name": ["not in", return_against_deposit_invoices],
                order_field: order.name,
            },
            pluck="name",
        )

        for deposit_invoice_name in deposit_invoices:
            deposit_invoice = frappe.get_cached_doc(invoice_doctype, deposit_invoice_name)
            if not deposit_invoice.items:
                continue
            deposit_item, initial_amount, deducted_amount = get_deposit_invoice_details(deposit_invoice)
            balance = initial_amount - deducted_amount

            # Calculate the invoice amount for the same order
            invoice_amount = sum(
                item.get("amount")
                for item in invoice.get("items", [])
                if item.get(order_field) == order.name and not item.get("is_deposit_item")
            )

            # Determine the allocated amount based on the deduction method
            if order.deposit_deduction_method == "Percent":
                percent_amount = (invoice_amount / order.total) * initial_amount
                allocated_amount = min(percent_amount, invoice_amount, balance)
            else:  # Full Amount
                allocated_amount = min(invoice_amount, balance)

            if allocated_amount > 0:
                deductions.append({
                    "reference_name": deposit_invoice.name,
                    "reference_row": deposit_item.name,
                    "remarks": deposit_item.description,
                    "deposit_amount": balance,
                    "allocated_amount": allocated_amount,
                })

    return deductions


def get_untied_deposits(invoice):
    """ Find deposit that is not related to any order but same customer/supplier and currency """
    invoice_doctype = invoice["doctype"]
    _, order_field, partner = get_invoice_order_type(invoice_doctype)

    deductions = []
    # Fetch all deposit invoices that is not tied to any order (not included return deposit invoice)
    return_against_deposit_invoices = frappe.get_all(
        invoice_doctype,
        filters={
            partner: invoice.get(partner),
            "docstatus": 1,
            "is_deposit_invoice": 1,
            "is_return": 1,
            order_field: ["in", ["", None]],
            "currency": invoice.get("currency"),
        },
        pluck="return_against",
    )
    deposit_invoices = frappe.get_all(
        invoice_doctype,
        filters={
            partner: invoice.get(partner),
            "docstatus": 1,
            "is_deposit_invoice": 1,
            "is_return": 0,
            "name": ["not in", return_against_deposit_invoices],
            order_field: ["in", ["", None]],
            "currency": invoice.get("currency"),
        },
        pluck="name",
    )

    for deposit_invoice_name in deposit_invoices:
        deposit_invoice = frappe.get_cached_doc(invoice_doctype, deposit_invoice_name)
        if not deposit_invoice.items:
            continue
        deposit_item, initial_amount, deducted_amount = get_deposit_invoice_details(deposit_invoice)
        balance = initial_amount - deducted_amount

        if balance > 0:
            deductions.append({
                "reference_name": deposit_invoice.name,
                "reference_row": deposit_item.name,
                "remarks": deposit_item.description,
                "deposit_amount": balance,
                "allocated_amount": 0,
            })

    return deductions


def get_deposit_invoice_details(doc):
    deposit_item = doc.items[0]
    initial_amount = deposit_item.amount

    # Calculate the total allocated amount from previous deductions
    previous_deductions = frappe.get_all(
        doc.doctype,
        filters=[
            [doc.doctype, "docstatus", "=", 1],
            [doc.doctype, "is_deposit_invoice", "=", 0],
            [f"{doc.doctype} Deposit", "reference_row", "=", deposit_item.name],
        ],
        fields=[f"`tab{doc.doctype} Deposit`.allocated_amount"],
    )
    deducted_amount = sum(d["allocated_amount"] for d in previous_deductions)

    # Calculate the remaining deposit balance
    return deposit_item, initial_amount, deducted_amount