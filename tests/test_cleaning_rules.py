from src.quality_rules import process_record

def base(**changes):
    value = {"order_id": "O1", "customer_id": "C1", "price": "5000 ريال", "phone": "+967 777-123-456", "email": "user@@mail..com", "order_date": "31/01/2025", "order_status": "مؤكد", "items": "[{\"sku\": \"A\"}]"}
    value.update(changes)
    return value

def test_valid_record_is_valid():
    doc, errors, status = process_record(base(email="user@mail.com", phone="777123456", price="5000", order_date="2025-01-31", order_status="PAID"))
    assert errors == [] and status == "valid" and doc["order_id"] == "O1"

def test_arabic_digits_and_currency_are_audited():
    doc, errors, status = process_record(base(price="٥٠٠٠ ريال"))
    assert not errors and status == "corrected" and doc["price"] == 5000
    assert all(set(item) >= {"field", "original_value", "corrected_value", "rule_code"} for item in doc["corrections"])

def test_missing_order_id_is_quarantined():
    doc, errors, status = process_record(base(order_id=""))
    assert doc is None and status == "quarantine" and errors[0]["code"] == "MISSING_ORDER_ID"

def test_impossible_date_is_quarantined():
    doc, errors, status = process_record(base(order_date="31/02/2025"))
    assert doc is None and errors[0]["code"] == "INVALID_IMPOSSIBLE_DATE"

def test_corrupt_json_is_quarantined():
    doc, errors, status = process_record(base(items="not-json"))
    assert doc is None and errors[0]["code"] == "CORRUPTED_ITEMS_JSON"

def test_empty_items_are_quarantined():
    doc, errors, status = process_record(base(items="[]"))
    assert doc is None and errors[0]["code"] == "EMPTY_ITEMS"

def test_common_alternative_english_headers_work():
    record = {"Order Number": "O2", "Client ID": "C2", "Total Amount": "125,000.00", "Mobile": "777 123 456", "Mail": "buyer@example.com", "Created At": "2025/01/31", "State": "paid", "Products": "[{\"sku\": \"B\"}]"}
    doc, errors, status = process_record(record)
    assert not errors and doc["order_id"] == "O2" and doc["customer_id"] == "C2" and doc["price"] == 125000

def test_common_arabic_headers_work():
    record = {"رقم الطلب": "O3", "معرف العميل": "C3", "الإجمالي": "2500", "رقم الهاتف": "777123456", "البريد الإلكتروني": "buyer@example.com", "تاريخ الطلب": "31/01/2025", "حالة الطلب": "مؤكد", "المنتجات": "[{\"sku\": \"C\"}]"}
    doc, errors, status = process_record(record)
    assert not errors and doc["order_id"] == "O3" and doc["order_status"] == "COMPLETED"
