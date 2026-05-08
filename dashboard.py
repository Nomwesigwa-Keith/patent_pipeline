from pathlib import Path
import json

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"
RAW_PATENT_PATH = BASE_DIR / "data" / "raw" / "g_patent.tsv"
REPORT_PATH = OUTPUTS_DIR / "report.json"


@st.cache_data(show_spinner=False)
def load_csv(filename: str) -> pd.DataFrame:
    file_path = OUTPUTS_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Missing {filename}. Run scripts/analyze.py and scripts/report.py first.")
    return pd.read_csv(file_path)


@st.cache_data(show_spinner=False)
def load_report() -> dict:
    if not REPORT_PATH.exists():
        raise FileNotFoundError("Missing outputs/report.json. Run scripts/report.py first.")
    with REPORT_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@st.cache_data(show_spinner=False)
def count_tsv_rows(path: str) -> int | None:
    file_path = Path(path)
    if not file_path.exists():
        return None
    with file_path.open("r", encoding="utf-8", newline="") as handle:
        total = sum(1 for _ in handle) - 1
    return max(total, 0)


def missing_outputs() -> list[str]:
    required_files = [
        "top_inventors.csv",
        "top_companies.csv",
        "country_trends.csv",
        "patents_per_year.csv",
        "report.json",
    ]

    return [name for name in required_files if not (OUTPUTS_DIR / name).exists()]


def as_int(value) -> int:
    return int(value) if pd.notna(value) else 0


