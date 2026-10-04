import json
import re
from datetime import datetime
from typing import Any

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
PRICE_WORDS = {"ألفان": 2000, "الفان": 2000, "خمسة آلاف": 5000, "خمسه آلاف": 5000}
STATUS_MAP = {"مؤكد": "COMPLETED", "مدفوع": "PAID", "ملغي": "CANCELLED", "ملغى": "CANCELLED"}
ALIASES = {
    "order_id": ("order_id", "OrderID", "orderId", "order_number", "order_no", "order_code", "رقم_الطلب", "معرف_الطلب"),
    "customer_id": ("customer_id", "CustomerID", "customerId", "client_id", "buyer_id", "customer_number", "معرف_العميل"),
    "price": ("price", "Price", "amount", "total", "total_price", "order_total", "original_price", "السعر", "المبلغ", "الإجمالي"),
    "phone": ("phone", "Phone", "customer_phone", "mobile", "telephone", "رقم_الهاتف"),
    "email": ("email", "Email", "customer_email", "customer_email_address", "mail", "البريد_الإلكتروني"),
    "order_date": ("order_date", "OrderDate", "date", "created_at", "order_time", "تاريخ_الطلب"),
    "order_status": ("order_status", "Status", "status", "state", "حالة_الطلب"),
    "items": ("items", "Items", "order_items", "line_items", "products", "product_list", "items_json", "تفاصيل_الطلب", "المنتجات"),
}

def _key(value):
    return re.sub(r"[^\w]", "", str(value).strip().lower())

def _value(record: dict, name: str, default: Any = ""):
    normalized = {_key(key): value for key, value in record.items()}
    for key in ALIASES[name]:
        if _key(key) in normalized:
            return normalized[_key(key)]
    # Fallbacks make the pipeline tolerant of common instructor naming variations.
    fallback_tokens = {
        "order_id": ("order", "طلب"), "customer_id": ("customer", "client", "عميل"),
        "price": ("price", "amount", "total", "سعر", "مبلغ", "اجمالي"),
        "phone": ("phone", "mobile", "هاتف"), "email": ("email", "mail", "بريد"),
        "order_date": ("date", "time", "تاريخ"), "order_status": ("status", "state", "حالة"),
        "items": ("item", "product", "منتج", "تفاصيل"),
    }
    for original_key, value in record.items():
        key = _key(original_key)
        if any(token in key for token in fallback_tokens[name]):
            return value
    return default

def _audit(corrections, field, original, corrected, rule_code):
    if str(original) != str(corrected):
        corrections.append({"field": field, "original_value": original, "corrected_value": corrected, "rule_code": rule_code})

def _quarantine(code, details=None):
    return None, [{"code": code, "details": details or code}], "quarantine"

def _parse_price(raw):
    value = "" if raw is None else str(raw).strip().translate(ARABIC_DIGITS)
    if value in PRICE_WORDS:
        return float(PRICE_WORDS[value]), value, "PRICE_WORD_MAPPING"
    cleaned = re.sub(r"(ريال يمني|ريال|YER|\$)", "", value, flags=re.IGNORECASE)
    cleaned = cleaned.replace(",", "").strip()
    try:
        number = float(cleaned)
    except ValueError:
        return None, value, None
    return number, cleaned, "PRICE_NORMALIZED"

def process_record(raw_record: dict):
    corrections = []
    order_id = _value(raw_record, "order_id")
    customer_id = _value(raw_record, "customer_id")
    if order_id is None or str(order_id).strip().lower() in {"", "null", "none"}:
        return _quarantine("MISSING_ORDER_ID")
    if customer_id is None or str(customer_id).strip().lower() in {"", "null", "none"}:
        return _quarantine("MISSING_CUSTOMER_ID")

    price_raw = _value(raw_record, "price")
    price, price_clean, price_rule = _parse_price(price_raw)
    if price is None:
        return _quarantine("UNKNOWN_PRICE", {"value": price_raw})
    if price < 0:
        return _quarantine("AMBIGUOUS_NEGATIVE_VALUE", {"field": "price", "value": price_raw})
    price_text = str(price_raw or "").strip().translate(ARABIC_DIGITS)
    if price_rule == "PRICE_WORD_MAPPING" or re.search(r"[٠-٩,]|ريال|YER|\$", str(price_raw), re.IGNORECASE):
        _audit(corrections, "price", price_raw, price, price_rule or "PRICE_NORMALIZED")

    phone_raw = _value(raw_record, "phone")
    phone = str(phone_raw or "").translate(ARABIC_DIGITS)
    phone = re.sub(r"[\s()\-+]", "", phone)
    _audit(corrections, "phone", phone_raw, phone, "PHONE_FORMATTED")

    email_raw = _value(raw_record, "email")
    email = str(email_raw or "").strip()
    repaired_email = re.sub(r"@+", "@", email)
    repaired_email = re.sub(r"\.+", ".", repaired_email)
    _audit(corrections, "email", email_raw, repaired_email, "EMAIL_REPEATED_SYMBOLS")
    email = repaired_email
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return _quarantine("INVALID_EMAIL", {"value": email_raw})

    date_raw = _value(raw_record, "order_date")
    date_text = str(date_raw or "").strip()
    formatted_date = None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            formatted_date = datetime.strptime(date_text, fmt).strftime("%Y-%m-%d")
            break
        except ValueError:
            continue
    if date_text and formatted_date is None:
        return _quarantine("INVALID_IMPOSSIBLE_DATE", {"value": date_raw})
    _audit(corrections, "order_date", date_raw, formatted_date or date_text, "DATE_STANDARDIZED")

    status_raw = _value(raw_record, "order_status")
    status_text = str(status_raw or "").strip()
    status = STATUS_MAP.get(status_text, status_text.upper())
    _audit(corrections, "order_status", status_raw, status, "STATUS_NORMALIZED")

    items_raw = _value(raw_record, "items")
    if items_raw is None or str(items_raw).strip() in {"", "[]", "{}", "null", "None"}:
        return _quarantine("EMPTY_ITEMS")
    try:
        items = json.loads(items_raw) if isinstance(items_raw, str) else items_raw
    except (TypeError, json.JSONDecodeError):
        return _quarantine("CORRUPTED_ITEMS_JSON", {"value": items_raw})
    if not isinstance(items, (list, dict)) or (isinstance(items, list) and not items):
        return _quarantine("EMPTY_ITEMS")

    normalized_items = items
    if isinstance(items, list):
        normalized_items = []
        for item in items:
            if isinstance(item, dict):
                item = dict(item)
                if "qty" in item:
                    try:
                        quantity = float(item["qty"])
                        item["qty"] = int(quantity) if quantity.is_integer() else quantity
                    except (TypeError, ValueError):
                        item["qty"] = 1
                normalized_items.append(item)
            else:
                normalized_items.append(item)

    status_value = "corrected" if corrections else "valid"
    validated = {
        "order_id": str(order_id).strip(), "customer_id": str(customer_id).strip(),
        "price": price, "currency": "YER", "phone": phone, "email": email,
        "order_date": formatted_date or date_text, "order_status": status,
        "items": normalized_items, "quality_status": status_value, "corrections": corrections,
        "run_id": raw_record.get("run_id"), "source_file": raw_record.get("source_file"),
    }
    return validated, [], status_value
