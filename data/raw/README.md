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
