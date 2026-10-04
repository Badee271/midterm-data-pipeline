from datetime import datetime, timezone
from pymongo import DESCENDING
from config.settings import COLLECTION_VALIDATED

VIEW_NAMES = {
    "daily_sales_summary": "Incremental daily sales totals",
    "top_products_summary": "Incremental product units and sales",
}
STATE_COLLECTION = "materialized_view_state"
CONTRIBUTIONS_COLLECTION = "materialized_view_contributions"


def list_views():
    return [{"name": name, "description": description} for name, description in VIEW_NAMES.items()]


def _apply_delta(db, view_name, key_field, key_value, delta, now):
    if not key_value:
        return
    collection = db[view_name]
    query = {key_field: key_value}
    collection.update_one(query, {"$inc": delta, "$set": {"updated_at": now}}, upsert=True)
    collection.delete_one({**query, "$expr": {"$lte": [{"$add": ["$orders", 0]}, 0]}}) if key_field == "date" else None


def _refresh_daily(db, match, now):
    rows = list(db[COLLECTION_VALIDATED].find(match, {"order_id": 1, "order_date": 1, "price": 1}))
    contributions = db[CONTRIBUTIONS_COLLECTION]
    processed = 0
    for doc in rows:
        order_id, date, sales = doc.get("order_id"), doc.get("order_date"), float(doc.get("price") or 0)
        if not order_id or not date:
            continue
        contribution_id = f"daily_sales_summary:{order_id}"
        old = contributions.find_one({"_id": contribution_id})
        if old and old.get("date") == date and float(old.get("sales", 0)) == sales and old.get("orders", 1) == 1:
            continue
        if old:
            _apply_delta(db, "daily_sales_summary", "date", old.get("date"), {"orders": -old.get("orders", 1), "sales": -old.get("sales", 0)}, now)
        _apply_delta(db, "daily_sales_summary", "date", date, {"orders": 1, "sales": sales}, now)
        contributions.replace_one({"_id": contribution_id}, {"_id": contribution_id, "view": "daily_sales_summary", "order_id": order_id, "date": date, "orders": 1, "sales": sales, "updated_at": now}, upsert=True)
        processed += 1
    return processed


def _refresh_products(db, match, now):
    rows = list(db[COLLECTION_VALIDATED].find(match, {"order_id": 1, "items": 1, "price": 1}))
    contributions = db[CONTRIBUTIONS_COLLECTION]
    processed = 0
    for doc in rows:
        order_id, price = doc.get("order_id"), float(doc.get("price") or 0)
        if not order_id:
            continue
        new_parts = {}
        for item in doc.get("items") or []:
            if not isinstance(item, dict):
                continue
            product = item.get("sku") or item.get("product_id") or item.get("name")
            if not product:
                continue
            units = float(item.get("qty") or 1)
            new_parts[str(product)] = {"units": units, "sales": price * units}
        contribution_id = f"top_products_summary:{order_id}"
        old = contributions.find_one({"_id": contribution_id})
        old_parts = old.get("products", {}) if old else {}
        if old_parts == new_parts:
            continue
        for product, values in old_parts.items():
            _apply_delta(db, "top_products_summary", "product", product, {"units": -values["units"], "sales": -values["sales"]}, now)
        for product, values in new_parts.items():
            _apply_delta(db, "top_products_summary", "product", product, {"units": values["units"], "sales": values["sales"]}, now)
        contributions.replace_one({"_id": contribution_id}, {"_id": contribution_id, "view": "top_products_summary", "order_id": order_id, "products": new_parts, "updated_at": now}, upsert=True)
        processed += 1
    return processed


def refresh_view(db, name):
    if name not in VIEW_NAMES:
        raise KeyError(f"Unknown view: {name}")
    state = db[STATE_COLLECTION].find_one({"_id": name}) or {"last_refresh": None, "runs": 0}
    match = {"updated_at": {"$gt": state["last_refresh"]}} if state.get("last_refresh") else {}
    now = datetime.now(timezone.utc)
    processed = _refresh_daily(db, match, now) if name == "daily_sales_summary" else _refresh_products(db, match, now)
    db[STATE_COLLECTION].update_one({"_id": name}, {"$set": {"last_refresh": now}, "$inc": {"runs": 1}}, upsert=True)
    return {"name": name, "processed_records": processed, "refreshed_at": now, "incremental": bool(state.get("last_refresh"))}


def read_view(db, name, limit=100):
    if name not in VIEW_NAMES:
        raise KeyError(f"Unknown view: {name}")
    return {"name": name, "results": list(db[name].find({}, {"_id": 0}).sort("updated_at", DESCENDING).limit(limit))}
