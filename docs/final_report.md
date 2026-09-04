# Final Internship Report

**Project:** NYC Restaurant Intelligence Platform
**Intern:** Yiyou "April" Qian · AI-Consulting Analyst Intern
**Organisation:** Gateway Solutions
**Duration:** Four weeks
**Repository:** https://github.com/AprilLovesData/nyc-restaurant-intelligence
**Live platform:** https://nyc-restaurant-intelligence.streamlit.app

---

## 1. What was delivered

A working decision-support platform for restaurant location and market analysis, built
from public data, deployed and access-controlled.

```
3 public data sources  →  5 notebooks  →  5 database tables  →  3 analytical modules
                          audit / clean / analyse / model / load
```

**Against the plan's Minimum Required Scope, all six items are complete:**

| Required | Delivered |
|---|---|
| Central restaurant database | Five normalised tables in Supabase — 31,222 restaurants, 93,106 inspections, 288,486 violations |
| Restaurant Market Overview | Borough and cuisine landscape, concentration analysis, neighbourhood drill-down |
| Location Opportunity Analyzer | "Location Finder" — ranks all neighbourhoods for a chosen cuisine, with user-adjustable weights |
| Competition and Market Gap Analyzer | "Market Gaps" — per-resident saturation and shortfall by area |
| Customer-facing Streamlit application | Deployed, behind a sign-in gate |
| Technical and operational documentation | Seven documents, listed in section 6 |

**Not built,** and recorded as a deliberate trade rather than an oversight: the Week 3
modules — Inspection Risk Analyzer, Restaurant Comparison Tool, Trend Tracker. The plan
lists these as secondary priorities. With the time available I chose to complete the
required scope and its documentation rather than begin a fourth module I could not
finish to the same standard. The violation data they need is already loaded and
indexed, so the Inspection Risk Analyzer is the cheapest of the three to pick up.

---

## 2. Principal findings

**The market is concentrated in Manhattan, and density is the reason.** Manhattan holds
40% of the city's restaurants at 73.5 per 10,000 residents — 4.1 times the Bronx (17.9).

**Raw share hides character; concentration reveals it.** American leads every borough,
but its location quotient never leaves 0.73–1.30, marking it as a catch-all category
rather than a regional preference. The cuisines with genuine geographic identity are
Caribbean — 1.82 in Brooklyn against 0.11 on Staten Island, a sixteen-fold spread — and
Latin American.

**Borough averages describe almost no actual neighbourhood.** Manhattan's neighbourhoods
range from 11 restaurants to 2,258 — a 205-fold spread inside one borough. The gap
between two Bronx neighbourhoods (14x) is wider than the gap between Manhattan and the
Bronx (4.1x). A single neighbourhood, Midtown, holds 2,258 restaurants: comparable to
the entire Bronx (2,632) spread across 38 neighbourhoods.

**Size is not variety.** Cuisine diversity plateaus around 3.2 past roughly 200
restaurants, but Flushing carries 500+ restaurants at a diversity of 1.99 against a
median of 2.85 — a single-cuisine destination rather than an underserved market.

**Per-capita density separates two different kinds of place.** Midtown reads at 788.7
restaurants per 10,000 residents against a median of 23.7. That is not a dense
restaurant market; it is a business district feeding commuters who are not in the
denominator. The thinnest genuine coverage is in large residential neighbourhoods —
Soundview-Castle Hill (7.5), South Jamaica (8.2), and Borough Park, whose 106,357
residents are served by 116 restaurants.

**A defensible gap, checked rather than assumed.** For Korean, the model ranks the Upper
West Side first: 132,378 residents, $140,206 median household income, zero Korean
restaurants. Verified against the records before being reported — the neighbourhood
holds 413 restaurants, 58 of them Asian, so the absence is specific to Korean rather
than to Asian food. Korean restaurants citywide cluster in Midtown (93) and Murray Hill,
Queens (90), the two Koreatowns.

---

## 3. Challenges, and what they taught

The most valuable work was not the charts. It was six failures where the code ran
without error, the page rendered, and the numbers were wrong.

| # | Problem | Consequence if undetected | How it surfaced |
|---|---|---|---|
| 1 | One row is one violation, not one restaurant | Mean inspection score inflated 43% (25.62 against a true 17.87), systematically understating citywide hygiene | Computed the same metric at two grains and compared |
| 2 | ZIP codes written as `10462.0` | Postgres accepts it into a text column **without error**; every downstream ZIP filter would silently miss | Full-column type scan after an unrelated import failure |
| 3 | Supabase caps responses at 1,000 rows | 1,000 of 31,222 restaurants displayed, returning HTTP 200 | Requested the exact row count first and compared against what assembled |
| 4 | Booleans arrive as `t`/`f`, not `true`/`false` | 1,285 forced closures read as zero; the KPI showed 0.0% | Cross-checked against a figure already known to be 4.1% |
| 5 | Airport neighbourhoods have zero residents | Per-capita density divided by zero | Outlier review |
| 6 | The basemap provider began requiring an API key | Maps rendered as grey boxes with no code change | A watermark in a screenshot, after three wrong hypotheses |

**The common thread:** nothing crashed. In every case the program was working and the
output was wrong. The only defence that actually worked was checking each result against
a number already known to be correct — which is why every stage of the pipeline asserts
its own expectations, and why a failing assertion should be read as the pipeline
working.

