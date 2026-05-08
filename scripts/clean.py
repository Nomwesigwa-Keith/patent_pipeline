"""STEP 3: DATA CLEANING

Cleans and normalizes extracted patent data:
- Removes duplicates and invalid records
- Standardizes field values and formats
- Handles missing/null values
- Performs data validation
- Generates cleaned CSV files for loading into database

Cleaning operations:
- Patents: Title/abstract cleanup, year extraction, deduplication
- Inventors: Name normalization, country standardization
- Companies: Name normalization, deduplication

Prerequisites:
- Raw extracted files must exist in data/clean/ (created by extract.py)

Usage:
    python scripts/clean.py

Outputs:
- Updated CSV files in data/clean/:
  - clean_patents.csv
  - clean_inventors.csv  
  - clean_companies.csv
"""

import argparse
import glob
import os
import sqlite3
import tempfile
import zlib
from contextlib import contextmanager

import pandas as pd

CLEAN = "data/clean"
RAW = "data/raw"
SEP = "\t"
DEFAULT_CHUNK_SIZE = 2000
DEFAULT_STAGE_CHUNK_INCREMENT = 0
SQLITE_BATCH_SIZE = 2000
SQLITE_IN_LIMIT = 900
PROGRESS_EVERY_N_CHUNKS = 50


def _clean_path(filename):
    return os.path.join(CLEAN, filename)


def _raw_path(filename):
    return os.path.join(RAW, filename)


def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def _extract_to_staging_if_missing(staging_file, raw_file, usecols, chunk_size, max_rows=None):
    staging_path = _clean_path(staging_file)
    if os.path.exists(staging_path):
        return staging_path

    raw_path = _raw_path(raw_file)
    if not os.path.exists(raw_path):
        raise FileNotFoundError(
            f"Missing required input files: {staging_file} and {raw_file}. "
            f"Check data/clean/ and data/raw/."
        )

    wrote_header = False
    total_rows = 0
    for chunk in pd.read_csv(
        raw_path,
        sep=SEP,
        usecols=usecols,
        dtype="string",
        chunksize=chunk_size,
    ):
        # Limit total rows if specified
        if max_rows and total_rows + len(chunk) > max_rows:
            chunk = chunk.head(max_rows - total_rows)

        chunk.to_csv(staging_path, index=False, mode="a", header=not wrote_header)
        wrote_header = True
        total_rows += len(chunk)

        if max_rows and total_rows >= max_rows:
            break

    return staging_path


def _load_csv_to_table(conn, csv_path, table_name, chunk_size):
    conn.execute(f"DROP TABLE IF EXISTS {table_name}")
    first = True
    for chunk in pd.read_csv(csv_path, dtype="string", chunksize=chunk_size):
        chunk.to_sql(table_name, conn, if_exists="replace" if first else "append", index=False)
        first = False


def _query_to_csv(conn, sql, out_path, chunk_size):
    if os.path.exists(out_path):
        os.remove(out_path)

    wrote_header = False
    for chunk in pd.read_sql_query(sql, conn, chunksize=chunk_size):
        chunk.to_csv(out_path, index=False, mode="a", header=not wrote_header)
        wrote_header = True


def _table_count(conn, table_name):
    return conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]


def _query_count(conn, sql):
    return conn.execute(f"SELECT COUNT(*) FROM ({sql})").fetchone()[0]


def _batch_iter(values, size):
    for i in range(0, len(values), size):
        yield values[i : i + size]


def _executemany_batched(conn, sql, rows, batch_size=SQLITE_BATCH_SIZE):
    if not rows:
        return

    cur = conn.cursor()
    for batch in _batch_iter(rows, batch_size):
        cur.executemany(sql, batch)


def _fetch_location_country_map(conn, location_ids):
    if not location_ids:
        return {}

    result = {}
    for loc_batch in _batch_iter(location_ids, SQLITE_IN_LIMIT):
        placeholders = ",".join("?" for _ in loc_batch)
        sql = f"SELECT location_id, disambig_country FROM locations WHERE location_id IN ({placeholders})"
        for location_id, disambig_country in conn.execute(sql, loc_batch):
            result[location_id] = disambig_country
    return result


