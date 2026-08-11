# Data-Source Inventory

**Project:** NYC Restaurant Intelligence Platform
**Repository:** https://github.com/AprilLovesData/nyc-restaurant-intelligence
**Dashboard:** https://nyc-restaurant-intelligence.streamlit.app
**Data snapshot date:** 2026-08-11

---

## 1. DOHMH New York City Restaurant Inspection Results

| Field | Detail |
|---|---|
| Owner | NYC Department of Health and Mental Hygiene (DOHMH) |
| URL | https://data.cityofnewyork.us/Health/DOHMH-New-York-City-Restaurant-Inspection-Results/43nn-pn8j |
| Dataset ID | `43nn-pn8j` |
| Update frequency | Daily |
| Snapshot | Downloaded 2026-08-11; source last updated 2026-08-10 |
| Size | 158 MB, 294,976 rows × 27 columns |
| Coverage | Inspections from 2007-08-10 to 2026-08-08 |
| Granularity | **One row = one violation cited during one inspection** (not one row per restaurant) |
| Scope note | Covers active establishments and college cafeterias; includes all confirmed/unadjudicated violations within 3 years of the most recent inspection |

**Key fields used:** `CAMIS` (unique restaurant ID), `DBA` (name), `BORO`, `ZIPCODE`,
`CUISINE DESCRIPTION`, `INSPECTION DATE`, `INSPECTION TYPE`, `ACTION`, `SCORE`,
`GRADE`, `VIOLATION CODE`, `VIOLATION DESCRIPTION`, `CRITICAL FLAG`, `Latitude`,
`Longitude`, `NTA`.

**Usage restrictions / data-quality notes:**
1. Not a business registry — only covers establishments DOHMH has inspected;
   cannot be read as "total restaurants in NYC."
2. One row ≠ one restaurant (avg. 9.4 rows/restaurant) — raw row counts
   overstate restaurant totals by roughly 10x.
3. Rolling 3-year window — not suitable for long-term historical trend
   analysis beyond that window.
4. NTA codes use the **2010 vintage** (e.g. `MN17`), incompatible with NYC's
   current 2020 NTA scheme (e.g. `MN0101`).
5. No explicit license stated in metadata; governed by NYC Open Data's
   general terms of use.

**Refresh procedure:** re-export CSV from source URL; re-run
`01_data_quality_check.ipynb` end to end (fully scripted, reproducible).

---

## 2. Borough Boundaries (water areas excluded)

| Field | Detail |
|---|---|
| Owner | NYC Department of City Planning (DCP) |
| URL | https://data.cityofnewyork.us/City-Government/Borough-Boundaries/gthc-hcne |
| Dataset ID | `gthc-hcne` |
| Update frequency | Quarterly |
| Source last updated | 2026-05-26 |
| Size | 3 MB, 5 rows × 5 columns |
| Fields | `BoroCode`, `BoroName`, `Shape_Area`, `Shape_Length`, `the_geom` (WKT MULTIPOLYGON) |

**Usage restrictions / data-quality notes:**
1. Land area only (water excluded) — e.g. Queens = 3,041,419,716 sq ft
   (≈109 sq mi).
2. Geometry field up to 1.37 MB of text per row (Queens) — exceeds most
   browser-based CSV import tools.
3. `Shape_Area`/`Shape_Length` contain thousands separators and load as
   strings, not numeric, until parsed.

---

## 3. NYC Population By Neighborhood Tabulation Areas (added mid-analysis)

| Field | Detail |
|---|---|
| Owner | NYC Department of City Planning |
| URL | https://data.cityofnewyork.us/City-Government/New-York-City-Population-By-Neighborhood-Tabulatio/swpk-hqdp |
| Dataset ID | `swpk-hqdp` |
| Size | 23 KB, 390 rows (195 NTAs × 2000/2010 census years) |
| Fields | `borough`, `year`, `fips_county_code`, `nta_code`, `nta_name`, `population` |
| Why added | The inspection data only carries NTA codes, not names; this
  dataset supplies both readable names and population, enabling per-capita
  neighborhood analysis. |
| Match rate | 193/193 NTA codes matched, 0 unmatched |

**Usage restrictions / data-quality notes:**
1. Population figures are from the **2010 Census** — not directly comparable
   to the 2020 Census figures used in the borough-level analysis, since no
   2020 population release exists for 2010-vintage NTAs.
2. The 2010 NTA boundary polygons have been removed from NYC Open Data;
   only the incompatible 2020 version remains on the portal.

---

## 4. Planned for Future Weeks (not yet used)

| Source | Planned use | Target week |
|---|---|---|
| U.S. Census American Community Survey | Income/demographic variables for Location Opportunity Score | Week 2 |
| MTA Open Data | Transit accessibility indicators | Week 2 |
| NYC Sidewalk Café Data | Outdoor dining analysis | Week 3 (if time permits) |
| NOAA Weather Data | Seasonal outdoor dining patterns | Week 3 (if time permits) |
| 2010 NTA boundary polygons (archival) | Proper choropleth maps with real neighborhood shapes | Enhancement |
