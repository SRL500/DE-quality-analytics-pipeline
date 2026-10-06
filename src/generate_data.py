"""
STEP 1 - Generate a realistic but MESSY e-commerce dataset.

Creates three CSVs in data/raw/: customers.csv, products.csv, orders.csv
and deliberately injects data-quality problems (NULLs, duplicates, invalid
values, orphan keys, inconsistent text). The injected counts are saved to
data/raw/injection_log.csv so we can later check that our quality checks
detect what we planted (a nice validation point for the report).
"""
import numpy as np
import pandas as pd
from common import RAW_DIR

SEED = 42
N_CUST, N_ORD = 1000, 20000
rng = np.random.default_rng(SEED)
log = []  # (table, issue, rows_affected)


def note(table, issue, n):
    log.append({"table": table, "issue": issue, "rows_affected": n})


# ----------------------------------------------------------------- products
catalog = {
    "Electronics": (1500, 45000, ["Wireless Earbuds", "Bluetooth Speaker", "Smartwatch", "Power Bank",
                                  "USB-C Hub", "Webcam", "Mechanical Keyboard", "Gaming Mouse",
                                  "Tablet", "LED Monitor", "Smart Bulb", "Fitness Band"]),
    "Fashion": (400, 4000, ["Cotton T-Shirt", "Denim Jeans", "Running Shoes", "Hoodie", "Leather Wallet",
                            "Sunglasses", "Backpack", "Formal Shirt", "Sneakers", "Jacket",
                            "Wrist Watch", "Cap"]),
    "Home & Kitchen": (300, 8000, ["Air Fryer", "Mixer Grinder", "Bedsheet Set", "Cookware Set",
                                   "Water Bottle", "Vacuum Cleaner", "Table Lamp", "Storage Box",
                                   "Electric Kettle", "Wall Clock", "Pillow Pair", "Dinner Set"]),
    "Books": (150, 900, ["Python Basics", "Data Engineering Guide", "SQL Cookbook", "Machine Learning Intro",
                         "Cloud Computing", "Statistics Made Easy", "Algorithms Handbook", "Novel Collection",
                         "Self Help Classic", "History of India", "Business Strategy", "Exam Prep Guide"]),
    "Beauty": (200, 2500, ["Face Wash", "Moisturiser", "Sunscreen", "Shampoo", "Perfume", "Lip Balm",
                           "Hair Serum", "Face Mask", "Body Lotion", "Beard Oil", "Kajal", "Hair Dryer"]),
}
rows, pid = [], 1
for cat, (lo, hi, names) in catalog.items():
    for nm in names:
        rows.append({"product_id": f"P{pid:03d}", "product_name": nm, "category": cat,
                     "price": round(float(rng.uniform(lo, hi)), 2)})
        pid += 1
products = pd.DataFrame(rows).astype(object)
N_PROD = len(products)
idx = rng.choice(N_PROD, 3, replace=False)
products.loc[idx, "category"] = None
note("products", "missing category", 3)

# ---------------------------------------------------------------- customers
first = ["Aarav", "Riya", "Kabir", "Ananya", "Vihaan", "Diya", "Arjun", "Isha", "Rahul", "Neha"]
last = ["Sharma", "Patel", "Iyer", "Nair", "Singh", "Khan", "Das", "Reddy", "Joshi", "Mehta"]
cities = ["Mumbai", "Pune", "Delhi", "Bengaluru", "Chennai", "Hyderabad", "Kolkata", "Ahmedabad"]
cust = pd.DataFrame({
    "customer_id": [f"C{i:04d}" for i in range(1, N_CUST + 1)],
    "first": rng.choice(first, N_CUST),
    "last": rng.choice(last, N_CUST),
    "city": rng.choice(cities, N_CUST, p=[.22, .14, .16, .18, .09, .08, .07, .06]),
    "signup_date": pd.to_datetime("2022-01-01") + pd.to_timedelta(rng.integers(0, 1260, N_CUST), unit="D"),
})
cust["name"] = cust["first"] + " " + cust["last"]
cust["email"] = (cust["first"] + "." + cust["last"] + cust["customer_id"].str[1:] + "@example.com").str.lower()
cust["signup_date"] = cust["signup_date"].dt.strftime("%Y-%m-%d")
customers = cust[["customer_id", "name", "email", "city", "signup_date"]].astype(object)

perm = rng.permutation(N_CUST)
miss, bad, citv = perm[:40], perm[40:70], perm[70:320]
customers.loc[miss, "email"] = None
note("customers", "missing email", len(miss))
customers.loc[bad, "email"] = ["bad.email#mail.com", "no_domain@", "user@mail", "plainaddress", "x y@mail.com"] * 6
note("customers", "invalid email format", len(bad))
for k, i in enumerate(citv):
    c = customers.at[i, "city"]
    customers.at[i, "city"] = [c.lower(), c.upper(), f"  {c} "][k % 3]