def _cleanup_stale_temp_dbs():
    _ensure_dir(CLEAN)
    patterns = [
        os.path.join(CLEAN, "_cleaning_tmp_*.db"),
        os.path.join(CLEAN, "_cleaning_tmp_*.db-wal"),
        os.path.join(CLEAN, "_cleaning_tmp_*.db-shm"),
    ]
    for pattern in patterns:
        for path in glob.glob(pattern):
            try:
                os.remove(path)
            except OSError:
                pass


def _compress_text(value):
    if value is None or pd.isna(value):
        return None
    text = str(value)
    if text == "":
        return None
    return sqlite3.Binary(zlib.compress(text.encode("utf-8"), level=9))


def _decompress_text(value):
    if value is None:
        return None
    return zlib.decompress(bytes(value)).decode("utf-8")


@contextmanager
def _tmp_clean_db():
    _ensure_dir(CLEAN)
    fd, temp_db = tempfile.mkstemp(prefix="_cleaning_tmp_", suffix=".db", dir=CLEAN)
    os.close(fd)

    conn = sqlite3.connect(temp_db)
    try:
        conn.execute("PRAGMA journal_mode=OFF")
        conn.execute("PRAGMA synchronous=OFF")
        conn.execute("PRAGMA cache_size=-32768")
        conn.execute("PRAGMA temp_store=FILE")
        yield conn
    finally:
        conn.close()
        wal = temp_db + "-wal"
        shm = temp_db + "-shm"
        for path in [wal, shm, temp_db]:
            if os.path.exists(path):
                os.remove(path)


def clean_patents(chunk_size, max_rows=None):
    print("Cleaning patents...")

    patents_path = _extract_to_staging_if_missing(
        "raw_patents.csv",
        "g_patent.tsv",
        ["patent_id", "patent_type", "patent_date", "patent_title"],
        chunk_size,
        max_rows,
    )
    abstracts_path = _extract_to_staging_if_missing(
        "raw_abstracts.csv",
        "g_patent_abstract.tsv",
        ["patent_id", "patent_abstract"],
        chunk_size,
        max_rows,
    )

    with _tmp_clean_db() as conn:
        conn.create_function("decompress_text", 1, _decompress_text)
        conn.execute(
            """
            CREATE TABLE abstracts (
                patent_id TEXT PRIMARY KEY,
                patent_abstract BLOB
            )
            """
        )

        abstract_chunks = 0
        for chunk in pd.read_csv(abstracts_path, dtype="string", chunksize=chunk_size):
            filtered = chunk[chunk["patent_id"].notna()][["patent_id", "patent_abstract"]].copy()
            if filtered.empty:
                continue

            rows = [
                (
                    str(pid),
                    _compress_text(abs_text),
                )
                for pid, abs_text in filtered.itertuples(index=False, name=None)
            ]
            _executemany_batched(
                conn,
                "INSERT OR REPLACE INTO abstracts (patent_id, patent_abstract) VALUES (?, ?)",
                rows,
            )
            abstract_chunks += 1
            if abstract_chunks % PROGRESS_EVERY_N_CHUNKS == 0:
                print(f"  Loaded abstract chunks: {abstract_chunks}")
        conn.commit()

        conn.execute(
            """
            CREATE TABLE patents (
                patent_id TEXT PRIMARY KEY,
                patent_type TEXT,
                patent_date TEXT,
                patent_title BLOB
            )
            """
        )

        patent_chunks = 0
        for chunk in pd.read_csv(patents_path, dtype="string", chunksize=chunk_size):
            filtered = chunk[chunk["patent_id"].notna() & chunk["patent_title"].notna()].copy()
            if filtered.empty:
                continue

            filtered = filtered[filtered["patent_title"].str.strip() != ""]
            if filtered.empty:
                continue

            filtered = filtered[["patent_id", "patent_type", "patent_date", "patent_title"]]
            rows = [
                (
                    str(pid),
                    None if pd.isna(pat_type) else str(pat_type),
                    None if pd.isna(pat_date) else str(pat_date),
                    _compress_text(title),
                )
                for pid, pat_type, pat_date, title in filtered.itertuples(index=False, name=None)
            ]
            _executemany_batched(
                conn,
                "INSERT OR REPLACE INTO patents (patent_id, patent_type, patent_date, patent_title) VALUES (?, ?, ?, ?)",
                rows,
            )

            patent_chunks += 1
            if patent_chunks % PROGRESS_EVERY_N_CHUNKS == 0:
                print(f"  Loaded patent chunks: {patent_chunks}")
        conn.commit()

        _query_to_csv(
            conn,
            """
            SELECT
                p.patent_id,
                decompress_text(p.patent_title) AS title,
                decompress_text(a.patent_abstract) AS abstract,
                CASE
                    WHEN LENGTH(COALESCE(p.patent_date, '')) >= 10 THEN SUBSTR(p.patent_date, 1, 10)
                    ELSE NULL
                END AS filing_date,
                CASE
                    WHEN LENGTH(COALESCE(p.patent_date, '')) >= 4 THEN CAST(SUBSTR(p.patent_date, 1, 4) AS INTEGER)
                    ELSE NULL
                END AS year,
                p.patent_type
            FROM patents p
            LEFT JOIN abstracts a
              ON p.patent_id = a.patent_id
            """,
            _clean_path("clean_patents.csv"),
            chunk_size,
        )
        total = _query_count(
            conn,
            "SELECT p.patent_id FROM patents p LEFT JOIN abstracts a ON p.patent_id = a.patent_id",
        )

    print(f"  Done. {total:,} clean patent records.")


