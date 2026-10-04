from contextlib import asynccontextmanager
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from config.settings import API_TITLE, API_VERSION, ENABLE_SCHEDULER, EXPLAIN_REPORT_FILE
from src.final_aggregations import list_aggregations, run_aggregation
from src.final_queries import create_indexes, explain_before_after, list_queries, run_query
from src.materialized_views import list_views, read_view, refresh_view
from src.mongo_setup import get_db
from src.scheduled_jobs import JOB_DEFINITIONS, run_job

_scheduler = None

@asynccontextmanager
async def lifespan(app):
    global _scheduler
    if ENABLE_SCHEDULER:
        from src.scheduled_jobs import start_scheduler
        _scheduler = start_scheduler()
    yield
    if _scheduler:
        _scheduler.shutdown(wait=False)

app = FastAPI(title=API_TITLE, version=API_VERSION, description="Unified API for the hybrid MongoDB data pipeline", lifespan=lifespan)

class IngestRequest(BaseModel):
    file_path: str = Field(..., description="Path to a dirty CSV file")

@app.get("/health")
def health():
    try:
        get_db().command("ping")
        return {"status": "ok", "mongodb": "reachable", "version": API_VERSION}
    except Exception as exc:
        return {"status": "degraded", "mongodb": "unreachable", "error": str(exc), "version": API_VERSION}

@app.post("/ingest")
def ingest(payload: IngestRequest):
    try:
        from src.main import run_pipeline
        return run_pipeline(payload.file_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/indexes")
def indexes():
    try:
        return {"indexes": create_indexes(get_db())}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/queries")
def queries():
    return {"queries": list_queries()}

@app.get("/queries/{name}")
def query(name: str, limit: int = 100):
    try:
        return run_query(get_db(), name, limit)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/queries/{name}/explain")
def query_explain(name: str, limit: int = 100):
    try:
        from src.final_queries import explain_query
        return explain_query(get_db(), name, limit)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/indexes/explain")
def indexes_explain():
    try:
        result = explain_before_after(get_db())
        with open(EXPLAIN_REPORT_FILE, "w", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, ensure_ascii=False, default=str)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/aggregations")
def aggregations():
    return {"aggregations": list_aggregations()}

@app.get("/aggregations/{name}")
def aggregation(name: str, limit: int = 100):
    try:
        return run_aggregation(get_db(), name, limit)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/views")
def views():
    return {"views": list_views()}

@app.get("/views/{name}")
def view(name: str, limit: int = 100):
    try:
        return read_view(get_db(), name, limit)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/views/{name}/refresh")
def view_refresh(name: str):
    try:
        return refresh_view(get_db(), name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/views/{name}/run")
def view_run(name: str):
    return view_refresh(name)

@app.post("/refresh-mv")
def refresh_all_views():
    try:
        db = get_db()
        return {name: refresh_view(db, name) for name in ("daily_sales_summary", "top_products_summary")}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/jobs")
def jobs():
    return {"jobs": [{"name": name, **spec} for name, spec in JOB_DEFINITIONS.items()]}

@app.post("/jobs/{name}/run")
def job_run(name: str):
    try:
        return run_job(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
