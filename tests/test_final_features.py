from src.final_aggregations import list_aggregations, run_aggregation
from src.final_queries import INDEX_DEFINITIONS, list_queries
from src.materialized_views import list_views
from src.scheduled_jobs import JOB_DEFINITIONS

def test_final_catalogs_meet_requirements():
    assert len(list_queries()) >= 5
    assert len(INDEX_DEFINITIONS) >= 3
    assert any(len(keys) >= 2 for keys, _ in INDEX_DEFINITIONS.values())
    assert len(list_aggregations()) >= 5
    assert len(list_views()) >= 2
    assert len(JOB_DEFINITIONS) >= 2

def test_aggregation_reports_return_real_results_with_mock_db():
    class Collection:
        def aggregate(self, pipeline, allowDiskUse=True):
            return [{"_id": "2025-01-01", "orders": 1, "sales": 20}]
    class DB:
        def __getitem__(self, name):
            return Collection()
    result = run_aggregation(DB(), "sales_by_day")
    assert result["count"] == 1 and result["results"][0]["sales"] == 20

def test_all_five_aggregations_return_results():
    import mongomock
    db = mongomock.MongoClient().db
    db.orders_validated.insert_many([
        {"order_id": "O1", "customer_id": "C1", "price": 100.0, "currency": "YER", "order_date": "2025-01-01", "order_status": "PAID", "items": [{"sku": "A", "qty": 2}]},
        {"order_id": "O2", "customer_id": "C2", "price": 50.0, "currency": "YER", "order_date": "2025-01-02", "order_status": "COMPLETED", "items": [{"sku": "B", "qty": 1}]},
    ])
    for name in ("sales_by_day", "top_products", "top_customers", "orders_by_status", "price_summary"):
        result = run_aggregation(db, name)
        assert result["count"] >= 1 and result["results"]

def test_materialized_view_replay_does_not_duplicate_contributions():
    import mongomock
    from datetime import datetime, timezone
    from src.materialized_views import refresh_view, read_view
    db = mongomock.MongoClient().db
    db.orders_validated.insert_one({"order_id": "O1", "order_date": "2025-01-01", "price": 20.0,
                                    "items": [{"sku": "A", "qty": 2}], "updated_at": datetime.now(timezone.utc)})
    refresh_view(db, "daily_sales_summary")
    refresh_view(db, "daily_sales_summary")
    assert read_view(db, "daily_sales_summary")["results"][0]["sales"] == 20.0
    refresh_view(db, "top_products_summary")
    refresh_view(db, "top_products_summary")
    assert read_view(db, "top_products_summary")["results"][0]["sales"] == 40.0

def test_api_exposes_required_refresh_mv_route():
    from src.api import app
    paths = {route.path for route in app.routes}
    assert "/refresh-mv" in paths