def clean_inventors(chunk_size, max_rows=None, filter_by_valid_patents=True):
    print("Cleaning inventors...")

    inventors_path = _extract_to_staging_if_missing(
        "raw_inventors.csv",
        "g_inventor_disambiguated.tsv",
        [
            "patent_id",
            "inventor_id",
            "disambig_inventor_name_first",
            "disambig_inventor_name_last",
            "location_id",
        ],
        chunk_size,
        max_rows,
    )
    locations_path = _extract_to_staging_if_missing(
        "raw_locations.csv",
        "g_location_disambiguated.tsv",
        ["location_id", "disambig_country", "disambig_city", "disambig_state"],
        chunk_size,
        max_rows,
    )

    with _tmp_clean_db() as conn:
        conn.create_function("decompress_text", 1, _decompress_text)
        conn.execute(
            """
            CREATE TABLE locations (
                location_id TEXT PRIMARY KEY,
                disambig_country TEXT
            )
            """
        )

        location_chunks = 0
        for chunk in pd.read_csv(locations_path, dtype="string", chunksize=chunk_size):
            filtered = chunk[chunk["location_id"].notna()][["location_id", "disambig_country"]].copy()
            if filtered.empty:
                continue

            filtered = filtered.drop_duplicates(subset=["location_id"], keep="last")
            rows = [
                (str(location_id), None if pd.isna(country) else str(country))
                for location_id, country in filtered.itertuples(index=False, name=None)
            ]
            _executemany_batched(
                conn,
                "INSERT OR REPLACE INTO locations (location_id, disambig_country) VALUES (?, ?)",
                rows,
            )

            location_chunks += 1
            if location_chunks % PROGRESS_EVERY_N_CHUNKS == 0:
                print(f"  Loaded location chunks: {location_chunks}")
        conn.commit()

        conn.execute(
            """
            CREATE TABLE clean_inventors (
                inventor_id TEXT PRIMARY KEY,
                name BLOB,
                country TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE inventor_relationships (
                patent_id TEXT NOT NULL,
                inventor_id TEXT NOT NULL,
                PRIMARY KEY (patent_id, inventor_id)
            )
            """
        )

        inventor_chunks = 0
        for chunk in pd.read_csv(inventors_path, dtype="string", chunksize=chunk_size):
            first = chunk["disambig_inventor_name_first"].fillna("").str.strip()
            last = chunk["disambig_inventor_name_last"].fillna("").str.strip()
            names = (first + " " + last).str.strip()

            chunk_location_ids = chunk["location_id"].dropna().astype("string").unique().tolist()
            location_country = _fetch_location_country_map(conn, chunk_location_ids)

            chunk = chunk.copy()
            chunk["name"] = names
            chunk["country"] = chunk["location_id"].astype("string").map(location_country)

            inventor_rows_df = chunk[
                chunk["inventor_id"].notna() & (chunk["name"] != "")
            ][["inventor_id", "name", "country"]].drop_duplicates(subset=["inventor_id"], keep="first")
            inventor_rows = [
                (
                    str(iid),
                    _compress_text(name),
                    None if pd.isna(country) else str(country),
                )
                for iid, name, country in inventor_rows_df.itertuples(index=False, name=None)
            ]
            _executemany_batched(
                conn,
                "INSERT OR IGNORE INTO clean_inventors (inventor_id, name, country) VALUES (?, ?, ?)",
                inventor_rows,
            )

            rel_rows_df = chunk[
                chunk["patent_id"].notna() & chunk["inventor_id"].notna()
            ][["patent_id", "inventor_id"]].drop_duplicates(keep="first")
            rel_rows = [
                (str(pid), str(iid))
                for pid, iid in rel_rows_df.itertuples(index=False, name=None)
            ]
            _executemany_batched(
                conn,
                "INSERT OR IGNORE INTO inventor_relationships (patent_id, inventor_id) VALUES (?, ?)",
                rel_rows,
            )

            inventor_chunks += 1
            if inventor_chunks % PROGRESS_EVERY_N_CHUNKS == 0:
                print(f"  Processed inventor chunks: {inventor_chunks}")
        conn.commit()

        main_db_path = os.path.join(os.getcwd(), "patent_pipeline.db")
        if filter_by_valid_patents and os.path.exists(main_db_path):
            print("  Filtering inventors by valid patent IDs...")
            conn.execute("ATTACH DATABASE ? AS source", (main_db_path,))
            conn.execute(
                """
                CREATE TABLE valid_patents AS
                SELECT patent_id FROM source.patents
                """
            )
            conn.commit()

            _query_to_csv(
                conn,
                """
                SELECT c.inventor_id, decompress_text(c.name) AS name, c.country
                FROM clean_inventors c
                INNER JOIN inventor_relationships ir ON c.inventor_id = ir.inventor_id
                INNER JOIN valid_patents vp ON ir.patent_id = vp.patent_id
                GROUP BY c.inventor_id, c.name, c.country
                """,
                _clean_path("clean_inventors.csv"),
                chunk_size,
            )
            _query_to_csv(
                conn,
                """
                SELECT ir.patent_id, ir.inventor_id
                FROM inventor_relationships ir
                INNER JOIN valid_patents vp ON ir.patent_id = vp.patent_id
                """,
                _clean_path("inventor_relationships.csv"),
                chunk_size,
            )

            inventor_total = _query_count(
                conn,
                """
                SELECT COUNT(DISTINCT c.inventor_id)
                FROM clean_inventors c
                INNER JOIN inventor_relationships ir ON c.inventor_id = ir.inventor_id
                INNER JOIN valid_patents vp ON ir.patent_id = vp.patent_id
                """,
            )
            rel_total = _query_count(
                conn,
                """
                SELECT COUNT(*)
                FROM inventor_relationships ir
                INNER JOIN valid_patents vp ON ir.patent_id = vp.patent_id
                """,
            )
        else:
            if filter_by_valid_patents:
                print("  Warning: Main database not found, exporting all inventors")
            else:
                print("  Skipping patent-ID filtering, exporting all inventors")

            _query_to_csv(
                conn,
                "SELECT inventor_id, decompress_text(name) AS name, country FROM clean_inventors",
                _clean_path("clean_inventors.csv"),
                chunk_size,
            )
            _query_to_csv(
                conn,
                "SELECT patent_id, inventor_id FROM inventor_relationships",
                _clean_path("inventor_relationships.csv"),
                chunk_size,
            )

            inventor_total = _table_count(conn, "clean_inventors")
            rel_total = _table_count(conn, "inventor_relationships")

    print(f"  Done. {inventor_total:,} unique inventors, {rel_total:,} relationships.")


