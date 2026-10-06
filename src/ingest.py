"""
STEP 2 - INGEST raw CSVs into DuckDB, exactly as they arrive.

We load every column as text (all_varchar=true) so that bad values such as
'N/A' or 'abc' are NOT rejected at load time. Detecting them is the job of
the quality-check step. Raw tables live in the `raw` schema and are never edited.
"""
from common import RAW_DIR, get_con


def main():
    con = get_con()
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    for table in ("customers", "products", "orders"):
        path = (RAW_DIR / f"{table}.csv").as_posix()
        con.execute(f"""
            CREATE OR REPLACE TABLE raw.{table} AS
            SELECT * FROM read_csv('{path}', header=true, all_varchar=true)
        """)
        n = con.execute(f"SELECT COUNT(*) FROM raw.{table}").fetchone()[0]
        print(f"[ingest] raw.{table}: {n} rows loaded")
    con.close()


if __name__ == "__main__":
    main()
