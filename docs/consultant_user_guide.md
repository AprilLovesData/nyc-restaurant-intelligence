# Consultant User Guide

**The platform:** https://nyc-restaurant-intelligence.streamlit.app
**Sign-in:** required. Credentials are issued per person.

---

## What this tool is for

Answering a restaurant client's location and concept questions from public data,
with the reasoning visible enough to put in front of them.

It covers **31,222 restaurants** across all five boroughs and 193 neighbourhoods,
built from the city's health inspection records.

**What it is not.** It is not a business directory, a rent database, or a footfall
model. It narrows a city down to a shortlist worth visiting. It does not decide
anything.

---

## The three modules, and which question each answers

| Module | The client asks | You open |
|---|---|---|
| **Market Overview** | "What does the New York restaurant market look like?" | Tab 1 |
| **Location Finder** | "I want to open a Korean restaurant. Where?" | Tab 2 |
| **Market Gaps** | "I have a site in Astoria. What should I put in it?" | Tab 3 |

Modules 2 and 3 are deliberately opposite entry points. Most client conversations
start from one or the other.

---

## Module 1 — Market Overview

Use it to frame a conversation before any specific question arrives.

**Reading the numbers**

- **Typical hygiene score** — lower is better. Inspectors add points for problems;
  13 or below earns an A from the city. Say this out loud to clients, because
  everyone assumes higher is better.
- **The concentration heatmap** compares each borough against the city as a whole
  rather than counting restaurants. A borough can lead on raw pizzeria count purely
  by being large; this controls for that.

**Worth knowing before a client does.** American is a catch-all in the city's
taxonomy — diners, bars and burger places all land there. It leads every borough and
means very little. Point at Caribbean instead: 1.82 in Brooklyn against 0.11 on
Staten Island, a sixteen-fold spread, which is a real cultural pattern.

---

## Module 2 — Location Finder

**When to use it:** the client has a concept and no site.

1. Select the cuisine
2. Narrow the boroughs if the client has already ruled some out
3. Adjust the three weights to match what the client actually cares about

**Use the sliders in front of the client.** A client who believes spending power
matters more than anything can watch the ranking change when they say so. That
conversation is more useful than the default ranking, and it stops the number from
looking like an oracle.

**Worked example.** Korean returns the Upper West Side first: 132,378 residents,
$140,206 median household income, zero Korean restaurants. Before presenting that,
it was checked against the records — the neighbourhood holds 413 restaurants, 58 of
them Asian (22 Chinese, 18 Japanese, 6 Thai), so the absence is specific to Korean
rather than to Asian food. Korean restaurants citywide cluster in Midtown and Murray
Hill, Queens, the two Koreatowns.

**That is a defensible gap and not a recommendation.** It says nobody is currently
serving Korean food to a large, wealthy, restaurant-dense neighbourhood. It does not
say why, and "why" is the next conversation.

---

## Module 3 — Market Gaps

**When to use it:** the client has a site, or a borough they know.

1. Choose the borough, then optionally a specific neighbourhood
2. Leave the citywide threshold at 300 unless you have reason to move it — it keeps
   the list to formats somebody has already made work in New York

**Reading saturation.** 1.00 means this area carries its fair share of that cuisine
for its population. 0.37 means it has just over a third of the competitors per
resident that the city average would give it. The **shortfall** column turns that
into a count, which is usually the more persuasive way to say it.

**Worked example.** Manhattan's widest gap is Caribbean: 53 restaurants against 145
at the citywide rate for its population.

**Why this can disagree with the heatmap in Module 1.** Module 1 measures each
cuisine's share of an area's restaurants; Module 3 measures competitors per
resident. Manhattan has far more restaurants per resident than anywhere else, so a
cuisine can look severely under-represented by share while looking less so per head.
Both are correct. Use share to describe an area's character, and per-resident when
the client is asking about competition.

---

## What to say when a client asks "so should I open there?"

The honest answer, and the one the tool is built to support:

> A gap in this data means nobody is currently serving that market. It can equally
> mean the market does not want it, cannot afford it, or that operators have already
> tried and closed. This narrows the city to a handful of places worth visiting. It
> does not replace the visit.

Every module states this on the page, deliberately. It is easier to defend an
analysis that names its own limits than one a client finds them in.

---

## Limits to disclose in any client deliverable

- Data is a **fixed snapshot**, dated in the sidebar. The city updates daily; the
  dashboard does not.
- **Restaurant counts** come from health inspections, so a business never inspected
  does not appear.
- **Population is the 2010 Census**; income is the 2018–2022 ACS. They describe the
  same places eight years apart.
- **Business districts distort per-resident figures.** Midtown carries 788 restaurants
  per 10,000 residents because it feeds commuters, not its few residents. Treat any
  central business district figure with care.
- **Cuisine is one label per restaurant**, assigned by the health department.

---

## Producing a client deliverable

A template for the written output is in
[client_summary_report_template.md](client_summary_report_template.md), with a fully
worked example. Any figure can be exported as an image using the camera icon that
appears in its top-right corner on hover.

## Still to confirm

| Question | Current position |
|---|---|
| Individual sign-ins per consultant? | Everyone shares one set of credentials at present. Individual accounts are straightforward to add, and would be needed before anyone outside Gateway is given access. |
| Should clients get access to the dashboard itself? | Not yet. The sign-in gate controls who opens the page but not which rows they see, so a client would see the whole city — including whatever another client is looking at. Per-user data permissions are the first item on the roadmap. |
