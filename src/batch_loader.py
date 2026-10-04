import csv
import time
from datetime import datetime, timezone
from config.settings import BATCH_SIZE, COLLECTION_RAW
from src.mongo_setup import get_db

def load_with_python_batch(file_path, run_id):
    raw_col = get_db()[COLLECTION_RAW]
    total_rows, batch_no, batch = 0, 0, []
    batch_metrics, errors = [], []
    started = time.perf_counter()
    try:
        with open(file_path, "r", encoding="utf-8-sig", errors="replace", newline="") as infile:
            reader = csv.DictReader(infile)
            for row_idx, row in enumerate(reader, start=1):
                batch.append({"run_id": run_id, "source_file": file_path, "source_row_number": row_idx,
                              "ingested_at": datetime.now(timezone.utc), "engine_used": "python_batch",
                              "raw_record": dict(row)})
                total_rows += 1
                if len(batch) >= BATCH_SIZE:
                    batch_no += 1
                    batch_metrics.append(_insert_batch(raw_col, batch, batch_no, errors))
                    batch.clear()
            if batch:
                batch_no += 1
                batch_metrics.append(_insert_batch(raw_col, batch, batch_no, errors))
                batch.clear()
    finally:
        elapsed = time.perf_counter() - started
    print(f"[Python Batch] rows={total_rows} batches={batch_no} elapsed={elapsed:.3f}s throughput={total_rows/elapsed if elapsed else 0:.2f} rows/s")
    return {"rows": total_rows, "batches": batch_no, "elapsed_seconds": round(elapsed, 4),
            "throughput": round(total_rows / elapsed if elapsed else 0, 2), "batch_metrics": batch_metrics, "errors": errors}

def _insert_batch(raw_col, batch, batch_no, errors):
    started = time.perf_counter()
    try:
        result = raw_col.insert_many(batch, ordered=False)
        elapsed = time.perf_counter() - started
        rate = len(result.inserted_ids) / elapsed if elapsed else 0
        print(f"  batch={batch_no} rows={len(batch)} elapsed={elapsed:.3f}s rate={rate:.2f} rows/s")
        return {"batch_number": batch_no, "rows": len(batch), "elapsed_seconds": round(elapsed, 4), "throughput": round(rate, 2)}
    except Exception as exc:
        errors.append({"batch_number": batch_no, "rows": len(batch), "error": repr(exc)})
        print(f"  batch={batch_no} FAILED rows={len(batch)} error={exc}")
        raise