def clean_companies(chunk_size, max_rows=None):
    print("Cleaning companies...")

    assignees_path = _extract_to_staging_if_missing(
        "raw_assignees.csv",
        "g_assignee_disambiguated.tsv",
        [
            "patent_id",
            "assignee_id",
            "disambig_assignee_organization",
            "disambig_assignee_individual_name_first",
            "disambig_assignee_individual_name_last",
            "location_id",
        ],
        chunk_size,
        max_rows,
    )

    with _tmp_clean_db() as conn:
        conn.create_function("decompress_text", 1, _decompress_text)
        conn.execute(
            """
            CREATE TABLE clean_companies (
                company_id TEXT PRIMARY KEY,
                name BLOB
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE assignee_relationships (
                patent_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                PRIMARY KEY (patent_id, company_id)
            )
            """
        )

        for chunk in pd.read_csv(assignees_path, dtype="string", chunksize=chunk_size):
            organization = chunk["disambig_assignee_organization"].fillna("").str.strip()
            first = chunk["disambig_assignee_individual_name_first"].fillna("").str.strip()
            last = chunk["disambig_assignee_individual_name_last"].fillna("").str.strip()
            individual = (first + " " + last).str.strip()

            chunk = chunk.copy()
            chunk["name"] = organization.where(organization != "", individual)

            company_rows_df = chunk[
                chunk["assignee_id"].notna() & (chunk["name"] != "")
            ][["assignee_id", "name"]].drop_duplicates(subset=["assignee_id"], keep="first")
            company_rows = [
                (str(cid), _compress_text(name))
                for cid, name in company_rows_df.itertuples(index=False, name=None)
            ]
            _executemany_batched(
                conn,
                "INSERT OR IGNORE INTO clean_companies (company_id, name) VALUES (?, ?)",
                company_rows,
            )

            rel_rows_df = chunk[
                chunk["patent_id"].notna() & chunk["assignee_id"].notna()
            ][["patent_id", "assignee_id"]].drop_duplicates(keep="first")
            rel_rows = [
                (str(pid), str(cid))
                for pid, cid in rel_rows_df.itertuples(index=False, name=None)
            ]
            _executemany_batched(
                conn,
                "INSERT OR IGNORE INTO assignee_relationships (patent_id, company_id) VALUES (?, ?)",
                rel_rows,
            )
        conn.commit()

        # Filter by valid patent IDs during CSV export
        main_db_path = os.path.join(os.getcwd(), "patent_pipeline.db")
        if os.path.exists(main_db_path):
            print("  Filtering companies by valid patent IDs...")
            # Attach the external database under a non-default alias and cache valid patents
            conn.execute("ATTACH DATABASE ? AS source", (main_db_path,))
            conn.execute(
                """
                CREATE TABLE valid_patents AS
                SELECT patent_id FROM source.patents
                """
            )
            conn.commit()

            _query_to_csv(
                conn,
                """
                SELECT c.company_id, decompress_text(c.name) AS name
                FROM clean_companies c
                INNER JOIN assignee_relationships ar ON c.company_id = ar.company_id
                INNER JOIN valid_patents vp ON ar.patent_id = vp.patent_id
                GROUP BY c.company_id, c.name
                """,
                _clean_path("clean_companies.csv"),
                chunk_size,
            )
            _query_to_csv(
                conn,
                """
                SELECT ar.patent_id, ar.company_id
                FROM assignee_relationships ar
                INNER JOIN valid_patents vp ON ar.patent_id = vp.patent_id
                """,
                _clean_path("assignee_relationships.csv"),
                chunk_size,
            )

            company_total = _query_count(
                conn,
                """
                SELECT COUNT(DISTINCT c.company_id)
                FROM clean_companies c
                INNER JOIN assignee_relationships ar ON c.company_id = ar.company_id
                INNER JOIN valid_patents vp ON ar.patent_id = vp.patent_id
                """
            )
            rel_total = _query_count(
                conn,
                """
                SELECT COUNT(*)
                FROM assignee_relationships ar
                INNER JOIN valid_patents vp ON ar.patent_id = vp.patent_id
                """
            )
        else:
            print("  Warning: Main database not found, exporting all companies")
            _query_to_csv(
                conn,
                "SELECT company_id, decompress_text(name) AS name FROM clean_companies",
                _clean_path("clean_companies.csv"),
                chunk_size,
            )
            _query_to_csv(
                conn,
                "SELECT patent_id, company_id FROM assignee_relationships",
                _clean_path("assignee_relationships.csv"),
                chunk_size,
            )

            company_total = _table_count(conn, "clean_companies")
            rel_total = _table_count(conn, "assignee_relationships")

    print(f"  Done. {company_total:,} unique companies, {rel_total:,} relationships.")


