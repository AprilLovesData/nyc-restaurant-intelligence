"""NYC Restaurant Intelligence Platform — Market Overview dashboard.

Reads the normalised tables from Supabase and lets the visitor ask their own
question of the data, rather than replaying the fixed views in the notebooks.

Run locally:
    streamlit run streamlit_app.py
"""

from __future__ import annotations

import io
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# ---------------------------------------------------------------- page setup

st.set_page_config(
    page_title="NYC Restaurant Market Overview",
    page_icon="🍽️",
    layout="wide",
)

# Same palette as the notebooks, so the dashboard and the report look like one thing.
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
DIVERGING = ["#8f2020", "#d03b3b", "#e88b8b", "#f0efec", "#86b6ef", "#2a78d6", "#0d366b"]
BLUE = "#2a78d6"
INK_SOFT = "#52514e"

# Cuisines that carry no information: one is a placeholder, the other a catch-all.
NON_CUISINES = ["UNKNOWN", "OTHER"]
BORO_ORDER = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]

# ---------------------------------------------------------------- data access


def _credentials() -> tuple[str, str]:
    """Read Supabase credentials, failing with instructions rather than a traceback."""
    try:
        cfg = st.secrets["supabase"]
        # The dashboard shows the REST endpoint in several places, so the value
        # pasted here is often ".../rest/v1" rather than the bare project URL.
        # Left alone it builds ".../rest/v1//rest/v1/restaurants" and Supabase
        # answers PGRST125, which looks nothing like "your URL has a suffix".
        base = cfg["url"].strip().rstrip("/")
        if base.endswith("/rest/v1"):
            base = base[: -len("/rest/v1")]
        return base, cfg["anon_key"].strip()
    except (KeyError, FileNotFoundError):
        st.error(
            "Supabase credentials not found.\n\n"
            "Create `.streamlit/secrets.toml` in the project root:\n\n"
            "```toml\n"
            "[supabase]\n"
            'url = "https://YOUR-PROJECT.supabase.co"\n'
            'anon_key = "YOUR-ANON-KEY"\n'
            "```\n\n"
            "Both values are in the Supabase dashboard under "
            "**Project Settings -> API**."
        )
        st.stop()


PAGE_SIZE = 1000  # Supabase caps a single response at 1000 rows
MAX_PARALLEL = 8


def _check(response: requests.Response, table: str) -> None:
    """Turn the two failures worth explaining into readable messages."""
    if response.status_code in (401, 403):
        st.error(
            f"Supabase rejected the request for `{table}` ({response.status_code}).\n\n"
            "Usual causes:\n"
            "- the key is not the **publishable / anon** one\n"
            "- `sql/schema.sql` was not run, so the read policy and grant are missing\n"
            "- the URL is missing the `https://` prefix"
        )
        st.stop()
    if response.status_code == 404:
        st.error(
            f"Supabase returned 404 for `{table}`.\n\n"
            f"Its reply: `{response.text[:200]}`\n\n"
            "`PGRST205` means the table is missing — run `sql/schema.sql` first. "
            "`PGRST125` means the request path is wrong — `url` in secrets.toml "
            "should stop at `.supabase.co`, with no `/rest/v1` suffix."
        )
        st.stop()
    response.raise_for_status()


