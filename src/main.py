import os
import sys
import time
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.settings import BATCH_SIZE, SMALL_FILE_THRESHOLD_MB
from src.batch_loader import load_with_python_batch
from src.elt_pipeline import process_elt_transformation
from src.file_router import route_file
from src.metrics import save_metrics
from src.mongo_setup import close_mongo, setup_mongo_indexes

def run_pipeline(file_path):
    run_id = f"run_{uuid.uuid4().hex}"
    started = time.perf_counter()
    try:
        setup_mongo_indexes()
        engine, size_mb, reason = route_file(file_path)
        if engine == "python_batch":
            load_stats = load_with_python_batch(file_path, run_id)
        else:
            from src.spark_loader import load_with_pyspark
            load_stats = load_with_pyspark(file_path, run_id)
        stats = process_elt_transformation(run_id)
        elapsed = time.perf_counter() - started
        raw_loaded = load_stats["rows"]
        processed = stats["valid_count"] + stats["corrected_count"] + stats["quarantine_count"]
        metrics = {"run_id": run_id, "file_name": file_path, "file_size_mb": size_mb, "engine_used": engine,
            "routing_reason": reason, "rows_read": raw_loaded, "raw_loaded": raw_loaded, **stats,
            "elapsed_seconds": round(elapsed, 4), "throughput": round(raw_loaded / elapsed if elapsed else 0, 2),
            "settings": {"small_file_threshold_mb": SMALL_FILE_THRESHOLD_MB, "batch_size": BATCH_SIZE,
                         "partitions": load_stats.get("partitions"), "batches": load_stats.get("batches")},
            "consistency_check": {"expected": raw_loaded, "actual": processed, "passed": raw_loaded == processed},
            "load_stats": load_stats}
        save_metrics(metrics)
        print(f"[Pipeline] run_id={run_id} consistency={raw_loaded == processed}")
        return metrics
    finally:
        close_mongo()

def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m src.main <csv_path>")
    run_pipeline(sys.argv[1])

if __name__ == "__main__":
    main()