note("customers", "inconsistent city text (case/whitespace)", len(citv))
dups = customers.sample(15, random_state=1)
customers = pd.concat([customers, dups], ignore_index=True)
note("customers", "duplicate customer rows", 15)

# ------------------------------------------------------------------- orders
cw = 1 / np.arange(1, N_CUST + 1) ** 0.5
cw /= cw.sum()
pw = rng.uniform(0.5, 2.0, N_PROD)
pw /= pw.sum()
days = pd.date_range("2024-01-01", "2025-12-31")
dw = np.where(days.month.isin([10, 11]), 1.8, 1.0)
dw = dw / dw.sum()

pi = rng.choice(N_PROD, N_ORD, p=pw)
price = products["price"].astype(float).values[pi]
orders = pd.DataFrame({
    "order_id": [f"ORD{100000 + i}" for i in range(N_ORD)],
    "customer_id": [f"C{i:04d}" for i in rng.choice(np.arange(1, N_CUST + 1), N_ORD, p=cw)],
    "product_id": products["product_id"].values[pi],
    "quantity": rng.choice([1, 2, 3, 4, 5], N_ORD, p=[.5, .25, .12, .08, .05]),
    "unit_price": np.round(price * rng.uniform(0.9, 1.0, N_ORD), 2),
    "order_date": rng.choice(days, N_ORD, p=dw),
    "status": rng.choice(["delivered", "shipped", "pending", "cancelled", "returned"], N_ORD,
                         p=[.70, .08, .05, .09, .08]),
    "payment_method": rng.choice(["upi", "card", "cod", "netbanking"], N_ORD, p=[.45, .30, .15, .10]),
})
orders["order_date"] = pd.to_datetime(orders["order_date"]).dt.strftime("%Y-%m-%d")
orders = orders.astype(object)

p = rng.permutation(N_ORD)
cut = np.cumsum([5, 200, 60, 100, 150, 100, 40, 100, 200])
s = np.split(p, cut)  # disjoint row sets, one per issue
orders.loc[s[0], "order_id"] = None;               note("orders", "missing order_id", len(s[0]))
orders.loc[s[1], "customer_id"] = None;            note("orders", "missing customer_id", len(s[1]))
orders.loc[s[2], "customer_id"] = "C9999";         note("orders", "unknown customer_id (orphan)", len(s[2]))
orders.loc[s[3], "product_id"] = "P999";           note("orders", "unknown product_id (orphan)", len(s[3]))
orders.loc[s[4], "quantity"] = rng.choice(["0", "-1", "-3", "abc"], len(s[4]))
note("orders", "invalid quantity (<=0 or text)", len(s[4]))
orders.loc[s[5], "unit_price"] = None;             note("orders", "missing unit_price", len(s[5]))
orders.loc[s[6], "unit_price"] = [-abs(float(x)) for x in orders.loc[s[6], "unit_price"]]
note("orders", "negative unit_price", len(s[6]))
orders.loc[s[7], "unit_price"] = [round(float(x) * 100, 2) for x in orders.loc[s[7], "unit_price"]]
note("orders", "price outlier (x100)", len(s[7]))
half = len(s[8]) // 2
orders.loc[s[8][:half], "order_date"] = rng.choice(["2024-02-30", "N/A", "31/12/2024", "2025-13-01"], half)
note("orders", "invalid order_date", half)
orders.loc[s[8][half:], "order_date"] = "2031-05-14"
note("orders", "future order_date", len(s[8]) - half)

# text inconsistencies (can overlap with other issues)
v = rng.choice(N_ORD, 3000, replace=False)
orders.loc[v, "status"] = [x.upper() if k % 2 == 0 else f" {x} "
                           for k, x in enumerate(orders.loc[v, "status"])]
note("orders", "inconsistent status text", len(v))
w = rng.choice(N_ORD, 2000, replace=False)
orders.loc[w, "payment_method"] = [x.lower() if k % 2 == 0 else f" {x} "
                                   for k, x in enumerate(orders.loc[w, "payment_method"])]
note("orders", "inconsistent payment_method text", len(w))

dup = orders[orders["order_id"].notna()].sample(400, random_state=7)
orders = pd.concat([orders, dup], ignore_index=True).sample(frac=1, random_state=3).reset_index(drop=True)
note("orders", "exact duplicate rows", 400)

# -------------------------------------------------------------------- write
customers.sample(frac=1, random_state=5).to_csv(RAW_DIR / "customers.csv", index=False)
products.to_csv(RAW_DIR / "products.csv", index=False)
orders.to_csv(RAW_DIR / "orders.csv", index=False)
pd.DataFrame(log).to_csv(RAW_DIR / "injection_log.csv", index=False)

print(f"customers: {len(customers)} rows | products: {len(products)} rows | orders: {len(orders)} rows")
print(pd.DataFrame(log).to_string(index=False))