@st.cache_data(ttl=3600, show_spinner="Loading data from Supabase…")
def fetch_table(table: str, columns: str = "*") -> pd.DataFrame:
    """Fetch a whole table.

    Two things make this less trivial than one GET. Supabase caps a response at
    1000 rows and does NOT signal truncation — asking for 31,222 restaurants
    returns 1000 rows with a 200 OK, so the app would silently show a third of
    the city. And fetching 32 pages one after another means paying the round
    trip to the database region 32 times over, which on a long link is a minute
    of staring at a spinner.

    So: ask Postgres for the exact row count first, then fetch every page at
    once. Total time becomes a few round trips instead of one per page.
    """
    url, key = _credentials()
    endpoint = f"{url}/rest/v1/{table}"
    # CSV rather than JSON: JSON repeats every field name on every row, which for
    # 31,222 restaurants is most of the payload. On a slow link that is the whole
    # cost of the request. Supabase serves either format from the same endpoint.
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "text/csv",
    }

    # Content-Range comes back as "0-0/31222"; the part after the slash is the
    # real total, which is how we know how many pages to ask for.
    probe = requests.get(
        endpoint,
        headers={**headers, "Prefer": "count=exact", "Range": "0-0"},
        params={"select": columns},
        timeout=30,
    )
    _check(probe, table)
    content_range = probe.headers.get("content-range", "")
    if "/" not in content_range:
        st.error(
            f"Supabase did not report a row count for `{table}`. "
            "Without it the app cannot tell a complete download from a truncated one."
        )
        st.stop()
    total = int(content_range.split("/")[-1])

    offsets = range(0, max(total, 1), PAGE_SIZE)
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
        pages = list(pool.map(
            lambda offset: _fetch_page(endpoint, headers, columns, offset, table),
            offsets,
        ))

    frame = pd.concat(pages, ignore_index=True)
    if len(frame) != total:
        st.warning(
            f"`{table}`: expected {total:,} rows but assembled {len(frame):,}. "
            "Some pages may have failed."
        )
    return frame


def _fetch_page(endpoint: str, headers: dict, columns: str,
                offset: int, table: str) -> pd.DataFrame:
    response = requests.get(
        endpoint,
        headers=headers,
        params={"select": columns, "limit": PAGE_SIZE, "offset": offset},
        timeout=60,
    )
    _check(response, table)
    if not response.text.strip():
        return pd.DataFrame()
    return pd.read_csv(io.StringIO(response.text))


RESTAURANT_COLUMNS = (
    "camis,dba,boro,cuisine,latitude,longitude,nta_code,"
    "n_inspections,avg_score,latest_grade,ever_closed,never_inspected"
)

# Downloading 31,222 rows takes as long as the slowest link in the way, and on a
# VPN that can be a minute. The data is a static snapshot, so it is worth keeping
# on disk: the download happens once, and every later run starts instantly. The
# cache is git-ignored and the sidebar can force a refresh.
CACHE_DIR = Path(__file__).parent / "data" / "processed" / ".dashboard_cache"


# Booleans arrive spelled differently depending on the path they took. Supabase's
# CSV endpoint emits Postgres' native "t"/"f"; a pandas round trip through disk
# writes "True"/"False"; JSON would give real booleans. Matching only one spelling
# silently turns every true into false — the "ever closed" figure read 0.0% instead
# of 4.1%, which is wrong without ever looking wrong.
TRUE_TOKENS = frozenset({"true", "t", "1", "yes", "y"})


def _to_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().isin(TRUE_TOKENS)


def _cached_or_fetch(name: str, fetch) -> pd.DataFrame:
    path = CACHE_DIR / f"{name}.csv"
    if path.exists():
        return pd.read_csv(path)
    frame = fetch()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return frame


@st.cache_data(ttl=3600)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    restaurants = _cached_or_fetch(
        "restaurants", lambda: fetch_table("restaurants", columns=RESTAURANT_COLUMNS)
    )
    neighborhoods = _cached_or_fetch(
        "neighborhoods", lambda: fetch_table("neighborhoods")
    )

    numeric = ["latitude", "longitude", "avg_score", "n_inspections"]
    restaurants[numeric] = restaurants[numeric].apply(pd.to_numeric, errors="coerce")
    neighborhoods["population_2010"] = pd.to_numeric(
        neighborhoods["population_2010"], errors="coerce"
    )
    for col in ["ever_closed", "never_inspected"]:
        restaurants[col] = _to_bool(restaurants[col])
    return restaurants, neighborhoods


restaurants, neighborhoods = load_data()

# Citywide cuisine shares are the baseline for the location quotient. They are
# computed once on the full dataset and never on the filtered subset — dividing a
# borough's share by a filtered "citywide" figure would change what the metric means.
# The 85 records with an unknown borough are dropped here too, so the figures match
# the ones reported in notebook 02 rather than being off by a rounding step.
baseline = restaurants[
    ~restaurants["cuisine"].isin(NON_CUISINES)
    & restaurants["boro"].isin(BORO_ORDER)
]
citywide_share = baseline["cuisine"].value_counts(normalize=True)

