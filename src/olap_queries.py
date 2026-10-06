"""
STEP 5 - OLAP / analytical queries on the CLEAN tables.
Each query is saved to reports/olap/<name>.csv and printed.
Revenue counts only 'delivered' and 'shipped' orders (cancelled/returned excluded).
"""
from common import OLAP_DIR, get_con

REV = "o.status IN ('delivered', 'shipped')"

QUERIES = {
    "01_kpi_summary": f"""
        SELECT COUNT(*) AS orders, COUNT(DISTINCT o.customer_id) AS customers,
               ROUND(SUM(o.revenue), 2) AS revenue, ROUND(AVG(o.revenue), 2) AS avg_order_value
        FROM clean.orders o WHERE {REV}""",

    "02_monthly_revenue": f"""
        WITH m AS (
            SELECT strftime(o.order_date, '%Y-%m') AS month, SUM(o.revenue) AS revenue
            FROM clean.orders o WHERE {REV} GROUP BY 1)
        SELECT month, ROUND(revenue, 2) AS revenue,
               ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
                     / LAG(revenue) OVER (ORDER BY month), 1) AS mom_growth_pct,
               ROUND(AVG(revenue) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2)
                     AS rolling_3m_avg
        FROM m ORDER BY month""",

    "03_top_products": f"""
        SELECT p.product_name, p.category, SUM(o.quantity) AS units, ROUND(SUM(o.revenue), 2) AS revenue
        FROM clean.orders o JOIN clean.products p ON o.product_id = p.product_id
        WHERE {REV} GROUP BY 1, 2 ORDER BY revenue DESC LIMIT 10""",

    "04_category_share": f"""
        SELECT p.category, ROUND(SUM(o.revenue), 2) AS revenue,
               ROUND(100.0 * SUM(o.revenue) / SUM(SUM(o.revenue)) OVER (), 1) AS share_pct
        FROM clean.orders o JOIN clean.products p ON o.product_id = p.product_id
        WHERE {REV} GROUP BY 1 ORDER BY revenue DESC""",

    "05_revenue_by_city": f"""
        SELECT c.city, COUNT(*) AS orders, ROUND(SUM(o.revenue), 2) AS revenue
        FROM clean.orders o JOIN clean.customers c ON o.customer_id = c.customer_id
        WHERE {REV} GROUP BY 1 ORDER BY revenue DESC""",

    "06_payment_mix": f"""
        SELECT o.payment_method, COUNT(*) AS orders,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS share_pct
        FROM clean.orders o WHERE {REV} GROUP BY 1 ORDER BY orders DESC""",

    "07_customer_segments": f"""
        WITH spend AS (
            SELECT o.customer_id, SUM(o.revenue) AS total_spend
            FROM clean.orders o WHERE {REV} GROUP BY 1),
        tiers AS (SELECT *, NTILE(4) OVER (ORDER BY total_spend DESC) AS quartile FROM spend)
        SELECT CASE quartile WHEN 1 THEN 'Platinum' WHEN 2 THEN 'Gold'
                             WHEN 3 THEN 'Silver' ELSE 'Bronze' END AS segment,
               COUNT(*) AS customers, ROUND(SUM(total_spend), 2) AS revenue,
               ROUND(AVG(total_spend), 2) AS avg_spend
        FROM tiers GROUP BY 1 ORDER BY revenue DESC""",

    "08_cancel_return_by_category": """
        SELECT p.category, COUNT(*) AS orders,
               SUM(CASE WHEN o.status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled,
               SUM(CASE WHEN o.status = 'returned'  THEN 1 ELSE 0 END) AS returned,
               ROUND(100.0 * SUM(CASE WHEN o.status IN ('cancelled','returned') THEN 1 ELSE 0 END)
                     / COUNT(*), 1) AS cancel_return_rate_pct
        FROM clean.orders o JOIN clean.products p ON o.product_id = p.product_id
        GROUP BY 1 ORDER BY cancel_return_rate_pct DESC""",
}


def main():
    con = get_con()
    for name, sql in QUERIES.items():
        df = con.execute(sql).df()
        df.to_csv(OLAP_DIR / f"{name}.csv", index=False)
        print(f"\n[olap] {name}")
        print(df.head(12).to_string(index=False))
    con.close()


if __name__ == "__main__":
    main()
