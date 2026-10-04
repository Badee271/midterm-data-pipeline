import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.settings import COLLECTION_VALIDATED
from src.main import run_pipeline
from src.mongo_setup import close_mongo, get_db


def check_idempotency(file_path):
    first = run_pipeline(file_path)
    after_first = get_db()[COLLECTION_VALIDATED].count_documents({})
    second = run_pipeline(file_path)
    after_second = get_db()[COLLECTION_VALIDATED].count_documents({})
    passed = after_second == after_first
    result = {
        "first_run_id": first["run_id"],
        "second_run_id": second["run_id"],
        "business_records_after_first": after_first,
        "business_records_after_second": after_second,
        "passed": passed,
    }
    print(result)
    close_mongo()
    if not passed:
        raise SystemExit("Idempotency check failed: business record count increased")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the same input twice and verify no duplicate business records")
    parser.add_argument("file_path")
    check_idempotency(parser.parse_args().file_path)
