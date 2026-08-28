"""NYC Restaurant Intelligence Platform — Market Overview dashboard.

Reads the normalised tables from Supabase and lets the visitor ask their own
question of the data, rather than replaying the fixed views in the notebooks.

Run locally:
    streamlit run streamlit_app.py
"""

from __future__ import annotations

import hmac
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

# The date the source CSV was pulled from NYC Open Data. Nothing in this pipeline
# refreshes itself, so this is stated on the page rather than left for the reader
# to assume the data is current.
SNAPSHOT_DATE = "11 August 2026"

# --------------------------------------------------------------------- access

# A door on the page, not a lock on the data.
#
# This gate decides who may open the dashboard. It does NOT decide who may read the
# underlying rows: the Supabase key ships inside the app, so anyone who knows the
# REST endpoint can still query the tables directly. Real per-user data isolation
# belongs in Supabase row level security, keyed on an authenticated user — which is
# a separate piece of work, and the one that actually protects anything.
#
# Credentials live in secrets.toml (git-ignored), never in this file.


def _credentials_match(username: str, password: str) -> bool:
    users = st.secrets.get("auth", {}).get("users", {})
    expected = users.get(username)
    if expected is None:
        # Compare anyway, against a dummy of similar length, so that a wrong
        # username and a wrong password take the same time to reject.
        hmac.compare_digest(password, "x" * len(password))
        return False
    return hmac.compare_digest(str(expected), password)


def require_login() -> str:
    """Show the dashboard only to a signed-in visitor. Returns the username."""
    if "auth_user" in st.session_state:
        return st.session_state["auth_user"]

    if "auth" not in st.secrets or not st.secrets["auth"].get("users"):
        st.error(
            "No sign-in credentials are configured, so the dashboard is closed.\n\n"
            "Add them to `.streamlit/secrets.toml`:\n\n"
            "```toml\n[auth.users]\nyour_username = \"your_password\"\n```\n\n"
            "On Streamlit Community Cloud, paste the same block into "
            "**Settings → Secrets**."
        )
        st.stop()

    _, middle, _ = st.columns([1, 1.4, 1])
    with middle:
        st.title("NYC Restaurant Market Overview")
        st.caption("Gateway Solutions · please sign in to continue")

        with st.form("sign_in"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)

        if submitted:
            if _credentials_match(username, password):
                st.session_state["auth_user"] = username
                st.rerun()
            else:
                st.error("That username and password combination was not recognised.")

    st.stop()


current_user = require_login()

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

# Census income and rent, aggregated to neighbourhood level. 194 rows of static
# reference data, so it travels with the code rather than the database.
ACS_FILE = Path(__file__).parent / "data" / "cleaned" / "nta_acs_2022.csv"

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

    if ACS_FILE.exists():
        acs = pd.read_csv(ACS_FILE)
        neighborhoods = neighborhoods.merge(acs, on="nta_code", how="left")
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

with st.sidebar:
    signed_in, sign_out = st.columns([2, 1], vertical_alignment="center")
    signed_in.caption(f"Signed in as **{current_user}**")
    if sign_out.button("Sign out", use_container_width=True):
        del st.session_state["auth_user"]
        st.rerun()
    st.divider()

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
    st.sidebar.caption("Showing a saved copy so the page loads quickly.")
    # Deliberately not called "latest": this reaches the database, and the database
    # is itself a fixed snapshot. Nothing here goes back to the city's live feed.
    if st.sidebar.button("Re-read from database", use_container_width=True):
        shutil.rmtree(CACHE_DIR)
        st.cache_data.clear()
        st.rerun()

