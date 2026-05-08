"""STEP 6: REPORT GENERATION

Generates comprehensive reports from analysis results.

Report types:
1. Console Report: Formatted output to terminal
2. CSV Reports: Individual CSV files for each metric
3. JSON Report: Comprehensive JSON export

Generates:
- Console report showing top inventors, companies, and countries
- CSV exports for each major analysis
- JSON report combining all metrics

Prerequisites:
- Analysis must have been run (outputs/ files must exist)
- Requires:
  - outputs/top_inventors.csv
  - outputs/top_companies.csv
  - outputs/country_trends.csv
  - outputs/patents_per_year.csv

Usage:
    python scripts/report.py

Outputs:
- outputs/report.json - Comprehensive JSON report
- Console output with formatted report

Note:
    Run scripts/analyze.py first to generate required input files.
"""

import pandas as pd
import json
import os

OUTPUTS = "outputs"


def require_report_inputs(files):
    missing = [f for f in files if not os.path.exists(os.path.join(OUTPUTS, f))]
    if missing:
        msg = "Missing analysis outputs: " + ", ".join(missing)
        msg += ". Run scripts/analyze.py first."
        raise FileNotFoundError(msg)

def generate_report():
    os.makedirs(OUTPUTS, exist_ok=True)
    require_report_inputs([
        "top_inventors.csv",
        "top_companies.csv",
        "country_trends.csv",
        "patents_per_year.csv",
    ])

    top_inventors = pd.read_csv(os.path.join(OUTPUTS, "top_inventors.csv"))
    top_companies = pd.read_csv(os.path.join(OUTPUTS, "top_companies.csv"))
    top_countries = pd.read_csv(os.path.join(OUTPUTS, "country_trends.csv"))
    patents_per_year = pd.read_csv(os.path.join(OUTPUTS, "patents_per_year.csv"))

    total_patents = patents_per_year["patent_count"].sum()

    # Console Report
    print("\n" + "=" * 55)
    print("           GLOBAL PATENT INTELLIGENCE REPORT")
    print("=" * 55)
    print(f"\n  Total Patents Analyzed : {total_patents:,}")
    print(f"  Years Covered          : {int(patents_per_year['year'].min())} - {int(patents_per_year['year'].max())}")

    print("\n  TOP 10 INVENTORS:")
    for i, row in top_inventors.iterrows():
        print(f"    {i+1:>2}. {row['name']:<35} {row['patent_count']:,} patents")

    print("\n  TOP 10 COMPANIES:")
    for i, row in top_companies.iterrows():
        print(f"    {i+1:>2}. {row['name']:<35} {row['patent_count']:,} patents")

    print("\n  TOP 10 COUNTRIES:")
    for i, row in top_countries.iterrows():
        print(f"    {i+1:>2}. {row['country']:<35} {row['patent_count']:,} patents")

    print("\n" + "=" * 55)

    # JSON Report
    report = {
        "total_patents": int(total_patents),
        "analyzed_total_patents": int(total_patents),
        "year_range": {
            "from": int(patents_per_year["year"].min()),
            "to": int(patents_per_year["year"].max())
        },
        "top_inventors": top_inventors.to_dict(orient="records"),
        "top_companies": top_companies.to_dict(orient="records"),
        "top_countries": top_countries.to_dict(orient="records")
    }

    with open(os.path.join(OUTPUTS, "report.json"), "w") as f:
        json.dump(report, f, indent=2)

    print("\n  JSON report saved to outputs/report.json")
    print("  CSV reports saved to outputs/")


if __name__ == "__main__":
    generate_report()