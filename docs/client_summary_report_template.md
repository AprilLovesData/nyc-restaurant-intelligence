# Client Summary Report — Standard Template

A Gateway consultant fills this in for one client engagement. It is deliberately
short: a client will read two pages and skim four, so the analysis behind it stays in
the platform and only the decision-relevant parts come out.

**How to use it.** Copy everything under the line, replace the bracketed fields, and
delete any section that does not apply. Every figure comes from the platform, so each
one should be reproducible by opening the dashboard and setting the same filters.
Section 6 is not optional.

**A worked example follows the template**, using a real result, so the intended level
of specificity is visible rather than described.

---
---

# Restaurant Market Assessment
## [Client name] · [Concept or site] · [Date]

Prepared by [consultant] · Gateway Solutions
Data: NYC Health Department inspection records, [snapshot date] · US Census ACS 2018–2022

---

### 1. The question

[One or two sentences, in the client's own framing. "Where in New York should we open
our second location?" or "We have a site on Roosevelt Avenue — what should go in it?"]

### 2. Recommendation

[Two or three sentences. Lead with the answer, not the method.]

**Shortlist**

| Rank | Neighbourhood | Borough | Why it ranks here |
|---|---|---|---|
| 1 | [name] | [borough] | [the one fact that puts it top] |
| 2 | [name] | [borough] | [ditto] |
| 3 | [name] | [borough] | [ditto] |

### 3. What the market looks like

[Three or four sentences on the current landscape for this cuisine or area. Where the
concept already clusters, how much of the city it covers, whether it is growing or
established. Include one chart.]

### 4. The competitive picture

[For each shortlisted neighbourhood: how many direct competitors, how many residents
per competitor, and how that compares with the citywide rate. The shortfall figure —
"X restaurants below what this population would support" — is usually the most
persuasive single number.]

| Neighbourhood | Direct competitors | Residents per competitor | vs city average |
|---|---|---|---|
| [name] | [n] | [n] | [n]x |

### 5. What we would check next

[Three to five items that this analysis cannot answer and that should be settled before
committing. Rent and availability, footfall, who actually lives there, why nobody has
served this market yet, whether anyone has tried and closed.]

### 6. What this analysis does not tell you

*Keep this section. It is what makes the rest defensible.*

- This is a **shortlist for site visits**, not a decision. A gap in the data means
  nobody currently serves that market; it can equally mean the market does not want
  it, cannot afford it, or that operators have already tried and closed.
- Restaurant counts come from **health inspection records**, so a business the city
  has never inspected does not appear.
- Population figures are from the **2010 Census**; income is the **2018–2022 ACS**.
- **Business districts distort per-resident figures.** Midtown carries 788 restaurants
  per 10,000 residents because it feeds commuters, not its few residents.
- Cuisine is **one label per restaurant**, assigned by the health department, so a
  restaurant serving two cuisines appears under one.
- Data is a **fixed snapshot** dated above, not a live feed.

### Appendix — how the ranking was produced

Neighbourhoods were scored on three components, each converted to a percentile rank so
that dollars, headcounts and ratios could be combined: **unmet demand** (residents per
existing restaurant of this cuisine), **spending power** (median household income), and
**dining culture** (restaurants per resident overall). Weights for this engagement were
[X / Y / Z]%. Full method: `docs/scoring_methodology.md`.

---
---

# Worked example

The same template, completed. Figures are real and reproducible in the dashboard by
selecting Korean with the default weights.

---

# Restaurant Market Assessment
## Han Group · Korean restaurant, second location · 4 September 2026

Prepared by Yiyou Qian · Gateway Solutions
Data: NYC Health Department inspection records, 11 August 2026 · US Census ACS 2018–2022

---

### 1. The question

The client operates one Korean restaurant in Midtown and wants a second location in a
residential neighbourhood rather than another business district. Where should they look?

### 2. Recommendation

**Start with the Upper West Side.** It has 132,378 residents, a median household income
of $140,206, 413 restaurants — and no Korean restaurant at all. That combination does
not occur anywhere else in Manhattan. Lincoln Square and Yorkville are the natural
second and third visits: both are adjacent, similarly affluent, and similarly unserved.

**Shortlist**

| Rank | Neighbourhood | Borough | Why it ranks here |
|---|---|---|---|
| 1 | Upper West Side | Manhattan | 132,378 residents, zero Korean restaurants, $140,206 median income |
| 2 | Lincoln Square | Manhattan | 61,489 residents, adjacent to the top-ranked area, comparable income |
| 3 | Yorkville | Manhattan | 77,942 residents, affluent, no established Korean presence |

### 3. What the market looks like

Korean is an established format in New York — 427 restaurants citywide — but a highly
concentrated one. Two neighbourhoods hold 43% of them: Midtown (93) and Murray Hill in
Queens (90), the city's two Koreatowns. Outside those clusters the cuisine thins out
sharply, which is what creates the opening: large parts of Manhattan's residential west
side have no Korean option at all.

This is a cuisine that clusters rather than spreads. That is a real pattern and worth
weighing — it may reflect supply chain, staffing, or customer expectations of a Korean
dining district rather than an isolated restaurant.

### 4. The competitive picture

| Neighbourhood | Direct competitors | Residents per competitor | vs city average |
|---|---|---|---|
| Upper West Side | 0 | 132,378 | no competitors at all |
| Lincoln Square | 0 | 61,489 | no competitors at all |
| Yorkville | 0 | 77,942 | no competitors at all |

For context, Midtown — where the client already trades — holds 93 Korean restaurants
against 28,630 residents.

**A check worth stating.** Zero Korean restaurants could mean the area does not eat
Asian food, which would be a reason to stop. It does not: the Upper West Side has 58
Asian restaurants (22 Chinese, 18 Japanese, 6 Thai, 6 Asian/Asian Fusion, 3 Southeast
Asian). The absence is specific to Korean.

### 5. What we would check next

1. **Rent and availability.** The three shortlisted neighbourhoods are among the most
   expensive in the city. This analysis models opportunity and ignores cost entirely.
2. **Why nobody is there.** Three adjacent affluent neighbourhoods with zero Korean
   restaurants is either an opening or a signal. Worth asking operators in Midtown
   whether they have considered the west side and decided against it.
3. **Whether anyone has tried.** The data covers a rolling three-year window, so a
   Korean restaurant that opened and closed in 2021 would not appear.
4. **Staffing and supply.** Both existing clusters are dense for a reason; an isolated
   location may face costs the clusters do not.
5. **Who actually lives there.** The model uses population and income. Age and
   household composition shape cuisine demand more than income alone, and are not yet
   in it.

### 6. What this analysis does not tell you

- This is a **shortlist for site visits**, not a decision. A gap means nobody currently
  serves that market; it can equally mean the market does not want it, cannot afford
  it, or that operators have already tried and closed.
- Restaurant counts come from **health inspection records**, so a business the city has
  never inspected does not appear.
- Population is the **2010 Census**; income is the **2018–2022 ACS**.
- **Business districts distort per-resident figures.** Midtown carries 788 restaurants
  per 10,000 residents because it feeds commuters.
- Cuisine is **one label per restaurant**, assigned by the health department.
- Data is a **fixed snapshot** dated 11 August 2026, not a live feed.

### Appendix — how the ranking was produced

Neighbourhoods were scored on three components, each converted to a percentile rank:
**unmet demand** (residents per existing Korean restaurant), **spending power** (median
household income), and **dining culture** (restaurants per resident overall). Weights
for this engagement were the defaults — 50 / 30 / 20%. The Upper West Side scored 92
out of 100. Full method: `docs/scoring_methodology.md`.
