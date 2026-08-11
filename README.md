# NYC Restaurant Intelligence Platform — Market Overview

Restaurant market analysis for New York City, built on NYC DOHMH health inspection data.
This module covers data quality auditing, cleaning, and baseline analysis of market size,
cuisine landscape and borough composition.

## Project structure

```
gateway-restaurant-project/
├── data/
│   ├── raw/            # Source data (git-ignored, see data/raw/README.md)
│   ├── cleaned/        # Analysis-ready tables
│   └── processed/      # Aggregated data for modelling and visualisation
├── notebooks/
│   ├── 01_data_quality_check.ipynb   # Quality audit + cleaning
│   └── 02_market_overview.ipynb      # Borough x cuisine market landscape
├── reports/
│   ├── data_quality_report.md        # Auto-generated issue list
│   ├── data_dictionary.md            # Field-level documentation
│   ├── cleaning_log.csv              # Step-by-step record of transformations
│   └── figures/                      # Chart output
├── src/                # Reusable helpers, extracted once logic stabilises
├── requirements.txt
└── .gitignore
```

## Source data

| Metric | Value |
|---|---|
| Inspection records | 294,976 rows x 27 columns |
| Unique restaurants (CAMIS) | 31,222 |
| Unique inspections | 93,106 |
| Date range | 2007-08-10 to 2026-08-08 |
| Borough boundaries | 5 boroughs, WKT MULTIPOLYGON |

**Critical premise: one row is not one restaurant.** Each row is a single violation cited
during one inspection, so aggregating the raw table double-counts restaurants that were
cited more often. Measured impact: the mean score computed on the raw table is **25.62**,
versus **17.87** once de-duplicated to inspection grain — a **43% overstatement**, because
restaurants with worse hygiene are cited for more violations and therefore occupy more
rows. This is why the cleaned data is split by grain.

## Cleaned tables (`data/cleaned/`)

| Table | Rows | One row is | Use it for |
|---|---|---|---|
| `restaurants.csv` | 31,222 | a restaurant | maps, cuisine mix, borough density |
| `inspections.csv` | 93,106 | an inspection | score trends, grade distribution |
| `violations.csv` | 288,486 | a cited violation | most common violation ranking |
| `borough_boundaries.csv` | 5 | a borough | map base layer |

**Usage rules**

1. Counting restaurants or cuisine share — use `restaurants.csv`
2. Averaging scores or plotting trends — use `inspections.csv`
3. Grade distributions — filter `is_gradeable == True` first, or the denominator absorbs
   inspection types that are never graded

## Key findings (Notebook 02)

1. **Concentrated in Manhattan**: 40% of restaurants, at 73.5 per 10,000 residents —
   4.1x the Bronx (17.9)
2. **Cuisine follows a long tail**: 91 cuisines, top 15 cover 65%, 42 have fewer than 50 locations
3. **Share hides character, concentration reveals it**: American leads every borough but its
   location quotient never leaves 0.73–1.30, marking it as a catch-all label. The cuisines
   with real geographic identity are Caribbean (Brooklyn 1.82 vs Staten Island 0.11, a 16x
   spread) and Latin American
4. **The Bronx has the least complete supply structure**: 6 of the 9 "established citywide
   but scarce locally" combinations

> A low location quotient is not automatically an opportunity — it may equally reflect
> different local demand, or operators who tried and closed. Separating those causes needs
> census demographics and opening/closing histories. See Notebook 02, section 6.

## Getting started

```bash
pip install -r requirements.txt
jupyter notebook notebooks/01_data_quality_check.ipynb
```

Notebook 01 must run first — it generates the cleaned tables that Notebook 02 consumes.

## Progress

- [x] Project structure
- [x] Data quality audit — 12 issues documented in [reports/data_quality_report.md](reports/data_quality_report.md)
- [x] Cleaning — 3 analysis tables, 12 validation checks passing, fields documented in [reports/data_dictionary.md](reports/data_dictionary.md)
- [x] Market Overview — borough x cuisine landscape, [notebooks/02_market_overview.ipynb](notebooks/02_market_overview.ipynb)
- [ ] Mapping and NTA-level drill-down
- [ ] Census demographics join, to separate genuine gaps from differing demand

## Data source

[NYC Open Data](https://opendata.cityofnewyork.us/) — DOHMH Restaurant Inspection Results
and Borough Boundaries
