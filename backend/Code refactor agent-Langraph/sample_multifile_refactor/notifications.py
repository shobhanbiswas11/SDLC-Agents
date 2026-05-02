"""
notifications.py — Customer notification logic.

BAD CODE (needs refactoring):
- String concatenation instead of f-strings
- Repeated email building logic
- No base template abstraction
"""

from models import Customer


def send_order_confirmation(customer, order):
    subject = "Order Confirmation - #" + str(order["id"])
    body = (
        "Dear " + customer.name + ",\n\n"
        + "Thank you for your order!\n\n"
        + "Order ID   : " + str(order["id"]) + "\n"
        + "Subtotal   : $" + str(round(order["subtotal"], 2)) + "\n"
        + "Tax        : $" + str(round(order["tax"], 2)) + "\n"
        + "Grand Total: $" + str(round(order["grand_total"], 2)) + "\n\n"
        + "We will notify you when your order ships.\n\n"
        + "Regards,\nShop Team"
    )
    return _send_email(customer.email, subject, body)


def send_cancellation_notice(customer, order):
    subject = "Order Cancelled - #" + str(order["id"])
    body = (
        "Dear " + customer.name + ",\n\n"
        + "Your order #" + str(order["id"]) + " has been cancelled.\n\n"
        + "Refund of $" + str(round(order["grand_total"], 2)) + " will be processed in 3-5 business days.\n\n"
        + "Regards,\nShop Team"
    )
    return _send_email(customer.email, subject, body)


def send_shipment_update(customer, order, tracking_number):
    subject = "Your Order #" + str(order["id"]) + " Has Shipped!"
    body = (
        "Dear " + customer.name + ",\n\n"
        + "Great news! Your order #" + str(order["id"]) + " is on its way.\n\n"
        + "Tracking Number: " + str(tracking_number) + "\n\n"
        + "Regards,\nShop Team"
    )
    return _send_email(customer.email, subject, body)


def _send_email(to_address, subject, body):
    # Simulated email send — in production connects to SMTP/SES
    print(f"[EMAIL] To: {to_address} | Subject: {subject}")
    print(body)
    return {"to": to_address, "subject": subject, "body": body, "sent": True}
