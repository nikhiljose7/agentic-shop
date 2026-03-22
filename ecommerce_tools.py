# ============================================================
#  ecommerce_tools.py — All e-commerce tool functions
#  Each function is an agent tool callable by the AI model
# ============================================================
import database as db

# ════════════════════════════════════════════════════════════
#  USER FUNCTIONS
# ════════════════════════════════════════════════════════════

def register_user(name: str, email: str, address: str) -> str:
    """
    Register a new user in the system with their name, email, and address.
    Use this when a user wants to create an account or sign up.
    Returns the new user's ID and confirmation.
    """
    if not name or not email or not address:
        return "Error: name, email, and address are all required."

    # Check for duplicate email
    for uid, user in db.users.items():
        if user["email"].lower() == email.lower():
            return f"Error: A user with email '{email}' already exists (User ID: {uid})."

    user_id = db.generate_user_id()
    db.users[user_id] = {
        "name": name,
        "email": email,
        "address": address
    }
    return (
        f"User registered successfully!\n"
        f"- User ID: {user_id}\n"
        f"- Name: {name}\n"
        f"- Email: {email}\n"
        f"- Address: {address}"
    )


def get_user_details(**kwargs) -> str:
    """
    Retrieve details of the currently logged-in user.
    Use this when a user asks about their account, profile, or personal details.
    """
    user_id = kwargs.get("user_id")
    if not user_id:
        return "Error: Could not retrieve the current user context."

    user = db.users.get(user_id)
    if not user:
        return f"Error: No user found with user_id '{user_id}'."

    # Get all orders for this user
    user_orders = [oid for oid, o in db.orders.items() if o["user_id"] == user_id]

    return {
        "status": "success",
        "user_id": user_id,
        "name": user["name"],
        "email": user["email"],
        "address": user["address"],
        "order_ids": user_orders
    }


def check_login_status(**kwargs) -> str:
    """
    Check if the user is currently logged into the system.
    ALWAYS use this tool FIRST before calling any other tool if you need to access personal data (like orders or coupons).
    If the response says the user is NOT logged in, tell the user they must log in using the button on the top right.
    """
    user_id = kwargs.get("user_id")
    if not user_id or str(user_id).lower() in ("none", "null", "undefined", ""):
        return "FALSE: The user is NOT logged in. You MUST ask the user to log in via the UI button."
    
    return f"TRUE: The user is logged in with user_id {user_id}."


# ════════════════════════════════════════════════════════════
#  ORDER FUNCTIONS
# ════════════════════════════════════════════════════════════

def get_order_status(order_id: str) -> str:
    """
    Get the current status of an order by order_id.
    Use this when a user asks 'where is my order', 'what is my order status',
    or 'has my order shipped'. Returns status and expected delivery date.
    """
    order = db.orders.get(order_id)
    if not order:
        return f"Error: No order found with order_id '{order_id}'."

    return (
        f"Order #{order_id} Status:\n"
        f"- Status: {order['status']}\n"
        f"- Expected Delivery: {order['delivery_date']}\n"
        f"- Shipping Address: {order['address']}"
    )


def get_order_details(order_id: str) -> str:
    """
    Get full details of an order including all items in the order.
    Use this when a user asks about what they ordered, their order contents,
    or wants a full order summary.
    """
    order = db.orders.get(order_id)
    if not order:
        return f"Error: No order found with order_id '{order_id}'."

    items = db.order_items.get(order_id, [])
    items_text = ""
    for item in items:
        items_text += (
            f"  • {item['product_name']} "
            f"(Item ID: {item['item_id']}, Qty: {item['quantity']})\n"
        )

    user = db.users.get(order["user_id"], {})
    return (
        f"Order #{order_id} Details:\n"
        f"- Customer: {user.get('name', 'Unknown')}\n"
        f"- Status: {order['status']}\n"
        f"- Delivery Date: {order['delivery_date']}\n"
        f"- Shipping Address: {order['address']}\n"
        f"- Items:\n{items_text.strip() if items_text else '  No items found'}"
    )