**The sixth is a different lesson.** The map broke without anyone touching the code,
because a third-party tile provider changed its terms. A dependency is not only the
libraries you install; it is every external service you call, and those change without
telling you. The requirements file said `plotly>=5.24`, which meant every platform
rebuild installed whatever was newest. Both are now pinned.

**A seventh worth recording:** the Supabase free tier de-provisions projects after a
week without traffic, which took the deployed dashboard down entirely. The dashboard now
falls back to a committed snapshot and says so on the page, rather than showing a stack
trace. It also raises a real hosting question if the platform is put in front of clients.

---

## 4. Judgment calls, documented rather than silently applied

- **50.8% of records have no letter grade** — not an error. Cross-tabulation confirmed
  DOHMH grades only Cycle and Pre-permit inspections. Imputing here would have corrupted
  every grade distribution.
- **1,907 rows score above 100** — not outliers to discard. 75% coincide with a forced
  closure, against 4% citywide, so they are genuine extreme violations.
- **3,641 rows dated 1900-01-01** — not corrupt dates. They are permitted but
  never-yet-inspected establishments: excluded from trend analysis, retained for market
  size.
- **149 violation codes map to 241 descriptions** — DOHMH has reworded conditions over
  the years. Kept as a code-plus-description lookup rather than force-merged, which
  would have rewritten historical records.
- **Borough boundary geometry is not in the database.** One cell holds 1.3 MB of
  coordinates and is never queried, only read whole to draw a map. It lives in the
  repository as a file.

---

## 5. Skills developed

**Data engineering.** Designing a normalised schema from a flat extract; foreign keys
and load ordering; row-level security and the difference between a table grant and a
policy; why `violations` shrank from 251.8 MB to 6.9 MB once repeated text moved into
lookup tables.

**Analysis.** Choosing a metric that answers the question rather than the one that is
easiest to compute — location quotient over raw share, per-resident saturation over
per-restaurant share, and knowing when the two disagree and why.

**Communication.** The hardest revision was not technical. Rewriting the dashboard for
someone who has never seen a statistic — replacing "median", "DOHMH" and "location
quotient" with language a restaurant owner reads without stopping — took longer than
building the module it described, and mattered more.

**Judgment.** Deciding not to run the data refresh forty minutes before a review,
because the load clears the tables before reloading them and a partial run would have
meant an empty database during a demo. Knowing when not to deploy is part of the job.

---

## 6. Deliverables

| Deliverable | Location |
|---|---|
| Data quality audit and cleaning pipeline | `notebooks/01_data_quality_check.ipynb` |
| Market overview analysis | `notebooks/02_market_overview.ipynb` |
| Geographic and neighbourhood analysis | `notebooks/03_geographic_analysis.ipynb` |
| Database schema and normalisation | `notebooks/04_database_schema.ipynb`, `sql/schema.sql` |
| Deployed platform | `streamlit_app.py` |
| One-command data refresh | `scripts/refresh_data.py` |
| Project requirements | `docs/project_requirements_document.md` |
| Data source inventory | `docs/data_source_inventory.md` |
| Scoring methodology | `docs/scoring_methodology.md` |
| Data refresh SOP | `docs/data_refresh_sop.md` |
| Consultant user guide | `docs/consultant_user_guide.md` |
| Client summary report template | `docs/client_summary_report_template.md` |
| Product roadmap | `docs/product_roadmap.md` |
| Data quality report, data dictionary, cleaning log | `reports/` |
| 11 analytical figures | `reports/figures/` |

---

## 7. Known limitations

- **Cuisine shares use a denominator of 26,957**, not 31,222. The 4,265 excluded are
  3,643 with no cuisine label, 589 filed only as "Other", and 85 with an unresolved
  borough.
- **Two population vintages are in play.** Borough density uses the 2020 Census;
  neighbourhood density uses 2010, the only release published for these boundaries.
  They are not directly comparable.
- **805 restaurants have no coordinates** and appear in every count but on no map.
- **Neither score has been validated** against outcomes. They are internally coherent
  and externally untested.
- **A supply gap is a descriptive signal, not a business case.** Nothing in this data
  distinguishes an unserved market from one that has rejected a cuisine, or one where
  operators have already tried and closed.
- **The data is a fixed snapshot** dated 11 August 2026. The refresh procedure exists
  and is documented; it has not been run since.

---

## 8. Recommended next steps

In the order the current build makes cheapest, with reasoning in
`docs/product_roadmap.md`:

1. **Add household composition and age** from the ACS release already in use. Cuisine
   demand tracks who lives somewhere more closely than what they earn, and the pipeline
   for it exists.
2. **Validate the scores** against restaurants that have opened since 2024. It produces
   no new screen to demonstrate, and would do more for the platform's credibility than
   any additional feature.
3. **Per-user data permissions.** The sign-in gate controls who opens the page, not
   which rows they see. Real isolation lives in the database, and is required before any
   client is given direct access.
4. **Inspection Risk Analyzer.** The data is loaded and unused; no new source needed.

---

## 9. For whoever continues this

- Cleaning logic lives in the notebooks, and the refresh script re-executes them rather
  than reimplementing it. Keeping it that way is deliberate: two copies would drift, and
  the report and the dashboard would quietly stop agreeing.
- The notebooks assert their own expectations. A failing assertion is the pipeline doing
  its job.
- Every score states its own limits on the page it appears on. That was a deliberate
  choice and is worth preserving — an analysis that names its own boundaries is easier
  to defend than one where a client finds them first.
