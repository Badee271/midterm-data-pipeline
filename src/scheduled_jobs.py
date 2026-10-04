import logging
import os
from datetime import datetime, timezone
from src.materialized_views import refresh_view
from src.mongo_setup import close_mongo, get_db

logger = logging.getLogger("hybrid_pipeline.jobs")
logging.basicConfig(level=logging.INFO)
JOB_DEFINITIONS = {
    "refresh_daily_sales": {"schedule": "every 15 minutes", "view": "daily_sales_summary"},
    "refresh_top_products": {"schedule": "every 30 minutes", "view": "top_products_summary"},
}

def run_job(name):
    if name not in JOB_DEFINITIONS:
        raise KeyError(f"Unknown job: {name}")
    started = datetime.now(timezone.utc)
    logger.info("job=%s status=started at=%s", name, started.isoformat())
    try:
        result = refresh_view(get_db(), JOB_DEFINITIONS[name]["view"])
        finished = datetime.now(timezone.utc)
        logger.info("job=%s status=success at=%s", name, finished.isoformat())
        return {"job": name, "status": "success", "started_at": started, "finished_at": finished, "result": result}
    except Exception as exc:
        finished = datetime.now(timezone.utc)
        logger.exception("job=%s status=failed at=%s", name, finished.isoformat())
        return {"job": name, "status": "failed", "started_at": started, "finished_at": finished, "error": repr(exc)}
    finally:
        close_mongo()

def start_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(lambda: run_job("refresh_daily_sales"), "interval", minutes=15, id="refresh_daily_sales", replace_existing=True)
    scheduler.add_job(lambda: run_job("refresh_top_products"), "interval", minutes=30, id="refresh_top_products", replace_existing=True)
    scheduler.start()
    return scheduler
