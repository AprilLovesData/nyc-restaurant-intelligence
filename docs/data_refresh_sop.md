# Data Refresh — Standard Operating Procedure

> **Draft.** Written before the Week 2 review; to be confirmed against whatever
> Scott decides about refresh cadence and ownership.

**Purpose:** bring the platform from a stale snapshot to current city data.
**Who runs it:** anyone with the repository and the Supabase service key.
**How long:** 20–40 minutes, most of it the 158 MB download.
**How often:** the city republishes daily. Monthly is enough for market analysis;
refresh before any client-facing use.

---

## 1. Before you start

| Requirement | Where it comes from |
|---|---|
| The repository, cloned and up to date | `git pull` |
| Python dependencies | `pip install -r requirements.txt` |
| `.streamlit/secrets.toml` with `supabase.url` and `supabase.service_key` | Supabase → Project Settings → API |

**On the service key.** It bypasses every row-level security policy. It belongs in
this local file and nowhere else — never in the deployed app's secrets, never in a
commit. The dashboard uses the read-only anon key and must continue to.

**Check the project is awake.** Supabase pauses free projects after seven days of
inactivity. Open the Supabase dashboard first; if it shows as paused, resume it and
wait for the database to come back before running anything.

---

## 2. Run it

```bash
cd /path/to/gateway-restaurant-project
python3 scripts/refresh_data.py
```

That performs four steps in order:

1. **Download** the current CSV exports from NYC Open Data into `data/raw/`, named
   with today's date
2. **Rebuild** by re-executing notebooks 01 and 04, which clean the data and
   normalise it into the five database tables
3. **Upload** — clears the Supabase tables and reloads them, children before parents
   so foreign keys never point at a missing row
4. **Verify** — compares every table's row count against the local file and stops if
   any disagree

To rehearse without changing anything:

```bash
python3 scripts/refresh_data.py --dry-run
```

Other flags: `--skip-download` reuses the file already on disk, `--skip-upload`
rebuilds locally without touching the database.

---

## 3. After it finishes

1. **Update the snapshot date** in `streamlit_app.py`:
   ```python
   SNAPSHOT_DATE = "11 August 2026"   # change to the new download date
   ```
2. **Commit and push.** Streamlit Cloud redeploys automatically.
   ```bash
   git add -A && git commit -m "Refresh data to <date>" && git push
   ```
3. **Open the dashboard** and confirm the restaurant count has moved and the sidebar
   shows the new date.

---

## 4. When it fails

| What you see | What it means | What to do |
|---|---|---|
| A notebook assertion fails during rebuild | A data-quality check caught something in the new extract | Read the failing assertion; the notebook names what it expected. Do not bypass it — it is the thing standing between bad data and the dashboard |
| `violates foreign key constraint` | A table loaded out of order | Re-run; the script's order is correct, so this usually means a partial previous run. It clears tables first, so re-running is safe |
| Row counts disagree at verification | Some pages failed to upload | Re-run with `--skip-download --skip-rebuild` to retry only the upload |
| Download stalls | Large file over a slow link | Re-run; an existing complete file is kept and skipped |

**The script is safe to re-run.** Every step either skips completed work or replaces
it wholesale.

---

## 5. What this does not do

- **It does not run on a schedule.** Somebody has to run it. Scheduling was discussed
  and set aside as unnecessary for current use.
- **It does not refresh the Census data.** Income and rent come from the ACS
  five-year release, updated annually, and are committed to the repository as a
  static file.
- **It does not preserve history.** Each run replaces the tables. The source itself
  is a rolling three-year window, so records also disappear upstream — the database
  is a current snapshot, not an archive.

---

## 6. Open questions for review

- How often should this run, and who owns it?
- Should refreshes be recorded somewhere, so a chart can be traced to a vintage?
- Is a history table worth adding, given the source's rolling window means anything
  not captured is lost permanently?
