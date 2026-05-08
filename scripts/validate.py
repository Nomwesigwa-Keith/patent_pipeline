"""VALIDATION SCRIPT

Smoke test validator for sample data and project setup.

Validations:
- Checks sample data file exists
- Verifies required columns are present
- Confirms data format is valid
- Used by CI/CD pipelines

Prerequisites:
- Sample data file: data/sample/sample_patents.csv

Usage:
    python scripts/validate.py

Expected Output:
    OK: sample dataset looks good
    Exit code: 0

Error Codes:
    0 - Success
    2 - Sample file not found
    3 - Sample file is empty
    4 - Missing required columns

Required Columns:
    - patent_id
    - title
    - abstract
"""
from __future__ import annotations

import csv
from pathlib import Path
import sys


def main() -> int:
    sample = Path("data/sample/sample_patents.csv")
    if not sample.exists():
        print("ERROR: sample data not found at data/sample/sample_patents.csv")
        return 2

    with sample.open("r", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        try:
            header = next(reader)
        except StopIteration:
            print("ERROR: sample file is empty")
            return 3

    expected = {"patent_id", "title", "abstract"}
    found = set(h.strip() for h in header)
    missing = expected - found
    if missing:
        print(f"ERROR: missing expected columns: {sorted(missing)}")
        return 4

    print("OK: sample dataset looks good")
    return 0


if __name__ == "__main__":
    sys.exit(main())
