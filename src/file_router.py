import os
from config.settings import SMALL_FILE_THRESHOLD_MB

def route_file(file_path):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Source file not found: {file_path}")
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb <= SMALL_FILE_THRESHOLD_MB:
        engine = "python_batch"
        reason = f"file_size_mb ({size_mb:.2f}) <= threshold ({SMALL_FILE_THRESHOLD_MB:.2f})"
    else:
        engine = "pyspark"
        reason = f"file_size_mb ({size_mb:.2f}) > threshold ({SMALL_FILE_THRESHOLD_MB:.2f})"
    print(f"[Router] size={size_mb:.2f} MB engine={engine} reason={reason}")
    return engine, size_mb, reason
