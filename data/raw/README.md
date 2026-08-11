# Source data

The raw files are not tracked in git — the inspection extract is 158 MB, over GitHub's
100 MB per-file limit. After cloning, download both files into this directory:

| File | Source | Size |
|---|---|---|
| `DOHMH_New_York_City_Restaurant_Inspection_Results_20260811.csv` | [NYC Open Data — DOHMH Restaurant Inspection Results](https://data.cityofnewyork.us/Health/DOHMH-New-York-City-Restaurant-Inspection-Results/43nn-pn8j) | ~158 MB |
| `Borough_Boundaries_20260811.csv` | [NYC Open Data — Borough Boundaries](https://data.cityofnewyork.us/City-Government/Borough-Boundaries/tqmj-j8zm) | ~3 MB |

> The `20260811` suffix is the download date (2026-08-11). If you use a different snapshot,
> update the `INSPECTION_FILE` and `BOROUGH_FILE` paths in
> `notebooks/01_data_quality_check.ipynb` to match.

## Reference file (needed by notebook 03)

`nta_population_2010.csv` maps NTA codes to neighbourhood names and resident population.
It is small enough to fetch directly:

```bash
curl -o data/raw/nta_population_2010.csv "https://data.cityofnewyork.us/resource/swpk-hqdp.csv?\$limit=5000"
```

Source: [NYC Open Data — New York City Population By Neighborhood Tabulation Areas](https://data.cityofnewyork.us/City-Government/New-York-City-Population-By-Neighborhood-Tabulatio/swpk-hqdp)
(dataset `swpk-hqdp`, 390 rows covering 195 NTAs for census years 2000 and 2010).

### Why the 2010 vintage

NYC has two incompatible generations of Neighborhood Tabulation Area geography:

| Vintage | Code format | Used by |
|---|---|---|
| **2010 NTAs** | `MN17`, `QN22` | the DOHMH inspection data, and therefore this project |
| 2020 NTAs | `MN0101`, `BK0802` | current NYC Open Data boundary files |

The two do not join. Note that **2010 NTA polygons are no longer published** on NYC Open
Data — only names and population are available from open sources, which is why notebook 03
uses a bubble map rather than a neighbourhood choropleth.
