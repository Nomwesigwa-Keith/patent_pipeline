"""STEP 1: DATA DOWNLOAD

Downloads patent data from external sources into data/raw/ directory.

This script provides a scaffold for downloading patent data:
- Can copy sample data for testing
- Can be extended to download from USPTO PatentsView
- Supports different data sources and formats

Usage:
    # Download and use sample data
    python scripts/download_data.py --sample
    
    # Specify custom destination
    python scripts/download_data.py --dest /path/to/data --sample

Options:
    --dest DEST        Destination folder (default: data/raw)
    --sample           Copy bundled sample data instead of downloading

Outputs:
- Patent data files in data/raw/ directory in TSV format:
  - g_patent.tsv
  - g_inventor.tsv
  - g_assignee.tsv
  - (other relationship files)

Note:
    Replace with your actual data source integration for production use.
    See PatentsView documentation: https://www.patentsview.org/
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil


def main():
    p = argparse.ArgumentParser(description="Download full datasets into data/raw/")
    p.add_argument("--dest", default="data/raw", help="Destination folder")
    p.add_argument("--sample", action="store_true", help="Copy bundled sample instead of downloading")
    p.add_argument("--source", default=r"C:\Users\viase\Desktop\Cloud Datasets", help="Source directory for TSV files")
    args = p.parse_args()

    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)

    if args.sample:
        sample = Path("data/sample/sample_patents.csv")
        if sample.exists():
            shutil.copy(sample, dest / sample.name)
            print(f"Copied sample to {dest / sample.name}")
        else:
            print("No sample found in data/sample. Run scripts/validate.py to create one.")
        return

    # Copy from user's Cloud Datasets directory
    source_dir = Path(args.source)
    if not source_dir.exists():
        print(f"Source directory not found: {source_dir}")
        print("Please specify the correct path to your TSV files with --source")
        return

    tsv_files = list(source_dir.glob("*.tsv"))
    if not tsv_files:
        print(f"No TSV files found in {source_dir}")
        return

    print(f"Copying {len(tsv_files)} TSV files from {source_dir} to {dest}")
    for tsv_file in tsv_files:
        dest_file = dest / tsv_file.name
        print(f"  Copying {tsv_file.name}...")
        shutil.copy2(tsv_file, dest_file)

    print(f"Successfully copied {len(tsv_files)} files to {dest}")
    total_size = sum(f.stat().st_size for f in dest.glob("*.tsv"))
    print(f"Total size: {total_size / (1024**3):.1f} GB")


if __name__ == "__main__":
    main()
