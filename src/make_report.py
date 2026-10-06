"""
STEP 7 - Build charts (reports/charts/*.png) and an auto-filled business report (reports/business_report.md).
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from common import CHART_DIR, OLAP_DIR, REPORT_DIR

NAVY, ORANGE = "#232F3E", "#FF9900"


def main():
    raw = pd.read_csv(REPORT_DIR / "quality_raw.csv")
    cln = pd.read_csv(REPORT_DIR / "quality_clean.csv")
    q = raw.merge(cln, on=["table", "rule"], suffixes=("_raw", "_clean"))
    q["label"] = q["table"] + "." + q["rule"]

    # 1. quality before vs after
    fig, ax = plt.subplots(figsize=(9, 7))
    y = range(len(q))
    ax.barh([i + 0.2 for i in y], q["pass_rate_pct_raw"], height=0.4, color=ORANGE, label="Raw")
    ax.barh([i - 0.2 for i in y], q["pass_rate_pct_clean"], height=0.4, color=NAVY, label="Clean")
    ax.set_yticks(list(y)); ax.set_yticklabels(q["label"], fontsize=8); ax.invert_yaxis()
    ax.set_xlim(80, 100.5); ax.set_xlabel("Pass rate (%)"); ax.legend()
    ax.set_title("Data quality: raw vs clean")
    fig.tight_layout(); fig.savefig(CHART_DIR / "quality_before_after.png", dpi=150); plt.close(fig)

    # 2. monthly revenue
    m = pd.read_csv(OLAP_DIR / "02_monthly_revenue.csv")
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(m["month"], m["revenue"], color=ORANGE, marker="o", label="Revenue")
    ax.plot(m["month"], m["rolling_3m_avg"], color=NAVY, linestyle="--", label="3-month rolling avg")
    ax.set_xticks(range(0, len(m), 2)); ax.set_xticklabels(m["month"][::2], rotation=45, fontsize=8)
    ax.set_title("Monthly revenue (delivered + shipped)"); ax.legend()
    fig.tight_layout(); fig.savefig(CHART_DIR / "monthly_revenue.png", dpi=150); plt.close(fig)

    # 3. category share
    c = pd.read_csv(OLAP_DIR / "04_category_share.csv")
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(c["category"], c["revenue"], color=NAVY)
    ax.set_title("Revenue by category"); plt.setp(ax.get_xticklabels(), rotation=20, fontsize=8)
    fig.tight_layout(); fig.savefig(CHART_DIR / "category_revenue.png", dpi=150); plt.close(fig)

    # 4. benchmark
    b = pd.read_csv(REPORT_DIR / "benchmark.csv").pivot(index="query", columns="format", values="median_sec")
    ax = b[["CSV", "Parquet", "DuckDB table"]].plot(kind="bar", figsize=(8, 4), color=[ORANGE, "#146EB4", NAVY])
    ax.set_ylabel("Median time (s)"); ax.set_title("Query time: CSV vs Parquet vs DuckDB table")
    plt.xticks(rotation=0, fontsize=8); plt.tight_layout()
    plt.savefig(CHART_DIR / "benchmark.png", dpi=150); plt.close()

    # business report (auto-filled)
    k = pd.read_csv(OLAP_DIR / "01_kpi_summary.csv").iloc[0]
    top = pd.read_csv(OLAP_DIR / "03_top_products.csv").iloc[0]
    seg = pd.read_csv(OLAP_DIR / "07_customer_segments.csv")
    best = m.loc[m["revenue"].idxmax()]
    crr = pd.read_csv(OLAP_DIR / "08_cancel_return_by_category.csv").iloc[0]
    sz = pd.read_csv(REPORT_DIR / "benchmark_sizes.csv").iloc[0]
    plat = seg[seg["segment"] == "Platinum"]["revenue"].sum() / seg["revenue"].sum() * 100
    md = f"""# Business Report - E-Commerce Orders (auto-generated)

## Data quality
- Overall quality score: **{raw['pass_rate_pct'].mean():.2f}% (raw) -> {cln['pass_rate_pct'].mean():.2f}% (clean)**
- Rules checked: {len(raw)} | rules with failures on raw data: {(raw['failed_rows'] > 0).sum()} | on clean data: {(cln['failed_rows'] > 0).sum()}
- Remaining issues are unrecoverable values (e.g. missing emails), which are flagged, not guessed.

## Key business insights
- Net revenue: **{k['revenue']:,.0f}** from {int(k['orders']):,} orders and {int(k['customers']):,} customers (average order value {k['avg_order_value']:,.0f}).
- Best month: **{best['month']}** with revenue {best['revenue']:,.0f}.
- Top product: **{top['product_name']}** ({top['category']}), revenue {top['revenue']:,.0f}.
- Platinum customers (top 25%) generate **{plat:.0f}%** of revenue.
- Highest cancel/return rate: **{crr['category']}** at {crr['cancel_return_rate_pct']}%.

## Performance
- Benchmark dataset: {int(sz['rows']):,} rows. CSV = {sz['csv_mb']} MB, Parquet = {sz['parquet_mb']} MB
  (compression x{sz['csv_mb'] / sz['parquet_mb']:.1f}). See reports/benchmark.csv and reports/charts/benchmark.png.

## Recommendations
1. Enforce NOT NULL / CHECK constraints and allowed-value lists at the source system.
2. Validate emails and dates at the entry form; normalise text (case/whitespace) on write.
3. Reduce {crr['category']} cancellations/returns (product descriptions, delivery SLAs).
4. Store analytical data as Parquet for faster scans and smaller storage.
"""
    (REPORT_DIR / "business_report.md").write_text(md, encoding="utf-8")
    print("[report] charts + business_report.md written to reports/")


if __name__ == "__main__":
    main()
