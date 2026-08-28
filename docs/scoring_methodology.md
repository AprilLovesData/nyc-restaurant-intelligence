# Scoring Methodology

**Module:** Location Finder (Location Opportunity Analyzer)
**Status:** v1, Week 2
**Where it runs:** the Location Finder tab of the deployed dashboard

---

## What the score answers

*Given a cuisine, which neighbourhoods look most favourable for opening one?*

It answers that with arithmetic on population, competition and income. It does not
answer whether a restaurant will succeed there, and section 5 below is explicit
about the difference.

## 1. Unit of analysis

One row per **Neighborhood Tabulation Area (NTA)** — the city's 2010-vintage
official neighbourhood units, 193 of which contain restaurants. Excluded from
scoring:

- Park and cemetery tracts (a token resident population makes every per-capita
  figure meaningless)
- Neighbourhoods with no recorded population

## 2. Components

Three components, each computed per neighbourhood for the selected cuisine.

| Component | Measured as | Rationale |
|---|---|---|
| **Unmet demand** | residents ÷ (existing restaurants of that cuisine + 1) | The audience a new restaurant would face. The `+1` avoids dividing by zero and gives the figure a literal reading: the demand facing one new entrant. |
| **Spending power** | median household income (ACS 2018–2022) | Whether that audience can support restaurant prices. |
| **Dining culture** | total restaurants per 10,000 residents | Whether the neighbourhood eats out at all. A dense restaurant scene indicates established demand for eating out, independent of cuisine. |

### Why percentile ranks, not raw values

The three components are measured in different units — dollars, headcounts, and a
ratio. Averaging them directly would let income, being numerically the largest,
dominate the result regardless of the weights.

Each component is therefore converted to a **percentile rank from 0 to 100** across
all candidate neighbourhoods before weighting. A score of 80 on spending power means
"richer than 80% of neighbourhoods", not any particular dollar amount.

## 3. Weights

$$\text{Score} = \frac{\sum_i w_i \cdot \text{rank}_i}{\sum_i w_i}$$

Defaults: **50% unmet demand, 30% spending power, 20% dining culture**.

The weights are exposed as sliders in the interface. This is deliberate: there is no
objectively correct weighting, and a score whose assumptions cannot be inspected or
changed invites more trust than it deserves. A user who believes spending power
matters most should be able to say so and watch the ranking respond.

## 4. Competitive saturation

Shown alongside the ranking. For each borough:

$$\text{Expected} = (\text{restaurants in borough}) \times \frac{\text{citywide restaurants of this cuisine}}{\text{all citywide restaurants}}$$

The gap is actual minus expected. A negative gap means the borough holds fewer of
that cuisine than its overall size would imply. This is the same location-quotient
logic used in the Market Overview, expressed as counts rather than a ratio because
counts are easier to argue with.

## 5. What the score deliberately excludes

Not in the model, and material to any real decision:

- **Rent and commercial availability** — a high-scoring neighbourhood may have no
  affordable vacant space
- **Footfall, transit access, parking**
- **Tourism and commuter flows** — the resident population undercounts the addressable
  market in business districts severely; Midtown is the extreme case
- **Who actually lives there** — age, household composition and ethnicity all shape
  cuisine demand, and none are in the model yet
- **Failure history** — a neighbourhood with no restaurants of a cuisine may be one
  where several have already closed

## 6. Known limitations

**Income is an approximation.** The ACS publishes median household income at census
tract level. Neighbourhood figures here are a population-weighted mean of tract
medians, which is not the same as a true neighbourhood median — a median cannot be
averaged. The error is small for homogeneous neighbourhoods and larger for mixed
ones.

**Two population vintages are in play.** Restaurant density uses 2010 Census
population, the only release published for these neighbourhood boundaries. Income
comes from the 2018–2022 ACS. They describe the same places roughly eight years
apart.

**291 of 2,327 census tracts did not match** the 2010 tract-to-NTA crosswalk, mostly
tracts created or renumbered after 2010. Their income is absent from the aggregate.

**Cuisine labels come from health department records**, one per restaurant, and
carry the granularity of that source: `American` is a catch-all covering diners and
bars, and a restaurant serving two cuisines appears under one.

**Absence in the data is not absence in reality.** A neighbourhood showing zero
restaurants of a cuisine may have one that has never been inspected, or one
classified differently.

## 7. Validation performed

The top result for Korean — Upper West Side, 132,378 residents, zero Korean
restaurants, $140,206 median income — was checked against the underlying records
rather than accepted from the model:

- The neighbourhood holds **413 restaurants**, so it is not a thin market
- **58 are Asian** (22 Chinese, 18 Japanese, 6 Thai, 6 Asian/Asian Fusion,
  3 Southeast Asian), so the absence is specific to Korean rather than to Asian
  cuisine generally
- Korean restaurants citywide concentrate in Midtown (93) and Murray Hill, Queens
  (90) — the two established Koreatowns — which is consistent with a cuisine that
  clusters rather than spreads

This is a plausible gap. It remains a gap in the data, not a validated opportunity.

## 8. Data sources

| Source | Used for | Vintage |
|---|---|---|
| NYC DOHMH Restaurant Inspection Results (`43nn-pn8j`) | Restaurant locations and cuisines | Snapshot 11 Aug 2026 |
| NYC Population by NTA (`swpk-hqdp`) | Neighbourhood names and population | 2010 Census |
| US Census ACS 5-Year (`B19013_001E`, `B25064_001E`) | Median household income and gross rent | 2018–2022 |
| 2010 Census Tract to NTA Equivalency (`8ius-dhrr`) | Tract → neighbourhood crosswalk | 2010 |

## 9. Next iteration

1. Add household composition and age from the same ACS release — cuisine demand
   varies more with these than with income alone
2. Weight business districts by daytime population rather than residents
3. Bring in commercial rent, so the score reflects cost as well as opportunity
4. Test against restaurants that have actually opened since 2024: does the score
   rank the neighbourhoods operators are already choosing?
