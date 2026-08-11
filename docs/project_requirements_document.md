# Project Requirements Document

**Project:** NYC Restaurant Intelligence Platform
**Prepared by:** Yiyou "April" Qian
**Organization:** Gateway Solutions
**Repository:** https://github.com/AprilLovesData/nyc-restaurant-intelligence
**Dashboard:** https://nyc-restaurant-intelligence.streamlit.app

---

## 1. Project Purpose

The NYC Restaurant Intelligence Platform consolidates publicly available NYC
data into a structured, maintainable database and provides analytical tools
for market evaluation, location assessment, competitive analysis, operational
risk, and trend monitoring for Gateway Solutions and its restaurant-industry
clients.

## 2. Intended Users and Use Cases

| User | What they use the platform for |
|---|---|
| Restaurant entrepreneurs / site selectors | Identify borough × cuisine combinations with clear supply gaps |
| Chain / franchise expansion teams | Assess saturation of their own cuisine category across boroughs |
| Market researchers / investors | Understand citywide cuisine mix and regional variation |
| Gateway Solutions consultants | Prepare data-backed client analyses and proposals |

## 3. Principal Business Questions

| # | Question | Status after Week 1 |
|---|---|---|
| 1 | How large is the NYC restaurant market and how is it distributed by borough? | Answered — 31,222 restaurants; Manhattan holds ~40% of market share, density 73.5 per 10k residents |
| 2 | What does the citywide cuisine mix look like? | Answered — 89 cuisine categories; top 15 account for 73% of restaurants |
| 3 | Which boroughs favor which cuisines? | Answered — quantified using Location Quotient (LQ) |
| 4 | Which borough × cuisine combinations are undersupplied? | Answered — 9 combinations identified, 6 in the Bronx |
| 5 | Which neighborhoods have the lowest restaurants-per-capita? | Answered — neighborhood-level per-capita analysis, 282x spread |
| 6 | Is an undersupply a real business opportunity or simply lower local demand? | **Not answerable with current data** — requires Census income/demographic data (planned Week 2) |

## 4. Week 1 Scope

**Completed:**
- Data-quality audit and cleaning pipeline (12 issues identified, 14 validation
  assertions passing)
- Central database (Supabase, normalized schema, 5 tables)
- Market Overview analysis (borough, cuisine, and neighborhood/NTA level)
- Interactive dashboard, publicly deployed

**Explicitly out of scope for Week 1:**
- Inspection/health-violation trend analysis (data loaded, not yet analyzed)
- Violation-type breakdowns (`violations` table populated, not yet analyzed)
- Competitive density / trade-area analysis
- Any analysis requiring external data (income, rent, foot traffic)

## 5. Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| Analysis | Python / pandas / matplotlib | Standard data-analysis stack |
| Storage | Supabase (PostgreSQL) | Cloud-accessible, reachable from the deployed app; free tier covers current scale (500 MB) |
| Frontend | Streamlit | Pure-Python web app, no separate frontend build needed |
| Deployment | Streamlit Community Cloud | Free, connects directly to GitHub, redeploys automatically on push |
| Version control | Git / GitHub | — |

**Design decision:** Maps use static matplotlib images rather than interactive
folium maps, because folium's HTML output does not render on GitHub (shows
blank) — since the project's primary audience views it via GitHub, static
rendering was prioritized over interactivity.

## 6. Known Limitations (Week 1)

- Cuisine-share percentages use a denominator of 26,957, not the full 31,222.
  The 4,265 excluded are 3,643 with no cuisine label (11.7%), 589 labelled
  only "OTHER" (1.9%), and 85 with an unresolved borough (0.3%).
- Borough-level density uses 2020 Census population; neighborhood-level
  density uses 2010 Census population (the only year available for 2010-
  vintage NTAs) — the two are **not directly comparable**.
- 805 restaurants (2.6%) were never geocoded and carry neither coordinates nor
  an NTA code — the same 805 records in both cases — so they appear in every
  count and in no map.
- A "supply gap" is a descriptive signal, not a validated business
  opportunity — it may reflect genuine white space, structurally lower local
  demand, or a market where others have already tried and failed. Current
  data cannot distinguish between these.

## 7. Planned Direction for Week 2

- Bring in Census income/demographic data to help distinguish genuine
  opportunity from lower local demand
- Source 2010-vintage NTA boundary polygons from NYC Planning's archive for
  proper choropleth mapping
- Begin using the already-loaded `inspections` and `violations` tables for
  health-trend and violation-type analysis
