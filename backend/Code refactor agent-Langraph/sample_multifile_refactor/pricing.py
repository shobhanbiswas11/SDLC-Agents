"""
pricing.py — Pricing and tax calculation logic.

BAD CODE (needs refactoring):
- Deeply nested ifs
- Magic numbers for tax rates
- No separation between tax computation and discount computation
- Duplicate calculation logic
"""

from models import Customer, OrderItem


TAX_RATE_STANDARD = 0.18    # GST standard
TAX_RATE_REDUCED  = 0.05    # GST reduced (essentials)
TAX_RATE_ZERO     = 0.00    # Tax exempt


def calculate_item_price(item, customer):
    # Apply loyalty discount on top of any existing product discount
    base = item.unit_price
    loyalty_disc = customer.get_loyalty_discount()
    discounted = base - (base * loyalty_disc / 100)
    item.line_total = discounted * item.quantity
    return item.line_total


def calculate_tax(subtotal, category):
    # Business rule: category determines tax rate — must not change
    if category == "essential":
        tax = subtotal * TAX_RATE_REDUCED
    elif category == "exempt":
        tax = subtotal * TAX_RATE_ZERO
    else:
        tax = subtotal * TAX_RATE_STANDARD
    return round(tax, 2)


def calculate_order_total(items, customer):
    subtotal = 0
    for i in range(len(items)):        # bad: should be for item in items
        subtotal = subtotal + calculate_item_price(items[i], customer)

    tax = 0
    for i in range(len(items)):        # bad: duplicate loop
        cat = items[i].product.category
        item_tax = calculate_tax(items[i].line_total, cat)
        tax = tax + item_tax

    grand_total = subtotal + tax
    return subtotal, tax, grand_total