def cancel_order(order_id: str) -> str:
    """
    Cancel an order by order_id.
    Use this when a user requests to cancel their order.
    Orders that are already Delivered or Cancelled cannot be cancelled.
    """
    order = db.orders.get(order_id)
    if not order:
        return f"Error: No order found with order_id '{order_id}'."

    if order["status"] == "Cancelled":
        return f"Order #{order_id} is already cancelled."

    if order["status"] == "Delivered":
        return (
            f"Error: Order #{order_id} has already been delivered and cannot be cancelled. "
            "Please initiate a return instead."
        )

    if order["status"] == "Shipped":
        return (
            f"Error: Order #{order_id} has already been shipped and cannot be cancelled. "
            "Please wait for delivery and then initiate a return."
        )

    # Processing orders can be cancelled
    db.orders[order_id]["status"] = "Cancelled"
    return f"Order #{order_id} has been successfully cancelled."


def update_order_address(order_id: str, new_address: str) -> str:
    """
    Update the shipping address of an order.
    Use this when a user wants to change their delivery address.
    Only orders in 'Processing' status can have their address updated.
    """
    if not new_address:
        return "Error: new_address cannot be empty."

    order = db.orders.get(order_id)
    if not order:
        return f"Error: No order found with order_id '{order_id}'."

    if order["status"] != "Processing":
        return (
            f"Error: Cannot update address for order #{order_id}. "
            f"The order is currently '{order['status']}'. "
            "Address can only be changed while the order is still Processing."
        )

    old_address = order["address"]
    db.orders[order_id]["address"] = new_address
    return (
        f"Shipping address for order #{order_id} updated successfully!\n"
        f"- Old Address: {old_address}\n"
        f"- New Address: {new_address}"
    )


def update_order_quantity(order_id: str, item_id: str, quantity: int) -> str:
    """
    Update the quantity of a specific item in an order.
    Use this when a user wants to change how many of an item they want.
    Only works for orders in 'Processing' status.
    Set quantity to 0 to remove the item from the order.
    """
    if quantity < 0:
        return "Error: Quantity cannot be negative."

    order = db.orders.get(order_id)
    if not order:
        return f"Error: No order found with order_id '{order_id}'."

    if order["status"] != "Processing":
        return (
            f"Error: Cannot update items for order #{order_id}. "
            f"The order is currently '{order['status']}'. "
            "Items can only be modified while the order is still Processing."
        )

    items = db.order_items.get(order_id, [])
    for item in items:
        if item["item_id"] == item_id:
            if quantity == 0:
                db.order_items[order_id] = [i for i in items if i["item_id"] != item_id]
                return f"Item '{item['product_name']}' (ID: {item_id}) removed from order #{order_id}."

            old_qty = item["quantity"]
            item["quantity"] = quantity
            return (
                f"Quantity updated for order #{order_id}:\n"
                f"- Item: {item['product_name']} (ID: {item_id})\n"
                f"- Old Quantity: {old_qty}\n"
                f"- New Quantity: {quantity}"
            )

    return f"Error: No item with item_id '{item_id}' found in order #{order_id}."


def get_order_history(**kwargs) -> str:
    """
    Get all orders for the currently logged-in user with their status and delivery date.
    Use this when a user asks 'show my orders', 'what are my orders',
    'show my order history', 'what have I ordered', or asks about delivery
    dates without providing a specific order ID.
    Returns a summary list of all orders belonging to the user.
    """
    user_id = kwargs.get("user_id")
    if not user_id or user_id not in db.users:
        return "Error: Could not retrieve order history for your session."

    user_name = db.users[user_id]["name"]
    user_orders = [
        (oid, o) for oid, o in db.orders.items()
        if o["user_id"] == user_id
    ]

    if not user_orders:
        return f"You have no orders yet, {user_name}."

    result = f"Order history for {user_name}:\n"
    for oid, order in user_orders:
        result += (
            f"\n• Order #{oid}"
            f"\n  - Status: {order['status']}"
            f"\n  - Expected Delivery: {order['delivery_date']}"
            f"\n  - Address: {order['address']}"
        )
    return result.strip()


# ════════════════════════════════════════════════════════════
#  COUPON FUNCTIONS
# ════════════════════════════════════════════════════════════

