"""Order checkout."""

from shop.money import percent_of

PROMO_CODES = {"WELCOME10": 10, "SUMMER15": 15, "VIP35": 35}
SUPPORTED_CITIES = ("msk", "spb")
MAX_DISCOUNT_PERCENT = 30
VAT_PERCENT = 20
SHIPPING_KOPEKS = 49_000
FREE_DELIVERY_FROM_KOPEKS = 500_000
TIER_DISCOUNTS = ((10, 5), (25, 10), (50, 15))
REQUIRED_LINE_KEYS = ("sku", "qty", "unit_price_kopecks")


def _is_invalid_number(val: str, allow_zero: bool = False) -> bool:
    try:
        num = int(val)
        return num < 0 if allow_zero else num <= 0
    except ValueError:
        return True


def _validate_single_line(item: dict[str, str], seen_skus: set[str]) -> str | None:
    for key in REQUIRED_LINE_KEYS:
        if key not in item:
            return f"missing key {key}"
    sku = item["sku"]
    if not sku:
        return "empty sku"
    if sku in seen_skus:
        return f"duplicate sku {sku}"
    seen_skus.add(sku)
    if _is_invalid_number(item["qty"], allow_zero=False):
        return "invalid qty"
    if _is_invalid_number(item["unit_price_kopecks"], allow_zero=True):
        return "invalid price"
    return None


def validate_order(
    lines: list[dict[str, str]],
    promo_code: str = "",
    shipping_city: str = "",
) -> str | None:
    """Return a human readable reason why the order is invalid, or None if it is fine."""
    if not lines:
        return "empty lines"

    seen_skus: set[str] = set()
    for item in lines:
        error = _validate_single_line(item, seen_skus)
        if error:
            return error

    if promo_code and promo_code not in PROMO_CODES:
        return f"unknown promo code: {promo_code}"

    if shipping_city and shipping_city not in SUPPORTED_CITIES:
        return f"unsupported city: {shipping_city}"

    return None


def calculate_order_total(
    lines: list[dict[str, str]],
    promo_code: str = "",
    shipping_city: str = "",
) -> int | None:
    """Return the order total in kopecks, or None if the order is invalid."""
    if validate_order(lines, promo_code, shipping_city) is not None:
        return None

    subtotal = sum(int(item["qty"]) * int(item["unit_price_kopecks"]) for item in lines)
    total_qty = sum(int(item["qty"]) for item in lines)

    tier_discount = 0
    for threshold, percent in sorted(TIER_DISCOUNTS, key=lambda x: x[0]):
        if total_qty >= threshold:
            tier_discount = percent

    promo_discount = PROMO_CODES.get(promo_code, 0) if promo_code else 0
    best_discount = max(tier_discount, promo_discount)
    final_discount_percent = min(best_discount, MAX_DISCOUNT_PERCENT)

    discount = percent_of(subtotal, final_discount_percent)
    discounted_subtotal = subtotal - discount

    shipping = 0
    if shipping_city and discounted_subtotal < FREE_DELIVERY_FROM_KOPEKS:
        shipping = SHIPPING_KOPEKS

    base = discounted_subtotal + shipping
    vat = percent_of(base, VAT_PERCENT)
    return base + vat
