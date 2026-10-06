"""
STEP 3 - DATA QUALITY CHECKS (run on raw data BEFORE cleaning, and on clean data AFTER).

Every rule is one SQL query that counts the rows that FAIL the rule.
    pass_rate = (total_rows - failed_rows) / total_rows * 100
    overall quality score = average pass rate across all rules
Dimensions covered: completeness, uniqueness, validity, consistency,
integrity (referential), accuracy.
"""
import sys
import pandas as pd
from common import REPORT_DIR, get_con

EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
VALID_STATUS = "('pending','shipped','delivered','cancelled','returned')"


def where(table, cond):
    return f"SELECT COUNT(*) FROM {{s}}.{table} t WHERE {cond}"


def build_rules():
    """(table, rule_name, dimension, description, SQL returning the failing-row count). {s} = schema."""
    return [
        # ---------------- orders
        ("orders", "order_id_missing", "Completeness", "order_id is NULL/blank",
         where("orders", "t.order_id IS NULL OR trim(t.order_id) = ''")),
        ("orders", "order_id_duplicate", "Uniqueness", "order_id appears more than once (extra copies)",
         "SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM {s}.orders WHERE order_id IS NOT NULL"),
        ("orders", "customer_id_missing", "Completeness", "customer_id is NULL/blank",
         where("orders", "t.customer_id IS NULL OR trim(t.customer_id) = ''")),
        ("orders", "customer_unknown", "Integrity", "customer_id not found in customers",
         where("orders", "t.customer_id IS NOT NULL AND NOT EXISTS "
                         "(SELECT 1 FROM {s}.customers c WHERE c.customer_id = t.customer_id)")),
        ("orders", "product_unknown", "Integrity", "product_id not found in products",
         where("orders", "NOT EXISTS (SELECT 1 FROM {s}.products p WHERE p.product_id = t.product_id)")),
        ("orders", "quantity_invalid", "Validity", "quantity is not a positive integer",
         where("orders", "TRY_CAST(t.quantity AS INTEGER) IS NULL OR TRY_CAST(t.quantity AS INTEGER) <= 0")),
        ("orders", "unit_price_invalid", "Validity", "unit_price is NULL, text or <= 0",
         where("orders", "TRY_CAST(t.unit_price AS DOUBLE) IS NULL OR TRY_CAST(t.unit_price AS DOUBLE) <= 0")),
        ("orders", "unit_price_outlier", "Accuracy", "unit_price > 5x the catalog price",
         where("orders", "TRY_CAST(t.unit_price AS DOUBLE) > 5 * (SELECT MAX(TRY_CAST(p.price AS DOUBLE)) "
                         "FROM {s}.products p WHERE p.product_id = t.product_id)")),
        ("orders", "order_date_invalid", "Validity", "order_date is not a valid YYYY-MM-DD date",
         where("orders", "TRY_CAST(t.order_date AS DATE) IS NULL")),
        ("orders", "order_date_future", "Validity", "order_date is in the future",
         where("orders", "TRY_CAST(t.order_date AS DATE) > CURRENT_DATE")),
        ("orders", "status_invalid", "Validity", "status not in the allowed list",
         where("orders", f"t.status IS NULL OR lower(trim(t.status)) NOT IN {VALID_STATUS}")),
        ("orders", "status_inconsistent", "Consistency", "status not trimmed/lower-case",
         where("orders", "t.status <> lower(trim(t.status))")),
        ("orders", "payment_inconsistent", "Consistency", "payment_method not trimmed/lower-case",
         where("orders", "t.payment_method <> lower(trim(t.payment_method))")),
        # ---------------- customers
        ("customers", "customer_id_duplicate", "Uniqueness", "customer_id appears more than once (extra copies)",
         "SELECT COUNT(*) - COUNT(DISTINCT customer_id) FROM {s}.customers"),
        ("customers", "email_missing", "Completeness", "email is NULL/blank",
         where("customers", "t.email IS NULL OR trim(t.email) = ''")),
        ("customers", "email_invalid", "Validity", "email has an invalid format",
         where("customers", "t.email IS NOT NULL AND trim(t.email) <> '' "
                            f"AND NOT regexp_matches(trim(t.email), '{EMAIL_RE}')")),
        ("customers", "city_inconsistent", "Consistency", "city not in Title case / has extra spaces",
         where("customers", "t.city <> (upper(left(trim(t.city), 1)) || lower(substr(trim(t.city), 2)))")),
        ("customers", "signup_date_invalid", "Validity", "signup_date is not a valid date",
         where("customers", "TRY_CAST(t.signup_date AS DATE) IS NULL")),
        # ---------------- products
        ("products", "price_invalid", "Validity", "price is NULL, text or <= 0",
         where("products", "TRY_CAST(t.price AS DOUBLE) IS NULL OR TRY_CAST(t.price AS DOUBLE) <= 0")),
        ("products", "category_missing", "Completeness", "category is NULL/blank",
         where("products", "t.category IS NULL OR trim(t.category) = ''")),
    ]


def run(schema):
    con = get_con()
    totals = {t: con.execute(f"SELECT COUNT(*) FROM {schema}.{t}").fetchone()[0]
              for t in ("orders", "customers", "products")}
    out = []
    for table, rule, dim, desc, sql in build_rules():
        failed = con.execute(sql.replace("{s}", schema)).fetchone()[0]
        total = totals[table]
        out.append({"table": table, "rule": rule, "dimension": dim, "description": desc,
                    "total_rows": total, "failed_rows": failed,
                    "pass_rate_pct": round(100.0 * (total - failed) / total, 2)})
    con.close()
    return pd.DataFrame(out)


def main(schema="raw"):
    df = run(schema)
    path = REPORT_DIR / f"quality_{schema}.csv"
    df.to_csv(path, index=False)
    print(f"\n[quality] results on schema '{schema}':")
    print(df[["table", "rule", "dimension", "failed_rows", "pass_rate_pct"]].to_string(index=False))
    print(f"[quality] OVERALL QUALITY SCORE ({schema}): {df['pass_rate_pct'].mean():.2f}%  -> saved {path.name}")
    return df


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "raw")
