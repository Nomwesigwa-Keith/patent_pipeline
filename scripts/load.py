"""STEP 4: DATA LOADING

Loads cleaned CSV data into SQLite database.

Operations:
- Creates database schema from schema.sql
- Loads cleaned patent data into patents table
- Loads cleaned inventor data into inventors table
- Loads cleaned company data into companies table
- Loads relationships into relationships table
- Creates indexes for performance

Prerequisites:
- Cleaned CSV files must exist in data/clean/:
  - clean_patents.csv
  - clean_inventors.csv
  - clean_companies.csv
  - (relationship files)
- schema.sql must be available

Usage:
    python scripts/load.py
    python scripts/load.py --chunk-size 10000

Options:
    --chunk-size SIZE  Rows per chunk during loading (default: 50000)
                       Reduce for low-memory systems

Outputs:
- patent_pipeline.db (SQLite database file)
- Database tables:
  - patents
  - inventors
  - companies
  - relationships

Note:
    Database is stored in the current directory. Subsequent runs will overwrite.
"""

import sqlite3
import pandas as pd
import os
import argparse

CLEAN = "data/clean"
DB = "patent_pipeline.db"
DEFAULT_CHUNK_SIZE = 50000


def run_schema(conn):
    print("Creating tables from schema...")
    with open("sql/schema.sql", "r") as f:
        schema = f.read()
    conn.executescript(schema)
    print("  Tables created.")


def require_clean_files(files):
    missing = [f for f in files if not os.path.exists(os.path.join(CLEAN, f))]
    if missing:
        msg = "Missing cleaned inputs: " + ", ".join(missing)
        msg += ". Run scripts/extract.py and scripts/clean.py first."
        raise FileNotFoundError(msg)


def load_table(conn, csv_file, table_name, chunk_size):
    path = os.path.join(CLEAN, csv_file)
    conn.execute(f"DELETE FROM {table_name}")

    total = 0
    for chunk in pd.read_csv(path, dtype="string", chunksize=chunk_size):
        chunk.to_sql(table_name, conn, if_exists="append", index=False)
        total += len(chunk)

    print(f"  Loaded {total:,} rows into '{table_name}'.")


def parse_args():
    parser = argparse.ArgumentParser(description="Load cleaned patent CSVs into SQLite.")
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f"Rows per chunk while loading CSV files (default: {DEFAULT_CHUNK_SIZE}).",
    )
    parser.add_argument(
        "--stage",
        choices=["patents", "inventors", "companies", "relationships", "all"],
        default="all",
        help="Which stage to load: patents, inventors, companies, relationships, or all (default: all).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    print("=" * 50)
    print("STEP 3: LOADING INTO DATABASE")
    print("=" * 50)

    stage_files = {
        "patents": ["clean_patents.csv"],
        "inventors": ["clean_inventors.csv"],
        "companies": ["clean_companies.csv"],
        "relationships": ["clean_relationships.csv"],
        "all": [
            "clean_patents.csv",
            "clean_inventors.csv",
            "clean_companies.csv",
            "clean_relationships.csv",
        ],
    }

    require_clean_files(stage_files[args.stage])

    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    run_schema(conn)

    if args.stage in ["patents", "all"]:
        load_table(conn, "clean_patents.csv", "patents", args.chunk_size)
    if args.stage in ["inventors", "all"]:
        load_table(conn, "clean_inventors.csv", "inventors", args.chunk_size)
    if args.stage in ["companies", "all"]:
        load_table(conn, "clean_companies.csv", "companies", args.chunk_size)
    if args.stage in ["relationships", "all"]:
        load_table(conn, "clean_relationships.csv", "relationships", args.chunk_size)

    conn.commit()
    conn.close()

    print(f"\nDatabase ready: {DB}")