def build_relationships(chunk_size, max_rows=None):
    print("Building relationships table...")

    required = ["inventor_relationships.csv", "assignee_relationships.csv"]
    missing = [f for f in required if not os.path.exists(_clean_path(f))]
    if missing:
        raise FileNotFoundError(
            "Missing cleaned relationship inputs: " + ", ".join(missing) + ". "
            "Run scripts/clean.py to regenerate them."
        )

    out_path = _clean_path("clean_relationships.csv")
    if os.path.exists(out_path):
        os.remove(out_path)

    wrote_header = False
    total = 0

    for chunk in pd.read_csv(_clean_path("inventor_relationships.csv"), dtype="string", chunksize=chunk_size):
        out_chunk = chunk[chunk["patent_id"].notna() & chunk["inventor_id"].notna()][["patent_id", "inventor_id"]].copy()
        if out_chunk.empty:
            continue
        out_chunk["company_id"] = pd.NA
        out_chunk = out_chunk[["patent_id", "inventor_id", "company_id"]]
        out_chunk.to_csv(out_path, index=False, mode="a", header=not wrote_header)
        wrote_header = True
        total += len(out_chunk)

    for chunk in pd.read_csv(_clean_path("assignee_relationships.csv"), dtype="string", chunksize=chunk_size):
        out_chunk = chunk[chunk["patent_id"].notna() & chunk["company_id"].notna()][["patent_id", "company_id"]].copy()
        if out_chunk.empty:
            continue
        out_chunk["inventor_id"] = pd.NA
        out_chunk = out_chunk[["patent_id", "inventor_id", "company_id"]]
        out_chunk.to_csv(out_path, index=False, mode="a", header=not wrote_header)
        wrote_header = True
        total += len(out_chunk)

    if not wrote_header:
        pd.DataFrame(columns=["patent_id", "inventor_id", "company_id"]).to_csv(out_path, index=False)

    print(f"  Done. {total:,} relationship records.")


