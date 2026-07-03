# ==========================================================
# calculations.py
# Simple invoice total calculator — NO GST.
# Each item's "rate" is the final line amount the user typed in
# (there is no quantity multiplier and no tax added on top).
# ==========================================================

def calculate_invoice(items):
    """
    items: list of dicts, each with at least:
        particular (str), hsn (str), rate (number)

    Returns:
        {
            "items": [ {particular, hsn, rate, amount}, ... ],
            "subtotal": float,   # kept for backward compatibility
            "grand_total": float,
        }
    """

    processed_items = []
    total = 0.0

    for item in items:
        try:
            rate = float(item.get("rate", 0) or 0)
        except (TypeError, ValueError):
            rate = 0.0

        amount = rate  # no GST, no quantity multiplier

        processed_items.append({
            "particular": item.get("particular", ""),
            "hsn": item.get("hsn", ""),
            "rate": rate,
            "amount": amount,
        })

        total += amount

    return {
        "items": processed_items,
        "subtotal": total,
        "grand_total": total,
    }