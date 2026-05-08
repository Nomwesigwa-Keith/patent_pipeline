# Patent Pipeline

Minimal pipeline for downloading, cleaning, analyzing, and visualizing patent data.

Quick start
- Clone: `git clone https://github.com/Nomwesigwa-Keith/patent_pipeline`
- Install: `pip install -r requirements.txt`
- Run sample pipeline:

```bash
python scripts/download_data.py --sample
python scripts/extract.py
python scripts/clean.py
python scripts/load.py
python scripts/analyze.py
python scripts/report.py
```

Run the dashboard locally:

```bash
streamlit run dashboard.py
```
DASHBOARD LINK: https://patentpipeline-dgokvdnmfbtctaz2jj63sj.streamlit.app/

What’s in this repo
- `scripts/` — ETL and analysis scripts
- `sql/schema.sql` — DB schema
- `data/sample/` — small sample data
- `outputs/` — generated CSV/JSON reports

Notes
- Cleaned CSVs are large and excluded from the repo; regenerate with `scripts/clean.py`.
- Deploy the dashboard on Streamlit Community Cloud (main file: `dashboard.py`).

Author
- Nomwesigwa Keith