def get_all_coupons() -> str:
    """
    Retrieve all available coupons in the system.
    Use this when a user asks 'what coupons are available', 'any discounts?',
    or 'show me all promo codes'.
    """
    if not db.coupons:
        return "No coupons are currently available."

    result = "Available Coupons:\n"
    for code, details in db.coupons.items():
        result += (
            f"\n• Code: {code}\n"
            f"  - Discount: {details['discount']}\n"
            f"  - Expires: {details['expiry_date']}\n"
        )
    return result.strip()


def get_coupon_details(coupon_code: str) -> str:
    """
    Get details about a specific coupon code including discount percentage and expiry.
    Use this when a user asks about a particular coupon or promo code.
    """
    coupon = db.coupons.get(coupon_code.upper())
    if not coupon:
        return f"Error: Coupon code '{coupon_code}' not found or is invalid."

    eligible_count = len(coupon["valid_users"])
    return (
        f"Coupon Details for '{coupon_code.upper()}':\n"
        f"- Discount: {coupon['discount']}\n"
        f"- Expiry Date: {coupon['expiry_date']}\n"
        f"- Eligible Users: {eligible_count} user(s)"
    )


def get_user_coupons(**kwargs) -> str:
    """
    Get all coupons available for the currently logged in user.
    Use this when a user asks 'what coupons do I have', 'my discounts',
    or 'coupons for my account'.
    """
    user_id = kwargs.get("user_id")
    if not user_id or user_id not in db.users:
        return f"Error: Could not retrieve coupons for your session."

    user_name = db.users[user_id]["name"]
    available = {
        code: details
        for code, details in db.coupons.items()
        if user_id in details["valid_users"]
    }

    if not available:
        return f"No coupons are currently available for {user_name}."

    result = f"Coupons available for {user_name}:\n"
    for code, details in available.items():
        result += (
            f"\n• Code: {code}\n"
            f"  - Discount: {details['discount']}\n"
            f"  - Expires: {details['expiry_date']}\n"
        )
    return result.strip()


# ════════════════════════════════════════════════════════════
#  KNOWLEDGE AGENT (RAG SIMULATION)
# ════════════════════════════════════════════════════════════

def search_faq(query: str) -> str:
    """
    Search the knowledge base for answers to common platform questions.
    Use this for questions about how to register, cancel orders, apply coupons,
    shipping times, return policies, payment methods, privacy, or any general
    platform usage question that does not require account-specific data.
    """
    query_lower = query.lower()

    KEYWORD_MAP = {
        "registration": [
            "register", "sign up", "signup", "create account", "new account",
            "join", "how to register", "how do i register"
        ],
        "cancellation": [
            "cancel", "cancellation", "how to cancel", "stop order",
            "undo order", "reverse order"
        ],
        "coupons": [
            "coupon", "promo", "discount", "voucher", "code", "apply coupon",
            "promotional", "offer", "deal"
        ],
        "shipping": [
            "shipping", "delivery time", "how long", "when will",
            "estimated delivery", "dispatch", "days"
        ],
        "returns": [
            "return", "refund", "send back", "exchange", "unworn",
            "return policy", "how to return"
        ],
        "payment": [
            "payment", "pay", "credit card", "debit card", "wallet",
            "how to pay", "accepted payments", "methods"
        ],
        "privacy": [
            "privacy", "data", "personal information", "secure", "security",
            "gdpr", "my data", "information stored"
        ],
    }

    matches = []
    seen_keys = set()

    for faq_key, keywords in KEYWORD_MAP.items():
        if faq_key in seen_keys:
            continue
        for keyword in keywords:
            if keyword in query_lower:
                if faq_key in db.faqs:
                    matches.append(db.faqs[faq_key])
                    seen_keys.add(faq_key)
                break

    if not matches:
        return (
            "I'm sorry, I couldn't find a specific answer in our knowledge base. "
            "You can ask me about registration, order cancellation, coupons, "
            "shipping times, returns, payment methods, or account privacy."
        )

    return "Here is information from our knowledge base:\n\n" + "\n\n".join(matches)