def display_stat(label: str, value: str, helper: str) -> None:
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-label">{label}</div>
            <div class="stat-value">{value}</div>
            <div class="stat-helper">{helper}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def display_ranked_table(title: str, frame: pd.DataFrame, name_col: str, value_col: str) -> None:
    st.markdown(f"<div class='panel-title'>{title}</div>", unsafe_allow_html=True)
    view = frame[[name_col, value_col]].copy()
    view.columns = ["Name", "Patents"]
    st.dataframe(view, use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(page_title="Patent Pipeline Dashboard", layout="wide", initial_sidebar_state="collapsed")
    st.markdown(
        """
        <style>
            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(255, 255, 255, 0.08), transparent 28%),
                    linear-gradient(180deg, #07111f 0%, #0b1730 45%, #f4f7fb 45%, #f4f7fb 100%);
                color: #0f172a;
            }
            .block-container {
                padding-top: 1.1rem;
                padding-bottom: 2rem;

            }
            .hero {
                background: linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.92));
                border: 1px solid rgba(148, 163, 184, 0.16);
                border-radius: 28px;
                padding: 2rem 2.2rem;
                color: white;
                box-shadow: 0 24px 70px rgba(15, 23, 42, 0.28);
            }
            .eyebrow {
                display: inline-block;
                padding: 0.35rem 0.8rem;
                border-radius: 999px;
                background: rgba(96, 165, 250, 0.18);
                color: #bfdbfe;
                font-size: 0.78rem;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                margin-bottom: 0.9rem;
            }
            .hero h1 {
                font-size: 2.8rem;
                line-height: 1.04;
                margin: 0;
                font-weight: 800;
            }
            .hero p {
                margin: 0.9rem 0 1.2rem;
                color: #cbd5e1;
                max-width: 52rem;
                font-size: 1.02rem;
            }
            .hero-badges {
                display: flex;
                flex-wrap: wrap;
                gap: 0.6rem;
            }
            .hero-badge {
                padding: 0.45rem 0.8rem;
                border-radius: 999px;
                background: rgba(255, 255, 255, 0.08);

                border: 1px solid rgba(255, 255, 255, 0.1);
                color: #e2e8f0;
                font-size: 0.88rem;
            }
            .section-shell {
                margin-top: 1.1rem;
                background: rgba(255, 255, 255, 0.82);
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 26px;
                padding: 1.2rem;
                box-shadow: 0 20px 60px rgba(15, 23, 42, 0.08);
                backdrop-filter: blur(10px);
            }
            .stat-card {
                background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
                border: 1px solid rgba(148, 163, 184, 0.16);
                border-radius: 20px;
                padding: 1rem 1rem 0.95rem;
                box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
                height: 100%;
            }
            .stat-label {
                color: #475569;
                font-size: 0.82rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                margin-bottom: 0.4rem;
            }
            .stat-value {
                color: #0f172a;
                font-size: 1.75rem;
                font-weight: 800;
                line-height: 1.1;
            }
            .stat-helper {
                color: #64748b;
                font-size: 0.88rem;
                margin-top: 0.35rem;
            }
            .panel-title {
                font-size: 1.05rem;
                font-weight: 700;

                color: #0f172a;
                margin: 0.1rem 0 0.6rem;
            }
            .insight-box {
                background: linear-gradient(135deg, #eff6ff 0%, #e0f2fe 100%);
                border: 1px solid rgba(96, 165, 250, 0.24);
                border-radius: 18px;
                padding: 1rem 1.1rem;
                color: #0f172a;
            }
            .insight-label {
                font-size: 0.78rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                color: #0369a1;
                margin-bottom: 0.3rem;
                font-weight: 700;
            }
            .insight-text {
                font-size: 0.98rem;
                color: #0f172a;
                line-height: 1.5;
            }
            div[data-baseweb="tab-list"] button {
                border-radius: 999px !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    missing_files = missing_outputs()
    if missing_files:
        st.error("Missing analysis outputs: " + ", ".join(missing_files))
        st.stop()
    report = load_report()
    top_inventors = load_csv("top_inventors.csv")
    top_companies = load_csv("top_companies.csv")
    top_countries = load_csv("country_trends.csv")
    patents_per_year = load_csv("patents_per_year.csv")
    analyzed_total_patents = int(

        report.get("analyzed_total_patents", report.get("total_patents", patents_per_year["patent_count"].sum()))
    )
    source_total_patents = report.get("source_total_patents")
    if source_total_patents is None:
        source_total_patents = count_tsv_rows(str(RAW_PATENT_PATH))
    source_total_patents = as_int(source_total_patents) if source_total_patents is not None else analyzed_total_patents
    year_range = report.get("year_range", {})
    start_year = as_int(year_range.get("from", patents_per_year["year"].min()))
    end_year = as_int(year_range.get("to", patents_per_year["year"].max()))
    complete_coverage = source_total_patents == analyzed_total_patents

    # Safely handle empty analysis outputs to avoid IndexError when calling .iloc[0]
    if not top_inventors.empty:
        top_inventor = top_inventors.iloc[0]
    else:
        top_inventor = {"name": "N/A", "patent_count": 0}

    if not top_companies.empty:
        top_company = top_companies.iloc[0]
    else:
        top_company = {"name": "N/A", "patent_count": 0}

    if not top_countries.empty:
        top_country = top_countries.iloc[0]
    else:
        top_country = {"country": "N/A", "patent_count": 0}

    if not patents_per_year.empty:
        yearly_peak = patents_per_year.sort_values("patent_count", ascending=False).iloc[0]
    else:
        yearly_peak = {"year": start_year, "patent_count": 0}
    st.markdown(
        f"""
        <div class="hero">
            <div class="eyebrow">Global Patent Intelligence</div>
            <h1>Patent dashboard for quick insights.</h1>
            <p>
                A clean executive view of patent volume, top inventors, leading companies, and country trends
                built from the pipeline outputs.
            </p>
            <div class="hero-badges">
                <span class="hero-badge">{source_total_patents:,} patents in source data</span>
                <span class="hero-badge">{start_year} - {end_year} analysis window</span>
                <span class="hero-badge">Top inventor: {top_inventor['name']}</span>
                <span class="hero-badge">Top company: {top_company['name']}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not complete_coverage:
        st.warning(

            f"Current analysis outputs cover {analyzed_total_patents:,} patents, but the source dataset contains "
            f"{source_total_patents:,}. Re-run the pipeline to refresh the cleaned outputs and analysis tables."
        )
    st.markdown("<div class='section-shell'>", unsafe_allow_html=True)
    stat_cols = st.columns(4)
    with stat_cols[0]:
        display_stat("Source patents", f"{source_total_patents:,}", "Rows in data/raw/g_patent.tsv")
    with stat_cols[1]:
        display_stat("Analyzed patents", f"{analyzed_total_patents:,}", "Rows currently summarized in outputs")
    with stat_cols[2]:
        display_stat("Top inventor", top_inventor["name"], f"{int(top_inventor['patent_count']):,} patents")
    with stat_cols[3]:
        display_stat("Top company", top_company["name"], f"{int(top_company['patent_count']):,} patents")
    with stat_cols[1]:
        display_stat("Top inventor", top_inventor["name"], f"{int(top_inventor['patent_count']):,} patents")
    with stat_cols[2]:
        display_stat("Top company", top_company["name"], f"{int(top_company['patent_count']):,} patents")
    with stat_cols[3]:
        display_stat("Top country", top_country["country"], f"{int(top_country['patent_count']):,} patents")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-shell'>", unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["Trends", "Top Lists", "Data Tables"])
    with tab1:
        chart_left, chart_right = st.columns([1.25, 0.95])
        with chart_left:
            st.markdown("<div class='panel-title'>Patents per year</div>", unsafe_allow_html=True)
            st.line_chart(patents_per_year.set_index("year")[['patent_count']], color="#2563eb")
        with chart_right:
            st.markdown("<div class='panel-title'>Country trends</div>", unsafe_allow_html=True)

            st.bar_chart(top_countries.set_index("country")[["patent_count"]], color="#0f766e")
        st.markdown(
            f"""
            <div class="insight-box">
                <div class="insight-label">Key insight</div>
                <div class="insight-text">
                    The strongest yearly output appears in <strong>{int(yearly_peak['year'])}</strong> with
                    <strong>{int(yearly_peak['patent_count']):,}</strong> patents, while
                    <strong>{top_country['country']}</strong> leads country-level patent volume.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with tab2:
        list_left, list_right = st.columns(2)
        with list_left:
            st.markdown("<div class='panel-title'>Top inventors</div>", unsafe_allow_html=True)
            st.bar_chart(top_inventors.set_index("name")[['patent_count']], color="#7c3aed")
            display_ranked_table("Ranked inventors", top_inventors, "name", "patent_count")
        with list_right:
            st.markdown("<div class='panel-title'>Top companies</div>", unsafe_allow_html=True)
            st.bar_chart(top_companies.set_index("name")[['patent_count']], color="#f97316")
            display_ranked_table("Ranked companies", top_companies, "name", "patent_count")
    with tab3:
        data_left, data_right = st.columns(2)
        with data_left:
            st.markdown("<div class='panel-title'>Country trends</div>", unsafe_allow_html=True)
            st.dataframe(top_countries, use_container_width=True, hide_index=True)
        with data_right:
            st.markdown("<div class='panel-title'>Patents per year</div>", unsafe_allow_html=True)

            st.dataframe(patents_per_year, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
