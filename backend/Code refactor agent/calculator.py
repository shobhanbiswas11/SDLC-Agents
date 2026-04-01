"""
A simple calculator module with basic arithmetic operations.
"""


def add(a, b):
    """Add two numbers and return the result."""
    return a + b


def subtract(a, b):
    """Subtract b from a and return the result."""
    return a - b


def multiply(a, b):
    """Multiply two numbers and return the result."""
    return a * b


def divide(a, b):
    """Divide a by b and return the result."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def power(base, exponent):
    """Raise base to the power of exponent."""
    return base ** exponent


def square_root(n):
    """Calculate the square root of a number."""
    if n < 0:
        raise ValueError("Cannot calculate square root of negative number")
    return n ** 0.5


def absolute_value(n):
    """Return the absolute value of a number."""
    return abs(n)


def modulo(a, b):
    """Return the remainder of a divided by b."""
    if b == 0:
        raise ValueError("Cannot perform modulo with zero")
    return a % b


if __name__ == "__main__":
    # Simple test cases
    print(f"10 + 5 = {add(10, 5)}")
    print(f"10 - 5 = {subtract(10, 5)}")
    print(f"10 * 5 = {multiply(10, 5)}")
    print(f"10 / 5 = {divide(10, 5)}")
    print(f"2 ^ 3 = {power(2, 3)}")
    print(f"√16 = {square_root(16)}")
    print(f"|-5| = {absolute_value(-5)}")
    print(f"17 % 5 = {modulo(17, 5)}")