# ------------------------------------------------------------------- sidebar

st.sidebar.title("Filters")

boroughs = st.sidebar.multiselect(
    "Borough",
    options=BORO_ORDER,
    default=BORO_ORDER,
    help="New York's five boroughs. A handful of records have no borough on file "
         "and are always left out.",
)

cuisine_options = (
    baseline["cuisine"].value_counts().index.tolist()
)
cuisines = st.sidebar.multiselect(
    "Cuisine",
    options=cuisine_options,
    default=[],
    help="Pick one or more to focus the whole page on them. Leave it empty to see "
         "everything. Categories come from the health department's own records.",
)

min_stores = st.sidebar.slider(
    "Hide small neighbourhoods",
    min_value=0, max_value=200, value=30, step=10,
    help="Leaves neighbourhoods with fewer than this many restaurants out of the "
         "table at the bottom. A neighbourhood with three restaurants can top any "
         "ranking by chance, which is rarely what you want to see.",
)

st.sidebar.divider()

if CACHE_DIR.exists():
    st.sidebar.caption("Showing a saved copy of the data so the page loads quickly.")
    if st.sidebar.button("Reload latest data", use_container_width=True):
        shutil.rmtree(CACHE_DIR)
        st.cache_data.clear()
        st.rerun()

st.sidebar.caption(
    "Source: New York City Health Department restaurant inspection records. "
    "This covers places the city has inspected — it is not a full business "
    "directory."
)

# --------------------------------------------------------------------- filter

view = restaurants[restaurants["boro"].isin(boroughs)]
if cuisines:
    view = view[view["cuisine"].isin(cuisines)]

st.title("NYC Restaurant Market Overview")
st.caption(
    f"Every one of the {len(restaurants):,} food businesses on record with the "
    "New York City Health Department, and what their spread across the city shows."
)

with st.expander("New here? How to read this page", expanded=True):
    st.markdown(
        """
**What this is.** Every restaurant, café and takeaway the New York City Health
Department inspects — where they are, what they serve, and how clean they were found
to be. Use the filters on the left to narrow it down to the boroughs and cuisines you
care about; everything on the page updates together.

**Four things worth knowing**

- **Hygiene scores work backwards.** A *low* score is good. Inspectors add points for
  each problem they find, so 5 points is a cleaner kitchen than 30. The city awards an
  **A** at 13 points or below.
- **"Concentrated" is not the same as "popular".** The heatmap further down compares
  each borough against the city as a whole, which is a fairer test than raw counts —
  a borough can have the most pizzerias simply by being the biggest borough.
- **Not every gap is an opening.** A cuisine being scarce somewhere can mean an
  untapped market, or it can mean the locals there simply do not order it. This page
  shows you where to look, not what to conclude.
- **These are inspection records, not a business directory.** A place that has never
  been inspected will not appear here, and a place that closed years ago might.
        """
    )

if view.empty:
    st.warning("No restaurants match these filters. Widen the selection to continue.")
    st.stop()

# ----------------------------------------------------------------------- KPIs

known_cuisine = view[~view["cuisine"].isin(NON_CUISINES)]

col1, col2, col3, col4 = st.columns(4)
col1.metric(
    "Restaurants",
    f"{len(view):,}",
    help="Food businesses on record with the city health department, within the "
         "filters you have set on the left.",
)
col2.metric(
    "Neighbourhoods",
    f"{view['nta_code'].nunique():,}",
    help="How many of the city's official neighbourhood areas these restaurants "
         "sit in. New York has 193 of them in total.",
)
col3.metric(
    "Typical hygiene score",
    f"{view['avg_score'].median():.1f}" if view["avg_score"].notna().any() else "—",
    help="The middle restaurant's average inspection score — half score better, half "
         "worse. LOWER IS BETTER: inspectors add points for each problem found. "
         "13 points or below earns an A grade from the city.",
)
col4.metric(
    "Shut down at least once",
    f"{view['ever_closed'].mean() * 100:.1f}%",
    help="Share of these restaurants the health department has ordered closed at "
         "some point since 2007. Most reopen after fixing the problem.",
)

