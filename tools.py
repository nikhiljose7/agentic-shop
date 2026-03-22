# ============================================================
#  tools.py — Master tool registry for the AI agent
#  Add all tool functions here and register them in TOOLS
# ============================================================

# ── Built-in utility tools ───────────────────────────────
def get_current_time() -> str:
    """Returns the current date and time. Use this when the user asks what time or date it is."""
    from datetime import datetime
    now = datetime.now()
    return now.strftime("Today is %A, %B %d, %Y. The current time is %I:%M %p.")


def calculator(expression: str) -> str:
    """
    Evaluates a mathematical expression and returns the result.
    Use this for any arithmetic, math calculations, or number problems.
    Example expressions: '2 + 2', '15 * 8', '100 / 4', '2 ** 10'
    """
    try:
        allowed = {
            "__builtins__": {},
            "abs": abs, "round": round, "pow": pow,
            "min": min, "max": max, "sum": sum,
        }
        result = eval(expression, allowed)
        return f"The result of {expression} is {result}"
    except Exception as e:
        return f"Could not evaluate '{expression}': {str(e)}"


# ── E-commerce tools ─────────────────────────────────────
from ecommerce_tools import (
    # User
    register_user,
    get_user_details,
    
    # Order
    get_order_status,
    get_order_details,
    cancel_order,
    update_order_address,
    update_order_quantity,
    # Coupon
    get_all_coupons,
    get_coupon_details,
    get_user_coupons,
    # Knowledge Agent
    search_faq,
)


# ── TOOL REGISTRY ────────────────────────────────────────
#  All tools the AI agent can call
TOOLS = [
    # Utility
    get_current_time,
    calculator,

    # User management
    register_user,
    get_user_details,
    

    # Order management
    get_order_status,
    get_order_details,
    cancel_order,
    update_order_address,
    update_order_quantity,

    # Coupons
    get_all_coupons,
    get_coupon_details,
    get_user_coupons,

    # Knowledge Agent (FAQ / RAG)
    search_faq,
]
