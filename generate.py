"""Deterministic relational fixtures with an isolated boundary dataset."""
from __future__ import annotations

import argparse
from contextlib import closing
import csv
from datetime import date, timedelta
from pathlib import Path
import random
import sqlite3


SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE);
CREATE TABLE accounts(id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(id), kind TEXT NOT NULL);
CREATE TABLE transactions(id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id), date TEXT NOT NULL, amount_cents INTEGER NOT NULL CHECK(amount_cents > 0));
CREATE TABLE edge_cases(case_name TEXT PRIMARY KEY, customer_name TEXT, email TEXT, date TEXT, amount_cents INTEGER, expected_issue TEXT NOT NULL);
"""


def generate(database: Path, customers: int, accounts_per_customer: int, transactions: int, seed: int, edge_cases: bool = False) -> dict[str, int]:
    if customers < 1 or accounts_per_customer < 1 or transactions < 0:
        raise ValueError("customers and accounts must be positive; transactions cannot be negative")
    rng = random.Random(seed)
    first = ["Amira", "Noah", "Maya", "Liam", "Aaliyah", "Omar", "Sofia", "Ethan"]
    last = ["Khan", "Chen", "Martin", "Singh", "Patel", "Brown", "Haddad", "Nguyen"]
    database = Path(database)
    if database.exists():
        raise FileExistsError(f"Refusing to overwrite {database}")
    database.parent.mkdir(parents=True, exist_ok=True)
    try:
        with closing(sqlite3.connect(database)) as db:
            db.executescript(SCHEMA)
            with db:
                db.executemany("INSERT INTO customers VALUES(?,?,?)", ((i, f"{rng.choice(first)} {rng.choice(last)}", f"customer{i}@example.test") for i in range(1, customers + 1)))
                account_count = customers * accounts_per_customer
                db.executemany("INSERT INTO accounts VALUES(?,?,?)", ((i, (i-1)//accounts_per_customer+1, "checking" if i % 2 else "savings") for i in range(1, account_count + 1)))
                start = date(2024, 1, 1)
                rows = ((i, rng.randint(1, account_count), (start + timedelta(days=rng.randrange(730))).isoformat(), max(1, round(rng.lognormvariate(3.2, 0.9)*100))) for i in range(1, transactions + 1))
                db.executemany("INSERT INTO transactions VALUES(?,?,?,?)", rows)
                if edge_cases:
                    cases = [
                        ("zero amount", "Sam Lee", "zero@example.test", "2024-02-29", 0, "nonpositive amount"),
                        ("negative amount", "Sam Lee", "negative@example.test", "2024-02-29", -100, "nonpositive amount"),
                        ("long name", "X"*255, "long@example.test", "2024-02-29", 100, "name length boundary"),
                        ("unicode name", "???? ?", "unicode@example.test", "2024-02-29", 100, "unicode boundary"),
                        ("duplicate email", "Another User", "customer1@example.test", "2024-02-29", 100, "duplicate email"),
                        ("leap day", "Leap Day", "leap@example.test", "2024-02-29", 100, "leap date boundary"),
                    ]
                    db.executemany("INSERT INTO edge_cases VALUES(?,?,?,?,?,?)", cases)
        return {"customers": customers, "accounts": account_count, "transactions": transactions, "edge_cases": 6 if edge_cases else 0}
    except BaseException:
        database.unlink(missing_ok=True)
        raise


def export_csv(database: Path, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database)) as db:
        for table in ("customers", "accounts", "transactions", "edge_cases"):
            columns = [row[1] for row in db.execute(f"PRAGMA table_info({table})")]
            with (directory / f"{table}.csv").open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(columns)
                writer.writerows(db.execute(f"SELECT * FROM {table}"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--customers", type=int, default=100)
    parser.add_argument("--accounts-per-customer", type=int, default=2)
    parser.add_argument("--transactions", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--edge-cases", action="store_true")
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--csv-dir", type=Path)
    args = parser.parse_args()
    try:
        counts = generate(args.database, args.customers, args.accounts_per_customer, args.transactions, args.seed, args.edge_cases)
        if args.csv_dir:
            export_csv(args.database, args.csv_dir)
    except (ValueError, FileExistsError) as ex:
        parser.error(str(ex))
    print(counts)

