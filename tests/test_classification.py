from pathlib import Path
from src.file_router import route_file

def test_small_file_routes_to_python_batch(tmp_path, monkeypatch):
    source = tmp_path / "orders.csv"
    source.write_text("order_id\nO1\n", encoding="utf-8")
    monkeypatch.setenv("SMALL_FILE_THRESHOLD_MB", "200")
    engine, size_mb, reason = route_file(str(source))
    assert engine == "python_batch"
    assert size_mb >= 0 and "threshold" in reason
