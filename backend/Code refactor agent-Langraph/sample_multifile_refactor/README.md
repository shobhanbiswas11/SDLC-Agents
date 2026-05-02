# Sample Multi-File Refactor Test

A small **e-commerce order system** with intentionally messy code across 4 files.
Use this to test whether the refactor agent can clean up all files without
breaking any business logic.

---

## Files

| File | Responsibility | What needs fixing |
|------|---------------|-------------------|
| `models.py` | Data models: Product, Customer, OrderItem | No type hints, redundant ternary, magic inline math |
| `pricing.py` | Tax & discount calculations | Duplicate loops, magic numbers, nested ifs |
| `order_service.py` | Order creation & cancellation | God function, deep nesting, `print()` instead of logging |
| `notifications.py` | Email notifications | String concat instead of f-strings, repeated body templates |

---

## Cross-File Dependencies

```
order_service.py
    ├── imports Customer, Product, OrderItem  ← from models.py
    └── imports calculate_order_total         ← from pricing.py

pricing.py
    └── imports Customer, OrderItem           ← from models.py

notifications.py
    └── imports Customer                      ← from models.py
```

---

## Business Rules That MUST NOT Change

1. **Loyalty discounts** — gold=15%, silver=10%, standard=5% (`models.py → Customer.get_loyalty_discount`)
2. **Tax rates** — standard=18%, reduced=5%, exempt=0% (`pricing.py → calculate_tax`)
3. **Stock deduction** — stock reduced on order, restored on cancel (`order_service.py`)
4. **`record_purchase`** — order count and total_spent must be updated on every order (`models.py`)
5. **`grand_total = subtotal + tax`** — formula must remain (`pricing.py`)
6. **Cancel guard** — shipped/delivered orders cannot be cancelled (`order_service.py`)

---

## How to Test

Send this prompt to the refactor agent:

```
Refactor all files in the sample_multifile_refactor/ directory.
Improve code quality (type hints, f-strings, early returns, remove magic numbers,
fix loops) but do NOT change any business logic or external interfaces.
```

After refactoring, the `logic_verification_node` should review all 4 files
and confirm all 6 business rules above are still intact.
