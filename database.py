# ============================================================
#  database.py — In-memory mock database
#  Structured for easy migration to PostgreSQL later
# ============================================================
import uuid
from datetime import datetime

# ── Users ────────────────────────────────────────────────
users = {
    "u1": {
        "name": "John Doe",
        "email": "john@example.com",
        "address": "Kochi, Kerala"
    },
    "u2": {
        "name": "Alice Smith",
        "email": "alice@example.com",
        "address": "Bangalore, India"
    }
}

# ── Orders ───────────────────────────────────────────────
orders = {
    "12345": {
        "user_id": "u1",
        "status": "Shipped",
        "delivery_date": "2026-03-25",
        "address": "Kochi, Kerala"
    },
    "10234": {
        "user_id": "u1",
        "status": "Processing",
        "delivery_date": "2026-03-28",
        "address": "Kochi, Kerala"
    },
    "20001": {
        "user_id": "u2",
        "status": "Delivered",
        "delivery_date": "2026-03-20",
        "address": "Bangalore, India"
    },
    "30001": {
        "user_id": "u2",
        "status": "Cancelled",
        "delivery_date": "2026-03-18",
        "address": "Bangalore, India"
    }
}

# ── Order Items ──────────────────────────────────────────
order_items = {
    "12345": [
        {"item_id": "i1", "product_name": "Running Shoes", "quantity": 1},
        {"item_id": "i2", "product_name": "T-shirt", "quantity": 2}
    ],
    "10234": [
        {"item_id": "i3", "product_name": "Laptop", "quantity": 1}
    ],
    "20001": [
        {"item_id": "i4", "product_name": "Headphones", "quantity": 1}
    ],
    "30001": [
        {"item_id": "i5", "product_name": "Backpack", "quantity": 1}
    ]
}

# ── Coupons ──────────────────────────────────────────────
coupons = {
    "SAVE20": {
        "discount": "20%",
        "expiry_date": "2026-04-01",
        "valid_users": ["u1", "u2"]
    },
    "FESTIVE10": {
        "discount": "10%",
        "expiry_date": "2026-03-30",
        "valid_users": ["u1"]
    },
    "WELCOME5": {
        "discount": "5%",
        "expiry_date": "2026-05-01",
        "valid_users": ["u2"]
    }
}

# ── FAQ Knowledge Base ──────────────────────────────────
faqs = {
    "registration": "To register a new account, simply provide your name, email, and address. Our assistant will use the 'register_user' tool to create your account instantly.",
    "cancellation": "You can cancel any 'Processing' order. However, if the order is already 'Shipped' or 'Delivered', it cannot be cancelled via the automated system. Please contact support for returns in that case.",
    "coupons": "To apply a coupon, find an active code using 'get_all_coupons' or 'get_user_coupons'. You can then share the code with us to verify its details.",
    "shipping": "Standard shipping takes 3-5 business days. You can check the 'delivery_date' in your order details at any time.",
    "returns": "Returns are accepted within 30 days of delivery for unworn items in original packaging.",
    "payment": "We currently accept all major credit cards, debit cards, and popular digital wallets.",
    "privacy": "We take your privacy seriously. Your personal data is encrypted and only used to process your orders and improve our service."
}

# ── Helpers ──────────────────────────────────────────────
def generate_user_id() -> str:
    """Generate a unique user ID."""
    return "u" + str(uuid.uuid4())[:8]

def generate_order_id() -> str:
    """Generate a unique order ID."""
    return str(uuid.uuid4().int)[:5]

def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")