st.divider()

# --------------------------------------------------------------- map + mix

map_col, mix_col = st.columns([3, 2], gap="large")

with map_col:
    st.subheader("Where they are")
    st.caption("Each dot is one restaurant. Hover to see its name and cuisine.")
    mappable = view.dropna(subset=["latitude", "longitude"])

    fig_map = px.scatter_map(
        mappable,
        lat="latitude",
        lon="longitude",
        hover_name="dba",
        hover_data={"cuisine": True, "boro": True, "latitude": False, "longitude": False},
        color_discrete_sequence=[BLUE],
        zoom=9.2,
        height=520,
    )
    fig_map.update_traces(marker={"size": 4, "opacity": 0.55})
    fig_map.update_layout(
        map_style="carto-positron",
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        showlegend=False,
    )
    st.plotly_chart(fig_map, use_container_width=True)
    st.caption(
        f"{len(mappable):,} of {len(view):,} shown. The other "
        f"{len(view) - len(mappable):,} have no map location on file, so they count "
        "in the totals above but cannot be placed here."
    )

with mix_col:
    st.subheader("What they serve")
    st.caption("The 15 most common cuisines in your current selection.")
    top_cuisines = known_cuisine["cuisine"].value_counts().head(15).sort_values()

    fig_mix = go.Figure(
        go.Bar(
            x=top_cuisines.values,
            y=[c.title() for c in top_cuisines.index],
            orientation="h",
            marker_color=BLUE,
            hovertemplate="%{y}: %{x:,} restaurants<extra></extra>",
        )
    )
    fig_mix.update_layout(
        height=520,
        margin={"l": 0, "r": 10, "t": 0, "b": 0},
        xaxis_title=None,
        yaxis_title=None,
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"showgrid": True, "gridcolor": "#e5e4e0"},
    )
    st.plotly_chart(fig_mix, use_container_width=True)
    st.caption(
        f"Out of {len(known_cuisine):,} restaurants with a cuisine worth counting. "
        f"Another {len(view) - len(known_cuisine):,} are either blank or filed simply "
        "as \"Other\", so they sit in the totals above but not in this chart."
    )

st.divider()

# ------------------------------------------------------- location quotient

st.subheader("Which cuisines cluster where")
st.markdown(
    "Counting restaurants alone mostly tells you which borough is biggest. This "
    "compares each borough **against the city as a whole** instead, so the size of the "
    "borough cancels out."
)
st.markdown(
    """
| You see | It means |
|---|---|
| **1.0** | This borough has its fair share — same as the city average |
| **2.0** | **Twice** as concentrated here as citywide — a local speciality |
| **0.5** | **Half** as common here as citywide — thin on the ground |
"""
)
st.caption(
    "Blue = more of this cuisine than the city average · Red = less · Grey = about "
    "average. The city-wide comparison always uses all five boroughs, so changing the "
    "borough filter never moves the goalposts."
)

lq_cuisines = cuisines if cuisines else citywide_share.head(12).index.tolist()
lq_boroughs = [b for b in BORO_ORDER if b in boroughs]

crosstab = pd.crosstab(baseline["cuisine"], baseline["boro"])
crosstab = crosstab.reindex(columns=BORO_ORDER, fill_value=0)
lq = crosstab.div(crosstab.sum(axis=0), axis=1).div(citywide_share, axis=0)
lq_view = lq.reindex(index=lq_cuisines, columns=lq_boroughs).dropna(how="all")

if lq_view.empty or not lq_boroughs:
    st.info("Select at least one borough to see concentration.")
else:
    fig_lq = px.imshow(
        lq_view,
        labels={"x": "", "y": "", "color": "vs city average"},
        x=lq_view.columns,
        y=[c.title() for c in lq_view.index],
        color_continuous_scale=DIVERGING,
        color_continuous_midpoint=1.0,
        text_auto=".2f",
        aspect="auto",
        height=max(320, 42 * len(lq_view)),
    )
    fig_lq.update_traces(
        hovertemplate="%{y} in %{x}<br>%{z:.2f}x the city average<extra></extra>",
        xgap=2, ygap=2,
    )
    fig_lq.update_layout(margin={"l": 0, "r": 0, "t": 10, "b": 0})
    st.plotly_chart(fig_lq, use_container_width=True)

