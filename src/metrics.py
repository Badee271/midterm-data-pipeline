import json
import os
from config.settings import REPORTS_DIR, RESULTS_FILE

def save_metrics(metrics_data):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    results = []
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, encoding="utf-8") as stream:
                value = json.load(stream)
                results = value if isinstance(value, list) else [value]
        except (OSError, json.JSONDecodeError):
            results = []
    results.append(metrics_data)
    with open(RESULTS_FILE, "w", encoding="utf-8") as stream:
        json.dump(results, stream, indent=2, ensure_ascii=False, default=str)
    print(f"[Metrics] saved to {RESULTS_FILE}")
