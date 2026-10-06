# Business Report - E-Commerce Orders (auto-generated)

## Data quality
- Overall quality score: **96.75% (raw) -> 99.65% (clean)**
- Rules checked: 20 | rules with failures on raw data: 17 | on clean data: 1
- Remaining issues are unrecoverable values (e.g. missing emails), which are flagged, not guessed.

## Key business insights
- Net revenue: **200,029,756** from 15,026 orders and 1,000 customers (average order value 13,312).
- Best month: **2024-10** with revenue 13,984,033.
- Top product: **Smartwatch** (Electronics), revenue 25,278,561.
- Platinum customers (top 25%) generate **57%** of revenue.
- Highest cancel/return rate: **Home & Kitchen** at 17.5%.

## Performance
- Benchmark dataset: 964,250 rows. CSV = 68.3 MB, Parquet = 1.98 MB
  (compression x34.5). See reports/benchmark.csv and reports/charts/benchmark.png.

## Recommendations
1. Enforce NOT NULL / CHECK constraints and allowed-value lists at the source system.
2. Validate emails and dates at the entry form; normalise text (case/whitespace) on write.
3. Reduce Home & Kitchen cancellations/returns (product descriptions, delivery SLAs).
4. Store analytical data as Parquet for faster scans and smaller storage.
