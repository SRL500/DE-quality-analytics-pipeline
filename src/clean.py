"""
STEP 4 - CLEAN & TRANSFORM raw -> clean (typed, deduplicated, standardised).

Policy (document this in the report):
  * Fixable problems are FIXED: text trimmed/normalised, duplicates removed,
    bad/missing/outlier prices replaced by the catalog price (and flagged).
  * Unfixable problems are REJECTED into clean.rejected_orders with a reason,
    so nothing disappears silently (full audit trail).
"""
from common import get_con
from quality_checks import EMAIL_RE, VALID_STATUS


def main():
    con = get_con()
    con.execute("CREATE SCHEMA IF NOT EXISTS clean")

    # ---- products: type price, fill missing category
    con.execute("""
        CREATE OR REPLACE TABLE clean.products AS
        SELECT trim(product_id) AS product_id,
               trim(product_name) AS product_name,
               COALESCE(NULLIF(trim(category), ''), 'Uncategorized') AS category,
               TRY_CAST(price AS DOUBLE) AS price
        FROM raw.products
    """)

    # ---- customers: dedupe, normalise city, validate email, type dates
    con.execute(f"""
        CREATE OR REPLACE TABLE clean.customers AS
        SELECT customer_id, name,
               CASE WHEN email_clean <> '' AND regexp_matches(email_clean, '{EMAIL_RE}')
                    THEN email_clean END AS email,
               CASE WHEN email_clean = '' THEN 'missing'
                    WHEN regexp_matches(email_clean, '{EMAIL_RE}') THEN 'valid'
                    ELSE 'invalid' END AS email_status,
               upper(left(city_t, 1)) || lower(substr(city_t, 2)) AS city,
               TRY_CAST(signup_date AS DATE) AS signup_date
        FROM (
            SELECT trim(customer_id) AS customer_id, trim(name) AS name,
                   lower(trim(COALESCE(email, ''))) AS email_clean,
                   trim(city) AS city_t, signup_date,
                   ROW_NUMBER() OVER (PARTITION BY trim(customer_id)) AS rn
            FROM raw.customers
        ) WHERE rn = 1
    """)

    # ---- orders: stage with types, then flag rows with a reject reason
    con.execute("""
        CREATE OR REPLACE TABLE clean.orders_stage AS
        SELECT trim(order_id) AS order_id,
               NULLIF(trim(customer_id), '') AS customer_id,
               NULLIF(trim(product_id), '') AS product_id,
               TRY_CAST(quantity AS INTEGER) AS quantity,
               TRY_CAST(unit_price AS DOUBLE) AS unit_price_raw,
               TRY_CAST(order_date AS DATE) AS order_date,
               lower(trim(status)) AS status,
               lower(trim(payment_method)) AS payment_method,
               ROW_NUMBER() OVER (PARTITION BY trim(order_id)) AS rn
        FROM raw.orders
    """)
    con.execute(f"""
        CREATE OR REPLACE TABLE clean.orders_flagged AS
        SELECT s.*, p.price AS catalog_price,
          CASE
            WHEN s.order_id IS NULL OR s.order_id = ''            THEN 'missing_order_id'
            WHEN s.rn > 1                                         THEN 'duplicate_order_id'
            WHEN s.customer_id IS NULL                            THEN 'missing_customer_id'
            WHEN c.customer_id IS NULL                            THEN 'unknown_customer_id'
            WHEN p.product_id IS NULL                             THEN 'unknown_product_id'
            WHEN s.quantity IS NULL OR s.quantity <= 0            THEN 'invalid_quantity'
            WHEN s.order_date IS NULL                             THEN 'invalid_order_date'
            WHEN s.order_date > CURRENT_DATE                      THEN 'future_order_date'
            WHEN s.status IS NULL OR s.status NOT IN {VALID_STATUS} THEN 'invalid_status'
          END AS reject_reason
        FROM clean.orders_stage s
        LEFT JOIN clean.products  p ON s.product_id  = p.product_id
        LEFT JOIN clean.customers c ON s.customer_id = c.customer_id
    """)
    con.execute("""
        CREATE OR REPLACE TABLE clean.orders AS
        SELECT order_id, customer_id, product_id, quantity,
               CASE WHEN unit_price_raw IS NULL OR unit_price_raw <= 0
                         OR unit_price_raw > 5 * catalog_price
                    THEN catalog_price ELSE unit_price_raw END AS unit_price,
               (unit_price_raw IS NULL OR unit_price_raw <= 0
                OR unit_price_raw > 5 * catalog_price) AS price_corrected,
               order_date, status, payment_method,
               quantity * CASE WHEN unit_price_raw IS NULL OR unit_price_raw <= 0
                                    OR unit_price_raw > 5 * catalog_price
                               THEN catalog_price ELSE unit_price_raw END AS revenue
        FROM clean.orders_flagged
        WHERE reject_reason IS NULL
    """)
    con.execute("""
        CREATE OR REPLACE TABLE clean.rejected_orders AS
        SELECT * EXCLUDE (rn, catalog_price) FROM clean.orders_flagged
        WHERE reject_reason IS NOT NULL
    """)
    con.execute("DROP TABLE clean.orders_stage")
    con.execute("DROP TABLE clean.orders_flagged")

    raw_n = con.execute("SELECT COUNT(*) FROM raw.orders").fetchone()[0]
    clean_n = con.execute("SELECT COUNT(*) FROM clean.orders").fetchone()[0]
    fixed = con.execute("SELECT COUNT(*) FROM clean.orders WHERE price_corrected").fetchone()[0]
    print(f"[clean] orders: raw={raw_n}  clean={clean_n}  rejected={raw_n - clean_n}  prices corrected={fixed}")
    print("[clean] rejected orders by reason:")
    print(con.execute("SELECT reject_reason, COUNT(*) AS rows FROM clean.rejected_orders "
                      "GROUP BY 1 ORDER BY 2 DESC").df().to_string(index=False))
    for t in ("customers", "products"):
        r = con.execute(f"SELECT COUNT(*) FROM raw.{t}").fetchone()[0]
        c = con.execute(f"SELECT COUNT(*) FROM clean.{t}").fetchone()[0]
        print(f"[clean] {t}: raw={r}  clean={c}")
    con.close()


if __name__ == "__main__":
    main()
