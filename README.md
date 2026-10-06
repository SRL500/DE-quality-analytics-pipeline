# Data Quality + Analytics Pipeline (DuckDB)

ISE 2 Case Study - Data Engineering, Unit 6.1 + self-learning (Data Quality / Modern OLAP engines)
Practical #19: ingest raw CSV -> quality checks -> clean -> store in DuckDB -> OLAP queries -> business report.

Group: <fill in> | Members: Shree Selvaraj (124A8105), Tushar Singh (124A8110), Sri Muthu L (124A8111), Rohit Swami (124A8113)

## Pipeline
```
generate_data -> ingest (raw schema) -> quality checks (BEFORE) -> clean (clean schema + rejected_orders)
              -> quality checks (AFTER) -> OLAP queries -> CSV vs Parquet benchmark -> charts + business report
```

## How to run
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
python src/run_pipeline.py
```
Or step by step (from the project root): `python src/generate_data.py`, `python src/ingest.py`,
`python src/quality_checks.py raw`, `python src/clean.py`, `python src/quality_checks.py clean`,
`python src/olap_queries.py`, `python src/benchmark.py`, `python src/make_report.py`.

## Folder structure
| Path | Purpose |
|---|---|
| src/ | one script per pipeline stage |
| data/raw/ | messy input CSVs + injection_log.csv (what errors we planted) |
| data/pipeline.duckdb | the DuckDB database (raw, clean schemas) - created on run |
| reports/quality_raw.csv, quality_clean.csv | quality scorecards before / after |
| reports/olap/ | result of every analytical query |
| reports/benchmark*.csv, explain_analyze_*.txt | performance results |
| reports/charts/ | PNG charts for the report and PPT |
| reports/business_report.md | auto-generated business summary |

## Data quality rules
19 SQL rules across 6 dimensions (completeness, uniqueness, validity, consistency, integrity, accuracy).
Pass rate = (rows - failing rows) / rows. Overall score = mean pass rate.
Note: detected counts can be slightly higher than injection_log.csv because duplicated rows copy their errors.

## Cleaning policy
Fixable -> fixed (trim/normalise text, dedupe, replace missing/negative/outlier price with catalog price).
Unfixable -> moved to `clean.rejected_orders` with a reason (audit trail). Unrecoverable emails stay NULL and are flagged.
