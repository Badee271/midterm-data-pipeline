from datetime import datetime, timezone
from pymongo import ASCENDING, DESCENDING
from config.settings import COLLECTION_VALIDATED

QUERY_DEFINITIONS = {
    "orders_by_status": {"description": "Orders filtered by order status", "filter": {"order_status": "PAID"}, "sort": [("order_date", DESCENDING)]},
    "customer_orders": {"description": "Orders for one customer", "filter": {"customer_id": "C1001"}, "sort": [("order_date", DESCENDING)]},
    "orders_in_date_range": {"description": "Orders in a date range", "filter": {"order_date": {"$gte": "2025-01-01", "$lte": "2025-12-31"}}, "sort": [("order_date", ASCENDING)]},
    "high_value_orders": {"description": "High-value orders", "filter": {"price": {"$gte": 1000}}, "sort": [("price", DESCENDING)]},
    "recent_orders": {"description": "Recently updated orders", "filter": {}, "sort": [("updated_at", DESCENDING)]},
}

INDEX_DEFINITIONS = {
    "status_date": ([('order_status', ASCENDING), ('order_date', DESCENDING)], "Supports status filtering with date ordering"),
    "customer_date": ([('customer_id', ASCENDING), ('order_date', DESCENDING)], "Supports customer history ordered by date"),
    "price_desc": ([('price', DESCENDING)], "Supports high-value order sorting/filtering"),
}

def list_queries():
    return [{"name": name, "description": spec["description"], "filter": spec["filter"]} for name, spec in QUERY_DEFINITIONS.items()]

def run_query(db, name, limit=100):
    if name not in QUERY_DEFINITIONS:
        raise KeyError(f"Unknown query: {name}")
    spec = QUERY_DEFINITIONS[name]
    cursor = db[COLLECTION_VALIDATED].find(spec["filter"]).sort(spec["sort"]).limit(limit)
    return {"name": name, "count": cursor.collection.count_documents(spec["filter"]), "results": list(cursor)}

def create_indexes(db):
    created = []
    for name, (keys, purpose) in INDEX_DEFINITIONS.items():
        index_name = db[COLLECTION_VALIDATED].create_index(keys, name=f"ix_{name}")
        created.append({"name": name, "mongo_name": index_name, "keys": keys, "purpose": purpose})
    return created

def explain_query(db, name, limit=100):
    if name not in QUERY_DEFINITIONS:
        raise KeyError(f"Unknown query: {name}")
    spec = QUERY_DEFINITIONS[name]
    command = {"find": COLLECTION_VALIDATED, "filter": spec["filter"], "sort": dict(spec["sort"]), "limit": limit}
    explanation = db.command("explain", command, verbosity="executionStats")
    return {"name": name, "captured_at": datetime.now(timezone.utc), "execution_stats": explanation.get("executionStats", {}), "query_planner": explanation.get("queryPlanner", {})}

def explain_before_after(db, names=("orders_by_status", "customer_orders", "high_value_orders")):
    before = {name: explain_query(db, name) for name in names}
    indexes = create_indexes(db)
    after = {name: explain_query(db, name) for name in names}
    return {"before": before, "indexes": indexes, "after": after}
