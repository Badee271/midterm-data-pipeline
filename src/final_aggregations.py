from config.settings import COLLECTION_VALIDATED

AGGREGATION_NAMES = {
    "sales_by_day": "Sales totals and order count by day",
    "top_products": "Top products from order items",
    "top_customers": "Top customers by spend",
    "orders_by_status": "Order distribution by status",
    "price_summary": "Order value summary by currency",
}

def _run(db, pipeline, name, limit=100):
    rows = list(db[COLLECTION_VALIDATED].aggregate(pipeline, allowDiskUse=True))
    for row in rows:
        if "_id" in row:
            row["group"] = row.pop("_id")
    return {"name": name, "count": len(rows), "results": rows[:limit]}

def list_aggregations():
    return [{"name": key, "description": value} for key, value in AGGREGATION_NAMES.items()]

def run_aggregation(db, name, limit=100):
    if name == "sales_by_day":
        return _run(db, [{"$match": {"order_date": {"$nin": [None, ""]}}}, {"$group": {"_id": "$order_date", "orders": {"$sum": 1}, "sales": {"$sum": "$price"}}}, {"$sort": {"_id": 1}}], name, limit)
    if name == "top_products":
        return _run(db, [{"$unwind": "$items"}, {"$project": {"product": {"$ifNull": ["$items.sku", {"$ifNull": ["$items.product_id", "$items.name"]}]}, "quantity": {"$ifNull": ["$items.qty", 1]}, "sales": {"$multiply": ["$price", {"$ifNull": ["$items.qty", 1]}]}}}, {"$group": {"_id": "$product", "units": {"$sum": "$quantity"}, "sales": {"$sum": "$sales"}}}, {"$sort": {"sales": -1}}, {"$limit": limit}], name, limit)
    if name == "top_customers":
        return _run(db, [{"$group": {"_id": "$customer_id", "orders": {"$sum": 1}, "total_spend": {"$sum": "$price"}}}, {"$sort": {"total_spend": -1}}, {"$limit": limit}], name, limit)
    if name == "orders_by_status":
        return _run(db, [{"$group": {"_id": {"$ifNull": ["$order_status", "UNKNOWN"]}, "orders": {"$sum": 1}, "sales": {"$sum": "$price"}}}, {"$sort": {"orders": -1}}], name, limit)
    if name == "price_summary":
        return _run(db, [{"$group": {"_id": {"$ifNull": ["$currency", "YER"]}, "orders": {"$sum": 1}, "average_price": {"$avg": "$price"}, "min_price": {"$min": "$price"}, "max_price": {"$max": "$price"}}}], name, limit)
    raise KeyError(f"Unknown aggregation: {name}")
