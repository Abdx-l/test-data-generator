from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from generate import export_csv, generate


class GeneratorTests(unittest.TestCase):
    def test_reproducible_and_relational(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a, b = root / "a.db", root / "b.db"
            counts = generate(a, 17, 2, 120, 19, True)
            generate(b, 17, 2, 120, 19, True)
            self.assertEqual(counts, {"customers": 17, "accounts": 34, "transactions": 120, "edge_cases": 6})
            with closing(sqlite3.connect(a)) as x, closing(sqlite3.connect(b)) as y:
                self.assertEqual(x.execute("SELECT * FROM transactions").fetchall(), y.execute("SELECT * FROM transactions").fetchall())
                self.assertEqual(x.execute("PRAGMA foreign_key_check").fetchall(), [])
                self.assertEqual(x.execute("SELECT count(*) FROM edge_cases WHERE date='2024-02-29'").fetchone()[0], 6)
                self.assertEqual(x.execute("SELECT count(*) FROM transactions WHERE amount_cents<=0").fetchone()[0], 0)
            export_csv(a, root / "csv")
            self.assertEqual(len((root / "csv" / "transactions.csv").read_text().splitlines()), 121)
            with self.assertRaises(FileExistsError):
                generate(a, 1, 1, 1, 1)


if __name__ == "__main__":
    unittest.main()

