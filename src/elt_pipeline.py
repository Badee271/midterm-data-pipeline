from collections import Counter
from datetime import datetime, timezone
from pymongo import UpdateOne
from config.settings import COLLECTION_QUARANTINE, COLLECTION_RAW, COLLECTION_VALIDATED
from src.mongo_setup import get_db
from src.quality_rules import process_record

def process_elt_transformation(run_id):
    db = get_db()
    raw_col, valid_col, quarantine_col = db[COLLECTION_RAW], db[COLLECTION_VALIDATED], db[COLLECTION_QUARANTINE]
    counts = {"valid_count": 0, "corrected_count": 0, "quarantine_count": 0, "inserted_count": 0, "updated_count": 0, "unchanged_count": 0}
    error_case_counts = Counter()
    for raw_doc in raw_col.find({"run_id": run_id}).batch_size(1000):
        raw_record = dict(raw_doc.get("raw_record") or {})
        if not isinstance(raw_record, dict):
            raw_record = {}
        raw_record.update({"run_id": run_id, "source_file": raw_doc.get("source_file"), "source_row_number": raw_doc.get("source_row_number")})
        validated_doc, errors, status = process_record(raw_record)
        if errors:
            counts["quarantine_count"] += 1
            codes = [item["code"] for item in errors]
            error_case_counts.update(codes)
            quarantine_col.insert_one({"run_id": run_id, "source_file": raw_doc.get("source_file"),
                "source_row_number": raw_doc.get("source_row_number"), "order_id": raw_record.get("order_id"),
                "error_codes": codes, "error_details": errors, "raw_record": raw_record,
                "quarantined_at": datetime.now(timezone.utc)})
            continue
        counts["corrected_count" if status == "corrected" else "valid_count"] += 1
        result = valid_col.update_one({"order_id": validated_doc["order_id"]}, {"$set": validated_doc}, upsert=True)
        if result.upserted_id is not None:
            counts["inserted_count"] += 1
        elif result.modified_count:
            counts["updated_count"] += 1
        else:
            counts["unchanged_count"] += 1
    counts["error_case_counts"] = dict(error_case_counts)
    return counts
