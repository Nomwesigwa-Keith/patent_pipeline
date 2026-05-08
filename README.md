# Global Patent Intelligence Data Pipeline

A comprehensive data engineering project that collects, cleans, stores, and analyzes real-world patent data from the USPTO PatentsView Granted Patent Disambiguated dataset.

## Project Overview

This pipeline demonstrates a complete data engineering workflow:
- **Extract**: Download patent data from external sources
- **Clean**: Process and clean data using Python and pandas
- **Load**: Store data in a SQLite database
- **Analyze**: Query data using SQL to generate insights
- **Report**: Export results in multiple formats (CSV, JSON, console)

### Data Source
[PatentsView Granted Patent Disambiguated Data](https://data.uspto.gov/bulkdata/datasets/pvgpatdis?fileDataFromDate=1976-01-01&fileDataToDate=2025-09-30)

See `PV_grant_data_dictionary.pdf` for field descriptions.

## Project Structure

```
.
├── scripts/              # Python ETL scripts
│   ├── download_data.py  # Download patent data
│   ├── extract.py        # Extract relevant fields
│   ├── clean.py          # Clean and normalize data
│   ├── load.py           # Load into SQLite
│   ├── analyze.py        # Run analysis queries
│   ├── report.py         # Generate reports
│   └── validate.py       # Validate sample data
├── sql/
│   ├── schema.sql        # Database schema definition
│   └── queries.sql       # All analytical queries
├── data/
│   ├── sample/           # Sample patent data for testing
│   ├── raw/              # Raw downloaded data (git-ignored)
│   └── clean/            # Cleaned data in CSV format
├── outputs/              # Generated reports and analyses
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

## Database Schema

### `patents` table
- `patent_id` (TEXT, PRIMARY KEY)
- `title` (TEXT)
- `abstract` (TEXT)
- `filing_date` (TEXT)
- `year` (INTEGER)
- `patent_type` (TEXT)

### `inventors` table
- `inventor_id` (TEXT, PRIMARY KEY)
- `name` (TEXT)
- `country` (TEXT)

### `companies` table
- `company_id` (TEXT, PRIMARY KEY)
- `name` (TEXT)

### `relationships` table
- `patent_id` (TEXT, FOREIGN KEY)
- `inventor_id` (TEXT, FOREIGN KEY)
- `company_id` (TEXT, FOREIGN KEY)

## Installation & Setup

### Prerequisites
- Python 3.11+ (tested with 3.13)
- pip (Python package manager)

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd patent_pipeline
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

Current dependencies:
- pandas==3.0.2 (data manipulation)
- numpy==2.4.4 (numerical computing)

### Step 3: Prepare Data
Download patent data from the PatentsView source or use the sample data:

```bash
python scripts/download_data.py --sample
```

## Running the Pipeline

### Option 1: Full Pipeline (Recommended)

Run all steps in sequence:

```bash
# 1. Download data (optional if you already have raw data)
python scripts/download_data.py --sample

# 2. Extract relevant fields
python scripts/extract.py

# 3. Clean and normalize data
python scripts/clean.py

# 4. Load into SQLite database
python scripts/load.py

# 5. Run analysis queries
python scripts/analyze.py

# 6. Generate reports
python scripts/report.py
```

### Option 2: Individual Steps

Run each script independently as needed.

## SQL Queries

The pipeline includes 7 comprehensive queries:

### Q1: Top Inventors
Who has the most patents?

### Q2: Top Companies
Which companies own the most patents?

### Q3: Countries
Which countries produce the most patents?

### Q4: Trends Over Time
How many patents are created each year?

### Q5: JOIN Query
Combine patents with inventors and companies (demonstrates JOINS)

### Q6: CTE Query (WITH statement)
Break a complex query into steps using Common Table Expressions

### Q7: Ranking Query
Rank inventors using window functions (RANK() OVER)

All queries are in `sql/queries.sql`

## Output Files

The pipeline generates the following reports:

### CSV Files (in `outputs/`)
- `top_inventors.csv` - Top 10 inventors by patent count
- `top_companies.csv` - Top 10 companies by patent count
- `country_trends.csv` - Patent counts by country
- `patents_per_year.csv` - Annual patent trends

### JSON Report (in `outputs/`)
- `report.json` - Comprehensive report with all metrics

### Console Output
A formatted report is printed to the terminal during report generation.

## Streamlit Dashboard

An interactive dashboard is available at the project root:

- `dashboard.py`

### Run locally

```bash
pip install -r requirements.txt
streamlit run dashboard.py
```

The app reads from `outputs/` and visualizes:

- Patents per year (line chart)
- Top countries (bar chart)
- Top inventors (bar chart)
- Top companies (bar chart)
- Ranked tables for quick inspection

### Publish with a permanent link

To get a stable shareable URL, deploy to Streamlit Community Cloud:

1. Push this repository to GitHub.
2. Go to `https://share.streamlit.io/`.
3. Click **New app** and select your repository and branch.
4. Set the main file path to `dashboard.py`.
5. Deploy.

After deployment, Streamlit gives you a persistent public app URL you can share.

## Testing

Validate the sample data:
```bash
python scripts/validate.py
```

Expected output: `OK: sample dataset looks good`

## Database

The SQLite database is created automatically when loading data:
- `patent_pipeline.db` - Main database (git-ignored)

To inspect the database:
```bash
sqlite3 patent_pipeline.db ".tables"
sqlite3 patent_pipeline.db ".schema patents"
```

## Project Requirements Met

✓ Data extraction from external source
✓ Data cleaning using pandas
✓ SQLite database with 4 main tables + relationships
✓ 7 SQL queries (JOIN, CTE, window functions)
✓ 3 types of reports (console, CSV, JSON)
✓ Full reproducibility - anyone can clone and run
✓ Proper documentation
✓ Git version control setup

## Extra Features (For Bonus Marks)

Potential enhancements:
- Add data visualization (matplotlib/plotly)
- Build interactive dashboard (Streamlit)
- Advanced analysis of patent categories
- Export to additional formats
- Performance optimization for large datasets

## Troubleshooting

### "Database not found" error
Run `scripts/load.py` first to create the database.

### Missing cleaned CSV files
Run `scripts/clean.py` after extracting data with `scripts/extract.py`.

### Import errors
Reinstall dependencies: `pip install -r requirements.txt`

## Requirements

- [x] `data/clean/clean_patents.csv`
- [x] `data/clean/clean_inventors.csv`
- [x] `data/clean/clean_companies.csv`
- [x] `sql/schema.sql`
- [x] Generated reports in `outputs/`

## Author Notes

This project demonstrates professional data engineering practices:
- Reproducible workflows
- Proper error handling
- Clear documentation
- Modular script design
- Version control best practices
