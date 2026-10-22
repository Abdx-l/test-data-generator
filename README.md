# Test Data Generator

Generate repeatable customer, account, and transaction fixtures with consistent foreign keys. Amounts use a lognormal distribution. The optional boundary set contains zero and negative amounts, long and Unicode names, duplicate emails, and a leap day for testing validation rules.

```sh
python generate.py --customers 100 --accounts-per-customer 2 --transactions 1000 --seed 42 --database sample.db --csv-dir export
python generate.py --customers 10 --transactions 50 --edge-cases --database edge.db
python -m unittest discover -s tests -v
```

The normal rows are stored in foreign-keyed SQLite tables. Boundary records live in a separate `edge_cases` table with an expected failure label, so invalid fixtures cannot silently corrupt the valid dataset. The same rows can be exported as CSV.