st.divider()

# ------------------------------------------------------- neighbourhood table

st.subheader("Neighbourhood by neighbourhood")
st.caption(
    "Borough averages hide a great deal. Manhattan's busiest neighbourhood has "
    "2,258 restaurants and its quietest has 11 — both are 'Manhattan'."
)

nta_stats = (
    view.dropna(subset=["nta_code"])
    .groupby("nta_code")
    .agg(restaurants=("camis", "size"), avg_score=("avg_score", "mean"))
    .join(neighborhoods.set_index("nta_code")[["nta_name", "borough", "population_2010"]])
    .dropna(subset=["nta_name"])
)

# Park and cemetery tracts hold a token population, which turns any per-capita
# figure into noise. Excluded entirely, as in notebook 03.
nta_stats = nta_stats[~nta_stats["nta_name"].str.contains("park-cemetery-etc", case=False)]
nta_stats = nta_stats[nta_stats["restaurants"] >= min_stores]

if nta_stats.empty:
    st.info("No neighbourhood clears the minimum. Lower the slider to see results.")
else:
    # Airport tracts have restaurants but no residents, so the ratio is undefined
    # rather than merely large — JFK would otherwise read as infinity per 10,000.
    # The row stays (61 restaurants is worth seeing); only the ratio is blanked.
    residents = nta_stats["population_2010"].where(nta_stats["population_2010"] > 0)
    nta_stats["per_10k"] = (nta_stats["restaurants"] / residents * 10000).round(1)
    nta_stats["avg_score"] = nta_stats["avg_score"].round(1)

    display = (
        nta_stats.reset_index()
        .rename(columns={
            "nta_name": "Neighbourhood", "borough": "Borough",
            "restaurants": "Restaurants", "population_2010": "Residents",
            "per_10k": "Restaurants per 10,000 residents",
            "avg_score": "Typical hygiene score",
        })
        [["Neighbourhood", "Borough", "Restaurants", "Residents",
          "Restaurants per 10,000 residents", "Typical hygiene score"]]
        .sort_values("Restaurants", ascending=False)
    )

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        height=420,
        column_config={
            "Neighbourhood": st.column_config.TextColumn(
                help="The city's official neighbourhood areas — the same ones used "
                     "for census reporting."
            ),
            "Restaurants": st.column_config.NumberColumn(format="%d"),
            "Residents": st.column_config.NumberColumn(
                format="%d", help="People living there, 2010 Census."
            ),
            "Restaurants per 10,000 residents": st.column_config.NumberColumn(
                format="%.1f",
                help="How well the people who live there are served. Read business "
                     "districts with care: Midtown scores enormously high because it "
                     "feeds commuters and tourists, not its few residents.",
            ),
            "Typical hygiene score": st.column_config.NumberColumn(
                format="%.1f",
                help="Lower is better. 13 or below is A-grade territory.",
            ),
        },
    )
    st.caption(
        f"Showing {len(display)} neighbourhoods with at least {min_stores} "
        "restaurants — smaller ones are left out because a handful of restaurants "
        "makes for a jumpy ranking. Click any column heading to sort by it. Parks "
        "and cemeteries are excluded, since almost nobody lives in them."
    )

# ------------------------------------------------------------------- footer

st.divider()
st.markdown(
    """
**Before you act on anything here.** A cuisine being scarce in a neighbourhood is a
question worth asking, not an answer. It can mean nobody has served that market yet —
or that the people living there do not want it, cannot afford it, or that somebody
tried and closed. This data cannot tell those apart. Treat a gap as a place to go and
look, not as a business case.
    """
)
st.caption(
    "Restaurant counts and hygiene scores: New York City Health Department inspection "
    "records, updated daily. Population: 2010 US Census. Full method and its limits: "
    "github.com/AprilLovesData/nyc-restaurant-intelligence"
)