def parse_args():
    parser = argparse.ArgumentParser(description="Clean staged patent data with low memory usage.")
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f"Rows per chunk for reading/writing CSV files (default: {DEFAULT_CHUNK_SIZE}).",
    )
    parser.add_argument(
        "--stage",
        choices=["patents", "inventors", "companies", "relationships", "all"],
        default="all",
        help="Which stage to run: patents, inventors, companies, relationships, or all (default: all).",
    )
    parser.add_argument(
        "--stage-chunk-increment",
        type=int,
        default=DEFAULT_STAGE_CHUNK_INCREMENT,
        help=(
            "Increase chunk size by this amount for each subsequent stage "
            "(patents -> inventors -> companies -> relationships). "
            f"Default: {DEFAULT_STAGE_CHUNK_INCREMENT}."
        ),
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Maximum rows to process per file for testing (default: all rows).",
    )
    parser.add_argument(
        "--skip-valid-patent-filter",
        action="store_true",
        help="Skip valid patent ID filtering for inventor exports.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    _cleanup_stale_temp_dbs()

    patents_chunk = max(1, args.chunk_size)
    inventors_chunk = max(1, args.chunk_size + args.stage_chunk_increment)
    companies_chunk = max(1, args.chunk_size + (2 * args.stage_chunk_increment))
    relationships_chunk = max(1, args.chunk_size + (3 * args.stage_chunk_increment))

    print("=" * 50)
    print("STEP 2: CLEANING DATA")
    print("=" * 50)
    print(
        "Chunk sizes by stage: "
        f"patents={patents_chunk}, "
        f"inventors={inventors_chunk}, "
        f"companies={companies_chunk}, "
        f"relationships={relationships_chunk}"
    )

    if args.stage == "patents":
        clean_patents(patents_chunk, args.max_rows)
    elif args.stage == "inventors":
        clean_inventors(
            inventors_chunk,
            args.max_rows,
            filter_by_valid_patents=not args.skip_valid_patent_filter,
        )
    elif args.stage == "companies":
        clean_companies(companies_chunk, args.max_rows)
    elif args.stage == "relationships":
        build_relationships(relationships_chunk, args.max_rows)
    else:
        clean_patents(patents_chunk, args.max_rows)
        clean_inventors(
            inventors_chunk,
            args.max_rows,
            filter_by_valid_patents=not args.skip_valid_patent_filter,
        )
        clean_companies(companies_chunk, args.max_rows)
        build_relationships(relationships_chunk, args.max_rows)

    print("\nCleaning complete. Check data/clean/ for clean_*.csv files.")
