"""
models.py — Data models for the order system.

BAD CODE (needs refactoring):
- No type hints
- Magic numbers scattered inline
- Redundant attribute assignments
- No __repr__ for debugging
"""


class Product:
    def __init__(self, id, name, price, stock):
        self.id = id
        self.name = name
        self.price = price
        self.stock = stock
        self.available = stock > 0  # simplified redundant ternary
        self.discount = 0
        self.category = "general"

    def apply_discount(self, pct):
        if pct < 0 or pct > 100:
            return False
        self.discount = pct
        self.price = self.price - (self.price * pct / 100)
        return True

    def reduce_stock(self, qty):
        if qty > self.stock:
            return False
        self.stock = self.stock - qty
        if self.stock == 0:
            self.available = False
        return True


class Customer:
    def __init__(self, id, name, email, tier):
        self.id = id
        self.name = name
        self.email = email
        self.tier = tier          # "standard", "silver", "gold"
        self.order_count = 0
        self.total_spent = 0.0

    def get_loyalty_discount(self):
        # Business rule: tier discounts must never change
        if self.tier == "gold":
            return 15
        elif self.tier == "silver":
            return 10
        elif self.tier == "standard":
            return 5
        else:
            return 0

    def record_purchase(self, amount):
        self.order_count = self.order_count + 1
        self.total_spent = self.total_spent + amount


class OrderItem:
    def __init__(self, product, quantity):
        self.product = product
        self.quantity = quantity
        self.unit_price = product.price
        self.line_total = self.unit_price * quantity  # use unit_price for clarity
