import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "big_data_midterm")
COLLECTION_RAW = "orders_raw"
COLLECTION_VALIDATED = "orders_validated"
COLLECTION_QUARANTINE = "orders_quarantine"
SMALL_FILE_THRESHOLD_MB = float(os.getenv("SMALL_FILE_THRESHOLD_MB", "200"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5000"))
MONGO_BATCH_SIZE = int(os.getenv("MONGO_BATCH_SIZE", "1000"))
REPORTS_DIR = os.getenv("REPORTS_DIR", str(PROJECT_ROOT / "reports"))
RESULTS_FILE = os.path.join(REPORTS_DIR, "results.json")
EXPLAIN_REPORT_FILE = os.path.join(REPORTS_DIR, "explain_results.json")
SPARK_APP_NAME = os.getenv("SPARK_APP_NAME", "HybridDataPipeline")
SPARK_MASTER = os.getenv("SPARK_MASTER", "local[*]")
ENABLE_SCHEDULER = os.getenv("ENABLE_SCHEDULER", "false").lower() == "true"
API_TITLE = "Hybrid Data Pipeline API"
API_VERSION = "2.0.0"
