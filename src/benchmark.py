"""
STEP 6 - PERFORMANCE: CSV vs Parquet vs native DuckDB table.

The clean orders are replicated SCALE times (~1M rows) so the differences are
measurable. Each query is run once as warm-up and then RUNS times; the median is reported.
Also saves EXPLAIN ANALYZE of one query (for the 'performance analysis' section).
"""
import statistics
import time
import pandas as pd
from common import BENCH_DIR, REPORT_DIR, get_con

SCALE, RUNS = 50, 5


def main():
    con = get_con()
    con.execute(f"CREATE OR REPLACE TABLE bench AS SELECT o.* FROM clean.orders o, range({SCALE}) r")
    rows = con.execute("SELECT COUNT(*) FROM bench").fetchone()[0]
    csv_p = (BENCH_DIR / "orders_big.csv").as_posix()
    pq_p = (BENCH_DIR / "orders_big.parquet").as_posix()
    con.execute(f"COPY (SELECT * FROM bench) TO '{csv_p}' (HEADER, DELIMITER ',')")
    con.execute(f"COPY (SELECT * FROM bench) TO '{pq_p}' (FORMAT PARQUET)")
    size_csv = (BENCH_DIR / "orders_big.csv").stat().st_size / 1e6
    size_pq = (BENCH_DIR / "orders_big.parquet").stat().st_size / 1e6
    print(f"[bench] rows={rows:,} | CSV={size_csv:.1f} MB | Parquet={size_pq:.1f} MB "
          f"| compression x{size_csv / size_pq:.1f}")

    sources = {"CSV": f"read_csv('{csv_p}', header=true)",
               "Parquet": f"read_parquet('{pq_p}')",
               "DuckDB table": "bench"}
    queries = {
        "Q1 group by status": "SELECT status, COUNT(*), SUM(revenue) FROM {src} GROUP BY status",
        "Q2 monthly revenue": "SELECT strftime(order_date, '%Y-%m') AS m, SUM(revenue) FROM {src} "
                              "WHERE status IN ('delivered','shipped') GROUP BY 1 ORDER BY 1",
        "Q3 top products 2025": "SELECT product_id, SUM(revenue) AS r FROM {src} "
                                "WHERE order_date >= DATE '2025-01-01' GROUP BY 1 ORDER BY r DESC LIMIT 10",
    }
    results = []
    for qn, q in queries.items():
        for fmt, src in sources.items():
            sql = q.replace("{src}", src)
            con.execute(sql).fetchall()  # warm-up
            times = []
            for _ in range(RUNS):
                t0 = time.perf_counter()
                con.execute(sql).fetchall()
                times.append(time.perf_counter() - t0)
            results.append({"query": qn, "format": fmt, "median_sec": round(statistics.median(times), 4)})
    df = pd.DataFrame(results)
    df.to_csv(REPORT_DIR / "benchmark.csv", index=False)
    pd.DataFrame([{"rows": rows, "csv_mb": round(size_csv, 2), "parquet_mb": round(size_pq, 2)}]) \
        .to_csv(REPORT_DIR / "benchmark_sizes.csv", index=False)
    print(df.pivot(index="query", columns="format", values="median_sec").to_string())

    plan = con.execute("EXPLAIN ANALYZE " + queries["Q3 top products 2025"].replace(
        "{src}", sources["Parquet"])).fetchall()
    (REPORT_DIR / "explain_analyze_parquet_q3.txt").write_text("\n".join(str(r[-1]) for r in plan), encoding="utf-8")
    con.execute("DROP TABLE bench")
    con.close()


if __name__ == "__main__":
    main()
