"""
order_service.py — Order creation and fulfilment logic.

BAD CODE (needs refactoring):
- God function doing too many things
- print() used instead of logging
- Repeated validation checks
- No early returns (deeply nested)
"""

from models import Customer, Product, OrderItem
from pricing import calculate_order_total


VALID_STATUSES = ["pending", "confirmed", "shipped", "delivered", "cancelled"]


class OrderService:

    def __init__(self):
        self.orders = {}
        self.next_id = 1000

    def create_order(self, customer, product_quantities):
        """
        Create a new order.
        product_quantities: list of (Product, int) tuples
        Returns order dict or None on failure.
        """
        # Validate customer
        if customer is None:
            print("ERROR: customer is None")
            return None
        else:
            if customer.email is None or customer.email == "":
                print("ERROR: customer has no email")
                return None
            else:
                # Build order items
                items = []
                errors = []
                for product, qty in product_quantities:
                    if qty <= 0:
                        errors.append(f"Invalid qty {qty} for {product.name}")
                    else:
                        if not product.available:
                            errors.append(f"{product.name} is out of stock")
                        else:
                            if product.stock < qty:
                                errors.append(f"Not enough stock for {product.name}: need {qty}, have {product.stock}")
                            else:
                                item = OrderItem(product, qty)
                                items.append(item)

                if len(errors) > 0:
                    print("ORDER ERRORS:", errors)
                    return None
                else:
                    # Deduct stock
                    for item in items:
                        item.product.reduce_stock(item.quantity)

                    # Calculate totals
                    subtotal, tax, grand_total = calculate_order_total(items, customer)

                    order_id = str(self.next_id)
                    self.next_id = self.next_id + 1

                    order = {
                        "id": order_id,
                        "customer_id": customer.id,
                        "customer_email": customer.email,
                        "items": items,
                        "subtotal": subtotal,
                        "tax": tax,
                        "grand_total": grand_total,
                        "status": "pending",
                    }

                    self.orders[order_id] = order
                    customer.record_purchase(grand_total)
                    print(f"Order {order_id} created. Total: {grand_total}")
                    return order

    def cancel_order(self, order_id):
        if order_id not in self.orders:
            print(f"ERROR: order {order_id} not found")
            return False
        order = self.orders[order_id]
        if order["status"] == "shipped" or order["status"] == "delivered":
            print(f"ERROR: cannot cancel order in status {order['status']}")
            return False
        # Restore stock
        for item in order["items"]:
            item.product.stock = item.product.stock + item.quantity
            if item.product.stock > 0:
                item.product.available = True
        order["status"] = "cancelled"
        print(f"Order {order_id} cancelled")
        return True

    def update_status(self, order_id, new_status):
        if order_id not in self.orders:
            return False
        if new_status not in VALID_STATUSES:
            return False
        self.orders[order_id]["status"] = new_status
        return True

    def get_order(self, order_id):
        return self.orders.get(order_id, None)
