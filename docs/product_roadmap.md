# Product Roadmap

> Ordering below reflects what the current build makes cheap or expensive. It is a
> starting point for a priority conversation, not a decision already taken.

---

## Where the platform stands

**Built and deployed**

| | |
|---|---|
| Central database | 5 normalised tables in Supabase, 31,222 restaurants / 93,106 inspections / 288,486 violations |
| Market Overview | Borough and cuisine landscape, concentration analysis, neighbourhood drill-down |
| Location Finder | Opportunity scoring with adjustable weights |
| Market Gaps | Per-resident saturation analysis |
| Access control | Sign-in gate on the dashboard |
| Refresh | One command from city data through to the database |
| Documentation | Requirements, data-source inventory, data dictionary, scoring methodology, refresh SOP, this guide |

**Not built**

Inspection Risk Analyzer · Restaurant Comparison Tool · Trend Tracker · Outdoor
Dining Analyzer · per-user data permissions · automated client reports.

---

## 1. Per-user data permissions

**The gap.** The dashboard has a sign-in gate, which controls who opens the page. It
does not control which rows a signed-in user can see. If the platform is ever to
show a restaurant owner *their* data, that distinction is the entire problem.

**Why it matters more than it looks.** Filtering in the interface would be
cosmetic — the database key ships inside the app, so anyone could query the API
directly and retrieve everything. Isolation has to be enforced by the database.

**What it takes**

1. Enable Supabase Auth
2. Add an owner-to-restaurant mapping table
3. Rewrite the row-level security policies to filter on the authenticated user
4. Change the app to authenticate as the user rather than anonymously

**Effort:** moderate. **Frontend-independent** — the same work whether the interface
stays Streamlit or moves to Next.js, which is why it should come before that
decision rather than after.

---

## 2. Demographics beyond income

**The gap.** The Location Opportunity Score uses population, competition and median
income. Cuisine demand varies more with who lives somewhere than with how much they
earn.

**What it takes.** The same ACS release already in use carries household
composition, age distribution and ancestry at tract level; the crosswalk to
neighbourhoods is already built. This is mostly additional variables through an
existing pipeline.

**Effort:** low. **The highest analytical return for the work involved.**

---

## 3. Daytime population

**The gap.** Every per-resident figure understates business districts. Midtown reads
as 788 restaurants per 10,000 residents because it feeds commuters who are not in
the denominator. Any score using resident population is wrong in exactly the places
with the most restaurants.

**What it takes.** A daytime-population or commuter-inflow source, applied as a
correction to the denominator.

**Effort:** low to moderate, depending on source availability. **Fixes a known
distortion rather than adding a feature.**

---

## 4. Commercial rent

**The gap.** The platform models opportunity and ignores cost. A high-scoring
neighbourhood may be unaffordable, and the tool would never say so.

**Effort:** moderate; the constraint is data, not code. No open city dataset covers
commercial rent well.

---

## 5. Inspection Risk Analyzer

**The gap.** Week 3's primary module. All the data is loaded — 288,486 violations
linked to inspections and restaurants — and unused.

**What it takes.** Violation categorisation, repeat-offence detection, a risk score,
and an inspection-readiness checklist.

**Effort:** moderate. **No new data required**, which makes it the cheapest of the
unbuilt modules.

---

## 6. Validating the scores

**The gap.** Neither score has been tested against reality. They are internally
reasonable and externally unverified.

**What it takes.** Take restaurants that opened since 2024 and ask whether the score
ranked their neighbourhoods highly. Not proof — operators may be wrong — but it
would show whether the model tracks real behaviour.

**Effort:** low. **Would do more for the platform's credibility than any new
feature.**

---

## 7. Scheduled refresh

Set aside during Week 2 review as unnecessary. Recorded here because the manual
alternative depends on somebody remembering.

**Effort:** low — the refresh script exists; this is a scheduler around it.

---

## Suggested order

| Priority | Item | Reasoning |
|---|---|---|
| 1 | Demographics beyond income | Cheapest meaningful analytical gain |
| 2 | Validating the scores | Credibility before more features |
| 3 | Per-user permissions | Required before any client-facing multi-user use |
| 4 | Inspection Risk Analyzer | Third module, no new data needed |
| 5 | Daytime population | Fixes a known distortion |
| 6 | Commercial rent | Highest value, hardest data |
| 7 | Scheduled refresh | Convenience |

---

## For whoever picks this up

- Cleaning logic lives in the notebooks, and the refresh script re-executes them
  rather than reimplementing it. Keep it that way — two copies would drift, and the
  report and the dashboard would quietly stop agreeing.
- The notebooks assert their own correctness. A failing assertion is the pipeline
  working, not breaking.
- Every score states its own limits on the page. That was deliberate, and worth
  preserving as the platform grows.
