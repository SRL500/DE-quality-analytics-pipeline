"""Shared paths and helpers used by every pipeline step."""
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
BENCH_DIR = DATA_DIR / "bench"
REPORT_DIR = ROOT / "reports"
OLAP_DIR = REPORT_DIR / "olap"
CHART_DIR = REPORT_DIR / "charts"
DB_PATH = DATA_DIR / "pipeline.duckdb"

for d in (RAW_DIR, BENCH_DIR, REPORT_DIR, OLAP_DIR, CHART_DIR):
    d.mkdir(parents=True, exist_ok=True)


def get_con():
    """Open (or create) the DuckDB database file. DuckDB is embedded: no server needed."""
    return duckdb.connect(str(DB_PATH))