st.sidebar.caption(
    f"Source: New York City Health Department restaurant inspection records, "
    f"**downloaded {SNAPSHOT_DATE}**. The city updates its records daily; this "
    "dashboard reads a fixed copy taken on that date, so newly opened or newly "
    "inspected restaurants will not appear until the snapshot is refreshed. "
    "Note also that it covers places the city has inspected — it is not a full "
    "business directory."
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

# ------------------------------------------------------------------ layout

# Scott's note was that a map, a bar chart and a heatmap stacked down one page
# reads as a pile of outputs rather than a product. Splitting the page by the
# question each half answers — what does the market look like, and where should
# I open — gives it the shape of a tool.
tab_overview, tab_finder, tab_gaps = st.tabs([
    "Market Overview",
    "Location Finder",
    "Market Gaps",
])

with tab_overview:
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

# ------------------------------------------------------------ location finder

with tab_finder:
    st.subheader("Where should this concept open?")
    st.markdown(
        "Pick a cuisine and this ranks every neighbourhood in the city on how well "
        "it would suit that concept — then shows you why, so you can disagree with "
        "the reasoning rather than take the number on faith."
    )

    picker_left, picker_right = st.columns([2, 3], gap="large")

    with picker_left:
        target_cuisine = st.selectbox(
            "Cuisine you want to open",
            options=cuisine_options,
            index=cuisine_options.index("KOREAN") if "KOREAN" in cuisine_options else 0,
            format_func=str.title,
        )
        target_boroughs = st.multiselect(
            "Boroughs to consider", options=BORO_ORDER, default=BORO_ORDER,
        )

    with picker_right:
        st.markdown("**What matters most to you?**")
        st.caption(
            "The score is a weighted blend of three things. Move these and the "
            "ranking moves with them — there is no single right answer, only "
            "assumptions you should be able to see."
        )
        w1, w2, w3 = st.columns(3)
        weight_demand = w1.slider("Unmet demand", 0, 100, 50, 5,
                                  help="Residents per existing restaurant of this "
                                       "cuisine. High means many people, few "
                                       "competitors.")
        weight_income = w2.slider("Spending power", 0, 100, 30, 5,
                                  help="Median household income of the neighbourhood.")
        weight_vitality = w3.slider("Dining culture", 0, 100, 20, 5,
                                    help="Restaurants per resident overall — does "
                                         "this neighbourhood eat out at all?")

    weights = {"demand": weight_demand, "income": weight_income,
               "vitality": weight_vitality}
    if sum(weights.values()) == 0:
        st.warning("Set at least one weight above zero.")
        st.stop()

    # ---- build the candidate table -------------------------------------------

    scope = restaurants[restaurants["boro"].isin(target_boroughs)]
    per_nta = (
        scope.dropna(subset=["nta_code"])
        .groupby("nta_code")
        .agg(total_restaurants=("camis", "size"))
    )
    same_cuisine = (
        scope[scope["cuisine"] == target_cuisine]
        .dropna(subset=["nta_code"])
        .groupby("nta_code")
        .agg(same_cuisine=("camis", "size"))
    )

    reference = neighborhoods.set_index("nta_code")
    candidates = (
        per_nta.join(same_cuisine, how="left")
        .join(reference[["nta_name", "borough", "population_2010"]])
        .join(reference[["median_income", "median_rent"]]
              if "median_income" in reference.columns else None)
    )
    candidates["same_cuisine"] = candidates["same_cuisine"].fillna(0).astype(int)
    candidates = candidates[
        candidates["borough"].isin(target_boroughs)
        & (candidates["population_2010"] > 0)
        & ~candidates["nta_name"].str.contains("park-cemetery-etc", case=False, na=True)
    ]

    # Residents per existing competitor. The +1 keeps a neighbourhood with zero
    # competitors from dividing by zero, and reads sensibly: it is the demand one
    # new restaurant would face.
    candidates["residents_per_competitor"] = (
        candidates["population_2010"] / (candidates["same_cuisine"] + 1)
    )
    candidates["restaurants_per_10k"] = (
        candidates["total_restaurants"] / candidates["population_2010"] * 10000
    )

    # Percentile rank rather than raw values: income is in dollars and density is a
    # ratio, so they cannot be averaged directly. Ranking puts every component on
    # the same 0-100 scale and makes the weights mean what they say.
    def rank(column: str) -> pd.Series:
        return candidates[column].rank(pct=True) * 100

    components = {
        "demand": rank("residents_per_competitor"),
        "vitality": rank("restaurants_per_10k"),
    }
    has_income = "median_income" in candidates.columns and candidates["median_income"].notna().any()
    components["income"] = rank("median_income") if has_income else pd.Series(
        50.0, index=candidates.index
    )

    total_weight = sum(weights.values())
    candidates["score"] = sum(
        components[key] * weight for key, weight in weights.items()
    ) / total_weight

    ranked = candidates.sort_values("score", ascending=False)

    if not has_income:
        st.info("Income data is unavailable, so spending power scores neutrally "
                "for every neighbourhood.")

    # ---- the recommendation ---------------------------------------------------

    if ranked.empty:
        st.warning("No neighbourhood matches. Widen the borough selection.")
    else:
        top = ranked.iloc[0]
        st.success(
            f"**{top['nta_name']}** ({top['borough']}) ranks highest for "
            f"{target_cuisine.title()}. "
            f"{int(top['population_2010']):,} residents, "
            f"{int(top['same_cuisine'])} existing "
            f"{target_cuisine.title()} restaurant"
            f"{'' if top['same_cuisine'] == 1 else 's'}"
            + (f", median household income ${int(top['median_income']):,}."
               if has_income and pd.notna(top["median_income"]) else ".")
        )

        map_col2, table_col = st.columns([2, 3], gap="large")

        with map_col2:
            located = (
                scope.dropna(subset=["nta_code", "latitude", "longitude"])
                .groupby("nta_code")
                .agg(latitude=("latitude", "mean"), longitude=("longitude", "mean"))
            )
            plot = ranked.join(located, how="inner").reset_index()
            fig_score = px.scatter_map(
                plot, lat="latitude", lon="longitude",
                size="total_restaurants", color="score",
                color_continuous_scale=SEQ_BLUE, size_max=28, zoom=8.8, height=430,
                hover_name="nta_name",
                hover_data={"score": ":.0f", "same_cuisine": True,
                            "latitude": False, "longitude": False,
                            "total_restaurants": False},
                labels={"score": "Opportunity"},
            )
            fig_score.update_layout(
                map_style="carto-positron",
                margin={"l": 0, "r": 0, "t": 0, "b": 0},
            )
            st.plotly_chart(fig_score, use_container_width=True)
            st.caption("Darker means a better fit for this concept. Bubble size is "
                       "how many restaurants the neighbourhood already holds.")

        with table_col:
            shortlist = ranked.head(12).reset_index()
            shortlist["score"] = shortlist["score"].round(0)
            display_cols = {
                "nta_name": "Neighbourhood", "borough": "Borough", "score": "Score",
                "population_2010": "Residents", "same_cuisine": "Competitors",
                "residents_per_competitor": "Residents per competitor",
            }
            if has_income:
                display_cols["median_income"] = "Median income"
            table = shortlist[list(display_cols)].rename(columns=display_cols)
            st.dataframe(
                table, use_container_width=True, hide_index=True, height=430,
                column_config={
                    "Score": st.column_config.ProgressColumn(
                        format="%d", min_value=0, max_value=100,
                        help="0-100, blended from the three weights above."),
                    "Residents": st.column_config.NumberColumn(format="%d"),
                    "Residents per competitor": st.column_config.NumberColumn(
                        format="%d",
                        help=f"People per existing {target_cuisine.title()} "
                             "restaurant. Higher means less contested."),
                    "Median income": st.column_config.NumberColumn(format="$%d"),
                },
            )

    st.divider()

    # ---- competition check ----------------------------------------------------

    st.subheader("How crowded is it already?")
    st.caption(
        f"Existing {target_cuisine.title()} restaurants per borough, against what "
        "that borough's size would lead you to expect."
    )

    city_share = (baseline["cuisine"] == target_cuisine).mean()
    saturation = []
    for borough in target_boroughs:
        in_boro = baseline[baseline["boro"] == borough]
        if in_boro.empty:
            continue
        actual = int((in_boro["cuisine"] == target_cuisine).sum())
        expected = round(len(in_boro) * city_share)
        saturation.append({
            "Borough": borough,
            f"{target_cuisine.title()} restaurants": actual,
            "Expected at citywide rate": expected,
            "Gap": actual - expected,
        })

    if saturation:
        sat = pd.DataFrame(saturation)
        st.dataframe(
            sat, use_container_width=True, hide_index=True,
            column_config={
                "Gap": st.column_config.NumberColumn(
                    format="%d",
                    help="Negative means fewer than the borough's size would "
                         "suggest — the kind of gap worth investigating."),
            },
        )
        st.caption(
            "A negative gap is a question, not a verdict: it can mean an unserved "
            "market, or that the borough has already decided it does not want this "
            "cuisine. The ranking above cannot tell those apart either."
        )

    with st.expander("How the score is calculated"):
        st.markdown(
            f"""
Every neighbourhood is scored on three components, each converted to a
**percentile rank from 0 to 100** so that dollars, headcounts and ratios can be
combined at all. Your sliders set the weights; the current blend is
**{weight_demand}% unmet demand, {weight_income}% spending power,
{weight_vitality}% dining culture**.

| Component | Measured as | Why |
|---|---|---|
| Unmet demand | Residents ÷ (existing {target_cuisine.title()} restaurants + 1) | The audience one new restaurant would face |
| Spending power | Median household income, ACS 2018–2022 | Whether that audience can pay restaurant prices |
| Dining culture | Restaurants per 10,000 residents | Whether the neighbourhood eats out at all |

**What it deliberately leaves out.** Rent, footfall, transit access, parking,
tourism, and the actual demographics of who lives there. A high score means the
arithmetic of population against competition looks favourable — nothing more. It
is a shortlist for site visits, not a decision.

**Known limits.** Income is aggregated from census tracts to neighbourhoods as a
population-weighted mean of tract medians, which is an approximation — a true
neighbourhood median would need the underlying microdata. Population is the 2010
Census, the only vintage published for these neighbourhood boundaries.
            """
        )

# --------------------------------------------------------------- market gaps

with tab_gaps:
    st.subheader("What is missing from this neighbourhood?")
    st.markdown(
        "The Location Finder starts from a concept and looks for a place. This "
        "starts from a place and looks for the concept — the question an operator "
        "asks when the lease is already the fixed part."
    )

    gap_left, gap_right = st.columns([2, 3], gap="large")

    with gap_left:
        gap_boro = st.selectbox("Borough", options=BORO_ORDER, key="gap_boro")
        area_options = (
            neighborhoods[neighborhoods["borough"] == gap_boro]
            .dropna(subset=["nta_name"])
            .sort_values("nta_name")
        )
        area_options = area_options[
            ~area_options["nta_name"].str.contains("park-cemetery-etc", case=False)
        ]
        area_names = ["— the whole borough —"] + area_options["nta_name"].tolist()
        chosen_area = st.selectbox("Neighbourhood", options=area_names, key="gap_area")

    with gap_right:
        min_citywide = st.slider(
            "Only consider cuisines with at least this many restaurants citywide",
            min_value=50, max_value=1000, value=300, step=50,
            help="A cuisine with a handful of locations anywhere is not a proven "
                 "format. This filters out the long tail so the gaps that surface "
                 "are ones somebody has already made work elsewhere.",
        )
        st.caption(
            "Saturation compares competitors **per resident** here against the same "
            "figure citywide. 1.0 means this area carries its fair share for its "
            "population; below 1.0 means fewer competitors per potential customer "
            "than the city average."
        )

    # ---- scope --------------------------------------------------------------

    if chosen_area == "— the whole borough —":
        local = baseline[baseline["boro"] == gap_boro]
        local_population = float(
            neighborhoods.loc[neighborhoods["borough"] == gap_boro, "population_2010"]
            .fillna(0).sum()
        )
        area_label = gap_boro
    else:
        code = area_options.loc[
            area_options["nta_name"] == chosen_area, "nta_code"
        ].iloc[0]
        local = baseline[baseline["nta_code"] == code]
        local_population = float(
            neighborhoods.loc[neighborhoods["nta_code"] == code,
                              "population_2010"].fillna(0).iloc[0]
        )
        area_label = chosen_area

    city_population = float(neighborhoods["population_2010"].fillna(0).sum())

    if local.empty or local_population <= 0:
        st.warning("Not enough data for this area.")
    else:
        established = baseline["cuisine"].value_counts()
        established = established[established >= min_citywide]

        rows = []
        for cuisine, citywide_count in established.items():
            here = int((local["cuisine"] == cuisine).sum())
            # Competitors per 10,000 residents, here and citywide. Using population
            # rather than share of restaurants answers the operator's actual
            # question: how many rivals am I splitting these customers with?
            here_per_10k = here / local_population * 10000
            city_per_10k = citywide_count / city_population * 10000
            saturation = here_per_10k / city_per_10k if city_per_10k else None
            rows.append({
                "Cuisine": cuisine.title(),
                "Here": here,
                "Per 10k residents": round(here_per_10k, 2),
                "Citywide per 10k": round(city_per_10k, 2),
                "Saturation": round(saturation, 2) if saturation is not None else None,
                "At citywide rate": round(city_per_10k * local_population / 10000),
            })

        table = pd.DataFrame(rows)
        table["Shortfall"] = (table["At citywide rate"] - table["Here"]).astype(int)

        st.markdown(f"### {area_label} — {int(local_population):,} residents, "
                    f"{len(local):,} restaurants")

        gaps_only = table[table["Saturation"] < 0.5].sort_values("Saturation")

        if gaps_only.empty:
            st.info(
                f"No established cuisine is notably under-represented in "
                f"{area_label} — every proven format already has at least half "
                "its citywide share here."
            )
        else:
            biggest = gaps_only.iloc[0]
            st.success(
                f"**{biggest['Cuisine']}** is the widest gap: "
                f"{int(biggest['Here'])} here against "
                f"{int(biggest['At citywide rate'])} at the citywide rate for this "
                f"population — a saturation of {biggest['Saturation']:.2f}."
            )

        chart_col, table_col2 = st.columns([2, 3], gap="large")

        with chart_col:
            plot = table.sort_values("Saturation").head(14).sort_values("Saturation")
            fig_gap = go.Figure(go.Bar(
                x=plot["Saturation"], y=plot["Cuisine"], orientation="h",
                marker_color=[
                    "#d03b3b" if v < 0.5 else BLUE if v < 1 else "#184f95"
                    for v in plot["Saturation"]
                ],
                hovertemplate="%{y}: %{x:.2f}x the citywide rate<extra></extra>",
            ))
            fig_gap.add_vline(x=1.0, line_width=1, line_dash="dash",
                              line_color=INK_SOFT)
            fig_gap.update_layout(
                height=440, margin={"l": 0, "r": 10, "t": 10, "b": 0},
                xaxis_title="Competitors per resident, vs the city average",
                yaxis_title=None, plot_bgcolor="rgba(0,0,0,0)",
                xaxis={"showgrid": True, "gridcolor": "#e5e4e0"},
            )
            st.plotly_chart(fig_gap, use_container_width=True)
            st.caption("Red marks cuisines running at under half the citywide rate. "
                       "The dashed line is parity.")

        with table_col2:
            st.dataframe(
                table.sort_values("Saturation")[
                    ["Cuisine", "Here", "At citywide rate", "Shortfall", "Saturation"]
                ],
                use_container_width=True, hide_index=True, height=440,
                column_config={
                    "Here": st.column_config.NumberColumn(
                        format="%d", help=f"Restaurants of this cuisine in {area_label}."),
                    "At citywide rate": st.column_config.NumberColumn(
                        format="%d",
                        help="How many there would be if this area matched the city "
                             "average for its population."),
                    "Shortfall": st.column_config.NumberColumn(
                        format="%d", help="The difference. Positive means fewer than "
                                          "expected."),
                    "Saturation": st.column_config.ProgressColumn(
                        format="%.2f", min_value=0, max_value=3,
                        help="Under 1.00 means less competition per resident than "
                             "the city average."),
                },
            )

    with st.expander("How saturation is measured"):
        st.markdown(
            """
For each cuisine:

$$\text{Saturation} = \frac{\text{competitors per 10,000 residents here}}
{\text{competitors per 10,000 residents citywide}}$$

Below 1.00 means fewer rivals per potential customer than the city average; above
means more. The **shortfall** column converts that into a count — how many
restaurants would have to open here to reach parity.

**Why per resident rather than per restaurant.** The Market Overview tab compares
each cuisine's *share* of a borough's restaurants. That answers "what is this area
known for". An operator is asking something different: how many competitors am I
splitting these customers with? That question needs population in the denominator.
The two measures can disagree, and when they do it is usually because an area has
an unusual number of restaurants for its population.

**The citywide floor exists for a reason.** Without it the list fills with cuisines
that are scarce everywhere. Requiring a proven citywide presence means each gap is
a format somebody has already made work in New York.

**A gap is not a recommendation.** Low saturation can mean an unserved market, a
market that has rejected this cuisine, or one where operators have already tried
and closed. Nothing here distinguishes those.
            """
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
