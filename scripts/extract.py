"""STEP 2: DATA EXTRACTION

Extracts relevant fields from raw TSV files into cleaned CSV format.

Operations:
- Patents: Extract patent_id, patent_type, patent_date, patent_title
- Abstracts: Extract patent_id and abstract text
- Inventors: Extract inventor information
- Companies: Extract company/assignee information
- Relationships: Extract patent-inventor and patent-company links

Handles large files by processing in chunks to manage memory.

Prerequisites:
- Raw data must be in data/raw/ (downloaded by download_data.py)

Usage:
    python scripts/extract.py
    
Outputs:
- Extracted CSV files in data/clean/:
  - raw_patents.csv
  - raw_abstracts.csv
  - raw_inventors.csv
  - raw_companies.csv
  - raw_relationships.csv
  - (other extracted files)
"""

import pandas as pd
import os
import argparse

RAW = "data/raw"
CLEAN = "data/clean"
SEP = "\t"
DEFAULT_CHUNK_SIZE = 50000


def extract_file(raw_filename, out_filename, usecols, chunk_size):
    raw_path = os.path.join(RAW, raw_filename)
    out_path = os.path.join(CLEAN, out_filename)

    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Missing input file: {raw_path}")

    os.makedirs(CLEAN, exist_ok=True)
    if os.path.exists(out_path):
        os.remove(out_path)

    total_rows = 0
    wrote_header = False
    for chunk in pd.read_csv(
        raw_path,
        sep=SEP,
        usecols=usecols,
        dtype="string",
        chunksize=chunk_size,
    ):
        chunk.to_csv(out_path, index=False, mode="a", header=not wrote_header)
        wrote_header = True
        total_rows += len(chunk)

    return total_rows


def extract_patents(chunk_size):
    print("Extracting patents...")
    count = extract_file(
        "g_patent.tsv",
        "raw_patents.csv",
        ["patent_id", "patent_type", "patent_date", "patent_title"],
        chunk_size,
    )
    print(f"  Done. {count:,} patent records extracted.")


def extract_abstracts(chunk_size):
    print("Extracting abstracts...")
    count = extract_file(
        "g_patent_abstract.tsv",
        "raw_abstracts.csv",
        ["patent_id", "patent_abstract"],
        chunk_size,
    )
    print(f"  Done. {count:,} abstract records extracted.")


def extract_inventors(chunk_size):
    print("Extracting inventors...")
    count = extract_file(
        "g_inventor_disambiguated.tsv",
        "raw_inventors.csv",
        [
            "patent_id",
            "inventor_id",
            "disambig_inventor_name_first",
            "disambig_inventor_name_last",
            "location_id",
        ],
        chunk_size,
    )
    print(f"  Done. {count:,} inventor records extracted.")


def extract_assignees(chunk_size):
    print("Extracting assignees (companies)...")
    count = extract_file(
        "g_assignee_disambiguated.tsv",
        "raw_assignees.csv",
        [
            "patent_id",
            "assignee_id",
            "disambig_assignee_organization",
            "disambig_assignee_individual_name_first",
            "disambig_assignee_individual_name_last",
            "location_id",
        ],
        chunk_size,
    )
    print(f"  Done. {count:,} assignee records extracted.")


def extract_locations(chunk_size):
    print("Extracting locations...")
    count = extract_file(
        "g_location_disambiguated.tsv",
        "raw_locations.csv",
        ["location_id", "disambig_country", "disambig_city", "disambig_state"],
        chunk_size,
    )
    print(f"  Done. {count:,} location records extracted.")


def parse_args():
    parser = argparse.ArgumentParser(description="Extract raw patent TSV files into staging CSVs.")
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f"Rows per chunk while reading large TSV files (default: {DEFAULT_CHUNK_SIZE}).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    print("=" * 50)
    print("STEP 1: EXTRACTING RAW DATA")
    print("=" * 50)
    extract_patents(args.chunk_size)
    extract_abstracts(args.chunk_size)
    extract_inventors(args.chunk_size)
    extract_assignees(args.chunk_size)
    extract_locations(args.chunk_size)
    print("\nExtraction complete. Check data/clean/ for output files.")