"""STEP 4: ANALYSIS QUERIES

Runs analytical SQL queries against the full patent database and exports the
report inputs used by the dashboard.

Optimizations:
- Materializes reusable aggregate tables once
- Uses COUNT(*) where the relationship tables are already deduplicated
- Writes CSV outputs incrementally so report.py can use them immediately
"""

from __future__ import annotations

import os
import sqlite3

import pandas as pd

DB = "patent_pipeline.db"
OUTPUTS = "outputs"
CLEAN = "data/clean"


def require_database(path: str) -> None:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Database not found at '{path}'. Run scripts/load.py first.")


def require_tables(conn: sqlite3.Connection, tables: list[str]) -> None:
    found = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", conn)["name"].tolist()
    missing = [table for table in tables if table not in found]
    if missing:
        raise RuntimeError(
            "Missing required tables: " + ", ".join(missing) + ". Run scripts/load.py to rebuild the database."
        )


def run_query(conn: sqlite3.Connection, sql: str) -> pd.DataFrame:
    return pd.read_sql_query(sql, conn)


def write_csv(frame: pd.DataFrame, filename: str) -> None:
    os.makedirs(OUTPUTS, exist_ok=True)
    frame.to_csv(os.path.join(OUTPUTS, filename), index=False)


def build_temp_tables(conn: sqlite3.Connection) -> None:
    print("  Building inventor aggregates...")
    conn.execute("DROP TABLE IF EXISTS inventor_counts")
    conn.execute(
        """
        CREATE TEMP TABLE inventor_counts AS
        SELECT
            i.inventor_id,
            i.name,
            i.country,
            COUNT(*) AS patent_count
        FROM relationships r
        JOIN inventors i ON i.inventor_id = r.inventor_id
        WHERE r.inventor_id IS NOT NULL
        GROUP BY i.inventor_id
        """
    )

    print("  Building company aggregates...")
    conn.execute("DROP TABLE IF EXISTS company_counts")
    conn.execute(
        """
        CREATE TEMP TABLE company_counts AS
        SELECT
            c.company_id,
            c.name,
            COUNT(*) AS patent_count
        FROM relationships r
        JOIN companies c ON c.company_id = r.company_id
        WHERE r.company_id IS NOT NULL
        GROUP BY c.company_id
        """
    )

    print("  Building country aggregates...")
    conn.execute("DROP TABLE IF EXISTS country_counts")
    conn.execute(
        """
        CREATE TEMP TABLE country_counts AS
        SELECT
            country,
            COUNT(*) AS patent_count
        FROM (
            SELECT DISTINCT
                r.patent_id,
                i.country
            FROM relationships r
            JOIN inventors i ON i.inventor_id = r.inventor_id
            WHERE r.inventor_id IS NOT NULL
              AND i.country IS NOT NULL
        )
        GROUP BY country
        """
    )

    print("  Building yearly trend aggregates...")
    conn.execute("DROP TABLE IF EXISTS patents_per_year")
    conn.execute(
        """
        CREATE TEMP TABLE patents_per_year AS
        SELECT
            year,
            COUNT(*) AS patent_count
        FROM patents
        WHERE year IS NOT NULL
        GROUP BY year
        ORDER BY year ASC
        """
    )

    print("  Building relationship link tables...")
    conn.execute("DROP TABLE IF EXISTS inventor_links")
    conn.execute(
        """
        CREATE TEMP TABLE inventor_links AS
        SELECT patent_id, inventor_id
        FROM relationships
        WHERE inventor_id IS NOT NULL
        """
    )
    conn.execute("DROP TABLE IF EXISTS company_links")
    conn.execute(
        """
        CREATE TEMP TABLE company_links AS
        SELECT patent_id, company_id
        FROM relationships
        WHERE company_id IS NOT NULL
        """
    )

    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_inventor_counts_patent_count ON inventor_counts(patent_count DESC);
        CREATE INDEX IF NOT EXISTS idx_company_counts_patent_count ON company_counts(patent_count DESC);
        CREATE INDEX IF NOT EXISTS idx_country_counts_patent_count ON country_counts(patent_count DESC);
        CREATE INDEX IF NOT EXISTS idx_patents_per_year_year ON patents_per_year(year ASC);
        CREATE INDEX IF NOT EXISTS idx_inventor_links_inventor ON inventor_links(inventor_id);
        CREATE INDEX IF NOT EXISTS idx_company_links_company ON company_links(company_id);
        """
    )


def main() -> None:
    print("=" * 50)
    print("STEP 4: RUNNING ANALYSIS QUERIES")
    print("=" * 50)

    os.makedirs(OUTPUTS, exist_ok=True)

    # Prefer running against the SQLite database when available. If the DB
    # isn't present (for users who haven't run the load step) fall back to
    # computing aggregates directly from the cleaned CSVs in `data/clean`.
    if not os.path.exists(DB):
        print("Database not found; running analysis from cleaned CSV files...")
        analyze_from_csv()
        return

    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-500000")
    conn.execute("PRAGMA automatic_index=ON")
    conn.execute("PRAGMA journal_mode=OFF")
    require_tables(conn, ["patents", "inventors", "companies", "relationships"])

    print("Building reusable aggregate tables...")
    build_temp_tables(conn)
    print("  Aggregates ready.")

    q1 = run_query(
        conn,
        """
        SELECT name, patent_count
        FROM inventor_counts
        ORDER BY patent_count DESC, name ASC
        LIMIT 10
        """,
    )
    print("\nQ1 - Top 10 Inventors:")
    print(q1.to_string(index=False))

    q2 = run_query(
        conn,
        """
        SELECT name, patent_count
        FROM company_counts
        ORDER BY patent_count DESC, name ASC
        LIMIT 10
        """,
    )
    print("\nQ2 - Top 10 Companies:")
    print(q2.to_string(index=False))

    q3 = run_query(
        conn,
        """
        SELECT country, patent_count
        FROM country_counts
        ORDER BY patent_count DESC, country ASC
        LIMIT 10
        """,
    )
    print("\nQ3 - Top 10 Countries:")
    print(q3.to_string(index=False))

    q4 = run_query(
        conn,
        """
        SELECT year, patent_count
        FROM patents_per_year
        ORDER BY year ASC
        """,
    )
    print("\nQ4 - Patents Per Year (first 10 rows):")
    print(q4.head(10).to_string(index=False))

    q5 = run_query(
        conn,
        """
        WITH combined AS (
            SELECT
                p.patent_id,
                p.title,
                p.year,
                i.name AS inventor_name,
                c.name AS company_name
            FROM patents p
            JOIN inventor_links il ON p.patent_id = il.patent_id
            JOIN inventors i ON il.inventor_id = i.inventor_id
            LEFT JOIN company_links cl ON p.patent_id = cl.patent_id
            LEFT JOIN companies c ON cl.company_id = c.company_id
        )
        SELECT *
        FROM combined
        LIMIT 20
        """,
    )
    print("\nQ5 - Patents with Inventors and Companies (first 20):")
    print(q5.to_string(index=False))

    q6 = run_query(
        conn,
        """
        WITH inventor_totals AS (
            SELECT inventor_id, name, country, patent_count AS total_patents
            FROM inventor_counts
        )
        SELECT name, country, total_patents
        FROM inventor_totals
        WHERE total_patents > 50
        ORDER BY total_patents DESC, name ASC
        LIMIT 10
        """,
    )
    print("\nQ6 - CTE: Inventors with more than 50 patents:")
    print(q6.to_string(index=False))

    q7 = run_query(
        conn,
        """
        WITH ranked AS (
            SELECT
                name,
                country,
                patent_count,
                RANK() OVER (ORDER BY patent_count DESC) AS inventor_rank
            FROM inventor_counts
        )
        SELECT
            name,
            country,
            patent_count,
            inventor_rank
        FROM ranked
        ORDER BY inventor_rank ASC, name ASC
        LIMIT 20
        """,
    )
    print("\nQ7 - Ranked Inventors (window function):")
    print(q7.to_string(index=False))

    write_csv(q1, "top_inventors.csv")
    write_csv(q2, "top_companies.csv")
    write_csv(q3, "country_trends.csv")
    write_csv(q4, "patents_per_year.csv")

    print("\nQuery results saved to outputs/")
    conn.close()


def analyze_from_csv() -> None:
    # Lightweight CSV-based analysis for environments without the DB.
    print("  Reading cleaned CSVs from data/clean...")
    required = [
        "clean_patents.csv",
        "clean_inventors.csv",
        "clean_companies.csv",
        "clean_relationships.csv",
    ]
    missing = [f for f in required if not os.path.exists(os.path.join(CLEAN, f))]
    if missing:
        raise FileNotFoundError("Missing cleaned CSVs: " + ", ".join(missing) + ". Run scripts/extract.py and scripts/clean.py first.")

    patents = pd.read_csv(os.path.join(CLEAN, "clean_patents.csv"), dtype="string")
    inventors = pd.read_csv(os.path.join(CLEAN, "clean_inventors.csv"), dtype="string")
    companies = pd.read_csv(os.path.join(CLEAN, "clean_companies.csv"), dtype="string")
    relationships = pd.read_csv(os.path.join(CLEAN, "clean_relationships.csv"), dtype="string")

    # patents per year
    patents["year"] = pd.to_numeric(patents.get("year"), errors="coerce")
    q4 = (
        patents.dropna(subset=["year"]).groupby("year", as_index=False)
        .agg(patent_count=("patent_id", "count"))
        .sort_values("year", ascending=True)
    )

    # inventor counts (join relationships -> inventors)
    rel_inv = relationships[relationships["inventor_id"].notna()].merge(
        inventors[["inventor_id", "name", "country"]], on="inventor_id", how="left"
    )
    q1 = (
        rel_inv.groupby(["inventor_id", "name", "country"], as_index=False)
        .agg(patent_count=("patent_id", "count"))
        .sort_values(["patent_count", "name"], ascending=[False, True])
        .loc[:, ["name", "patent_count"]]
        .head(10)
    )

    # company counts
    rel_comp = relationships[relationships["company_id"].notna()].merge(
        companies[["company_id", "name"]], on="company_id", how="left"
    )
    q2 = (
        rel_comp.groupby(["company_id", "name"], as_index=False)
        .agg(patent_count=("patent_id", "count"))
        .sort_values(["patent_count", "name"], ascending=[False, True])
        .loc[:, ["name", "patent_count"]]
        .head(10)
    )

    # country counts - deduplicate patent/country pairs
    rel_ctry = relationships[relationships["inventor_id"].notna()].merge(
        inventors[["inventor_id", "country"]], on="inventor_id", how="left"
    )
    rel_ctry = rel_ctry.dropna(subset=["country"]) [["patent_id", "country"]].drop_duplicates()
    q3 = (
        rel_ctry.groupby("country", as_index=False)
        .agg(patent_count=("patent_id", "count"))
        .sort_values(["patent_count", "country"], ascending=[False, True])
        .head(10)
    )

    print("\nQ1 - Top 10 Inventors:")
    print(q1.to_string(index=False))
    print("\nQ2 - Top 10 Companies:")
    print(q2.to_string(index=False))
    print("\nQ3 - Top 10 Countries:")
    print(q3.to_string(index=False))
    print("\nQ4 - Patents Per Year (first 10 rows):")
    print(q4.head(10).to_string(index=False))

    write_csv(q1, "top_inventors.csv")
    write_csv(q2, "top_companies.csv")
    write_csv(q3, "country_trends.csv")
    write_csv(q4, "patents_per_year.csv")

    print("\nQuery results saved to outputs/")


if __name__ == "__main__":
    main()
