# Fix Chicago Housing — project spec and handoff

A free, browser-based game on a real 3D model of Chicago's ~481,000 buildings. Players change zoning and flip on real housing policies, then simulate 15 years to see whether they close the region's housing shortage and what happens to rent.

**Goals, in order:** teach people the real causes of the housing crisis, let them try to fix it, and make it fun. It's a for-fun project, not a policy tool. It must never feel bloated.

**Owner:** Kyle (urban planner / housing finance background; doesn't code; directs Claude to build).

**Live version:** a private claude.ai artifact at https://claude.ai/artifact/XHPMwjqFSW9C4Rbmg8Xe81. Republishing needs the claude.ai Artifact tool. Otherwise host the folder anywhere static: it's plain HTML plus data files, with no build step.

## Decisions already made (don't relitigate)

- **Name:** "Fix Chicago Housing."
- **Voice:** witty, a little edgy, mild language at most. Myth cards and public comments carry the humor; numbers stay straight and sourced.
- **Devices:** phone and desktop equally.
- **Look:** "City Hall" only (Kyle picked it over Ballpark Scoreboard and Lakefront at Night). It's a civic look inspired by chicago.gov: nav blue #2b5da0, flag blue #41b6e6, red six-point stars #e4002b, blue score band, Big Shoulders Display + Public Sans + Source Serif 4. Guardrails: no city seal, logo or "official" banner, and the line "A fan-made game. Not affiliated with the City of Chicago." stays visible. The old "Playful" look and Style button are gone (`setLook("model")` is still called once to set legend colors). The three prototypes live in a claude.ai design canvas: https://claude.ai/artifact/HnniCGdUrGZfhKYKB7qgAR (artboard "Main" = A).
- **Citations:** every number in the game is either linked to a source or listed under "Game assumptions (not measured)" in The math tab. Keep it that way: no new number without a link or an assumption label.
- **Accounts:** none. Saving is browser storage plus share links and plan codes that encode the whole plan.
- **Not included, on purpose:**
  - A transfer tax / "mansion tax" (Kyle: shown to reduce development, as in LA).
  - Per-lot developer pro formas. They would look precise and be wrong lot by lot. The single illustrative interest-rate card on the results screen replaces them.
  - Leaderboards.
- **Anti-bloat:** the main screen stays map + goal meter + simulate button. Everything else is progressive.
  - Tools unlock by milestones: 10k homes → neighborhoods + Metra; 30k → policies; 60k → corridors + office conversions. An "unlock all" option exists.
  - Myth cards and public comments appear only in response to actions.

## Files

| Path | What |
|---|---|
| `index.html` | The whole game: HTML, CSS and JS, one file. Loads deck.gl 9.3.11 from unpkg. |
| `meta.json` | 77 community areas, with name, center, homes, and demand factor. Also L stations (124), Metra stations (74), corridor street paths (38 streets), community-area outlines, the lake polygon, and the city outline. |
| `b/<area>.wasm` | One binary file per community area holding its buildings. It's named .wasm only because the artifact host serves just a few binary types; it isn't WebAssembly. |
| `tools/prep.py` | Rebuilds `b/` and `meta.json` from the city's raw building footprints and street centerlines. It expects the raw downloads in `dl/` and outputs `.bin` files; rename them to `.wasm`. |
| `b/streets.wasm` + `meta.json` `streetLabels` | Street centerlines (expressway / arterial / local) and ~200 label points, built by `tools/prep_streets.py`. Format is documented at the top of that script. |
| `tools/prep_zoning.py` | **Run this first on your Mac** (it needs internet). It downloads Chicago's zoning map and flags buildings that would be illegal to build today. |
| `tools/stations.csv`, `tools/metra.csv` | Station coordinates. |

### Building binary format (little-endian), per area

1. **Header (24 bytes):** `uint32 N` (buildings), `uint32 V` (vertices), `float64 lon0`, `float64 lat0` (the origin).
2. **Vertices:** `int16[2V]`, in 0.5 m units east/north of the origin, rendered with deck.gl METER_OFFSETS.
3. **Per-building arrays:**
   - `uint8 nverts[N]`, `uint8 stories[N]` (0 = unknown, treated as 1), `uint8 flags[N]`.
   - One pad byte if `3N` is odd.
   - `uint16 units[N]`, then `uint16 footprint_sqft_div2[N]`.

**Flag bits:**

| Value | Meaning |
|---|---|
| 1–2 (bits 0–1) | L station distance: 2 = within ¼ mi, 1 = within ½ mi |
| 4 | Within ½ mi of Metra |
| 8 | Built 2000 or later (never redeveloped) |
| 16 | On a commercial corridor (centroid within 150 ft of a corridor centerline) |
| 32 | Older downtown tower: Loop or Near North/West/South, no homes, 8+ stories, built before 1990 |
| 64 | Illegal to build today; set by `prep_zoning.py` |
| 128 | Shop lot that can become housing: no homes, has a street address, no landmark name or monument tag, and on a corridor or within ¼ mi of the L. Non-residential buildings without it never redevelop (keeps Grant Park, museums and field houses out). |

**Building order is the random seed.** Never reorder buildings: which lots redevelop comes from a hash of (index, area). Rebuilding from the same raw data with `prep.py` keeps the order.

## Model (all in `index.html`; constants at the top of the script)

- **Zoning levels** (stories / homes on a standard 25×125 = 3,125 sq ft lot), tied to Chicago's minimum-lot-area rules (§17-2-0303):

  | Level | Stories | Homes per std lot (`k`) | Based on |
  |---|---|---|---|
  | 3-flat | 3 | 3 | RT-4: 1 home per 1,000 sq ft of lot |
  | 6-flat | 4 | 6 | RM-5: 1 per 400 sq ft (capped to a realistic 6) |
  | Mid-rise | 6 | 10 | RM-6: 1 per 300 sq ft |
  | High-rise | 12 | 20 | RM-6.5: 1 per 300 sq ft, or studios at 1 per 135 (assumed mix) |

  Homes on a lot = `floor(k × lot / 3,125)`; net new = that minus existing homes. (These replaced the earlier 3/6/12/28 guesses and lowered totals, e.g. mid-rise near the L went from ~116k to ~93k.)
- **Which buildings can be rebuilt:**
  - Applies to buildings in a rezoned area: by neighborhood, near the L or Metra (½ mi), on a corridor, or every lot with 1–4 homes under the BUILD Act.
  - The building must be a home, or a small storefront under 12,000 sq ft of footprint.
  - It must be built before 2000, shorter than the new limit, and on a lot under about 40k sq ft (lot ≈ 2× footprint).
  - The new building must add at least 1 home net.
- **Chance it rebuilds within 15 years:** 6% × the neighborhood demand factor (0.3–2.5×, from each area's share of buildings built since 1990), capped at 60%. Policy multipliers stack on top:
  - Prerogative reform: +15%.
  - Faster permits: +10% chance, and homes arrive about 20% sooner.
  - Single stair: +25% for 6-flat and mid-rise projects on lots under 7,500 sq ft.
  - Affordable requirement (ARO) dial: ×1.30 / 1.0 / 0.70 on projects of 10+ homes (gross, not net), with 10 / 20 / 30% affordable.
  - No parking minimums (`park`, or `mpls`): +10% on lots NOT near transit (assumption; Chicago already dropped mandates near transit).
  - Small-lot homes (`small`): +20% for 3-flat and 6-flat projects on lots of 5,000+ sq ft (assumption).
- **"Worked in other cities" zoning rules** (in `tierAt`):
  - Minneapolis (`mpls`): every 1–4-home lot gets at least 3-flat; corridor lots (flag 16) at least mid-rise; plus the parking boost citywide.
  - Cambridge (`camb`): every 1–4-home lot gets at least 6-flat.
  - Texas SB 840 (`comm`): corridor lots get at least 6-flat.
  - BUILD Act (`build`): every 1–4-home lot gets at least 3-flat.
- **Policies that add homes without changing the map:**
  - Office conversions: 141.9M sq ft × (5 / 15 / 27%) ÷ 1,026 sq ft per home.
  - Coach houses / ADUs: eligible lots × 0.75% × (2 − 34/50).
  - Short-term rentals: 11,236 listings × 80.2% entire homes × (10% or 50%).
  - City-owned lots: 7,100 lots × 2 homes × 50%.
  - Empty-homes tax (`vac`, Vancouver): 60,223 "other vacant" homes (ACS 2024 B25004) × 10% returned (assumption).
  - Triple the social housing fund (`social`, Montgomery County): +$270M at 6,000 homes per $100M over 20 years, counted for 15 years ≈ 12,150 homes, 30% affordable.
- **Baseline ("no change"):**
  - Starting shortage: the selected estimate (Up for Growth 165,687 by default; Zillow 115,282; NLIHC 224,445).
  - The shortage grows +8,760/yr while Chicago keeps permitting ~4,900/yr. The goal is today's shortage + 15 × 8,760.
  - Rent grows 3.4%/yr; wages grow 3.2%/yr.
- **Rent effect:** each 1% added to the housing stock (1,282,248 homes, ACS 2024) → 0.19% lower rent (Mense 2025). Applied to the $1,440 median gross rent, and to a $1,745 one-bedroom for the people.
- **Jobs and taxes (NAHB, 2015 dollars):** 1.61 jobs per home in its build year, 0.44 lasting jobs per home, $5,030 per home per year in local taxes and fees.

## What's built now

- **Build tab:**
  - L-station levels.
  - Metra-station levels.
  - Neighborhood picker (tap the map) with each neighborhood's demand factor.
  - Corridor levels.
  - Office-conversion levels.
  - A hidden "illegal to build today" toggle that appears once bit 64 data exists.
  - Start over / unlock all.
- **Policies tab, two groups:**
  - *On the table in Chicago:* BUILD Act, affordable requirement (ARO) dial, Cut the Tape, short-term rental limits (2 levels), single stair, ADUs everywhere, city lots, prerogative reform. Parking reform near transit and Green Social Housing are listed as already law.
  - *Worked in other cities · not on the table here* (`#policiesElse`, status class `.status.else`): Minneapolis 2040 plan, Cambridge 4-story by right, Houston small lots, no parking minimums anywhere (Buffalo/Austin), Texas SB 840 housing on commercial land, Vancouver empty-homes tax, Montgomery County social housing fund.
  - Each card shows real status, a live "+homes" (marginal, computed by `marginal()`), what happened elsewhere, how the game models it, and linked sources.
  - Note for the copy pass: Illinois SB 2111 (People Over Parking Act, Dec 2025) exists and limits parking mandates near transit statewide; mention it on the parking card if it helps.
- **Missions tab:** 7 missions with medals, plus a selector for which shortage you're solving.
- **Impact tab:**
  - Share of new homes within a 10-minute walk of transit.
  - Affordable homes.
  - Homes torn down.
  - North / Downtown / West / South split.
  - Jobs and taxes.
  - Six people (made-up names, real jobs and wages) showing the share of pay going to a one-bedroom today, in 2041 with no change, and in 2041 with your plan.
- **Simulate next 15 years:**
  - Buildings rise year by year while the camera slowly orbits.
  - A results screen shows shortage and rent charts (no change vs. plan), the six people, and an interest-rate card explaining why zoning alone can't force building.
- **Myth cards (9):** illegal-to-build, luxury towers, filtering, Airbnb, "just build affordable", shrinking city, density, "upzoning doesn't do anything" (Minneapolis, Austin, Auckland), ARO. Each fires once, when relevant; replay them from "The math".
- **Public comments:** witty one-liners when you rezone or flip a policy.
- **Header:** fan-made bar, flag mark, title, and a **Sources** button that opens The math tab. Score band: homes vs goal, red-star grade, segmented bar (z zoning, o offices, a ADUs, s short-term rentals, l city lots, v empty homes, h social housing).
- **Layout (v8):** the sheet is sized from the HUD's real height (`--hudH`, set by a ResizeObserver), so the HUD never hides the Simulate button. On phones the stats row hides while the tool sheet is open (shows when it's collapsed) and the map key collapses to a "Map key" pill.
- **Map layers:** flat layers (lake, land, neighborhoods, station circles, corridors) use `parameters: FLAT` (`depthCompare:"always"`, no depth write) so they don't z-fight at ground level when zoomed in. Station circles are ½ mile (805 m), outlined, and the legend shows "½ mile of a station (≈10-min walk)" whenever L or Metra zoning is on.
- **Policy cards** are collapsed to title, status, +homes and switch; "What happened & sources" expands each one, "Show all details" expands everything, and the three groups are collapsible sections ("Already law" starts closed).
- **Streets (v9):** three PathLayers (local streets appear from zoom ~11.8, darker from 13.2) plus a TextLayer of street names; zoom bands tracked in `onViewStateChange`.
- **Policies sorted (v9):** cards are ranked by homes added with the current map (`GAIN`, from `marginal()`), tagged "#n · Big/Medium/Small"; re-sorted only when the Policies tab opens so cards don't jump while you click.
- **Town hall (v9):** `TOWN` (10 common objections: research + how another place got past it + sources) and `TACTICS` (4 ways to win the room). Listed in the Missions tab; public-comment bubbles have "How to answer this ›" that opens the matching card (`TOWN_FOR`).
- **First-run walkthrough (v9):** three tips (L zoning → Policies → Simulate) after the intro; stored as `fch-tour`.
- **Fact check (Oct 11, 2026):** an independent pass verified ~50 figures and fixed: ARO factor 1.30/0.70 (Terner ~30%), Airbnb entire-home share 80.2% (AirDNA supply page), HUD prerogative finding dated 2023 and withdrawn 2025, $70B affordable math, Houston assessed values and lot sizes, ADU details, rate-card labeling, Vancouver/Cambridge/Minneapolis wording, and missing source links. Persona wages are BLS OEWS May 2025 medians (home aide is SOC 31-1120). Still unverified (sites block automated reads): TRD permit counts, ACS B25004 60,223.
- **Motion (v11):** modals rise in / sink out (`hideModal()`), panes fade, details slide open, grade pops on change. Simulation: one year = `YEAR_MS` (700 ms); buildings rise continuously (elevation transition = one year, linear); neighborhoods update in a 6-frame ripple (`recomputeWave`); camera does one smooth eased 70° orbit with a slight pitch arc (`orbit()`). All motion is off under prefers-reduced-motion.
- **Myths (v11):** each card is myth quote → one-line verdict (`a`) → plain-language explanation (`b`) → sources.
- **Goal explained (v11):** intro shows 165,687 today + 131,400 growth = 297,087; the Missions tab shows the same equation for whichever shortage estimate is selected.
- **v12:** station zones are pre-merged shapes (`meta.json` ringL/ringM/ringLM from `tools/prep_rings.py`) so overlapping circles read as one zone; camera buttons (zoom, spin, 2D/3D, reset) plus a walkthrough step; zoom limited to the city region; basemap presets in `BASES` (island / region / night, default region) with an extended Lake Michigan shape and neighboring-town labels; policies that add nothing explain why (`ZERO`); ARO card explains the tradeoff and that real-world evidence is mixed.
- **v13 (branch `next`):** disclaimer now just "Not affiliated with the City of Chicago."; share links + preview image on fixchicagohousing.com; keyboard camera (WASD/arrows, Q/E, R/F, +/-); new levers: suburban Metra stations (`plan.sub`, 168 stations × game-model per-station homes × 0.3, assumption) and "Get the megaprojects built" (`p.mega`, `MEGA` list of 6 projects, 31,063 planned homes × 0.5, assumption) with purple map pins and a "Big projects in the pipeline" section in The math; plan code `u4` (= u3 + suburban tier; `mega` appended to BIT_KEYS); OpenFreeMap/MapLibre vector basemap under the deck canvas (camera synced in `onAfterRender`), only on our own domain, falling back to the built-in basemap elsewhere; zoning flags merged (96,392 of 481,262 buildings, 20.0%, with lots estimated as max(2× footprint, 3,125 sq ft)) and a first-visit intro hook that shows them red (`introHook`).
- **v14:** intro opens with an Axios Chicago headline clipping; results screen has "Do something about it" (copy-a-note + ward lookup, ILGA members, Abundant Housing Illinois, Housing Action Illinois) and "Add it to the community"; the Save tab is now **Share** with "What other players chose", a plan gallery (newest / most liked / my neighborhood, open-to-remix, likes) and an "I live in" picker; policy cards show "% of players turn this on" once 20+ plans exist. Backend: `worker/index.js` (Workers + one SQLite Durable Object `Community`), config in `wrangler.jsonc` (static assets from the repo root, `.assetsignore` keeps tools/docs private, custom domains fixchicagohousing.com + www). Finished simulations are counted anonymously; posting to the gallery is opt-in; no free text is stored, so nothing needs moderation; rate limit 40 plans per hashed IP per day. Community UI hides itself where there's no /api (claude.ai preview).
- **Expand mode (v15):** desktop "⤢ Expand" button widens the tool panel next to the score card (cards in a grid, Build tab in two columns); "⤡ Collapse" returns to the sidebar; remembered per browser (`fch-wide`).
- **The math tab:** zoning table with code citations, decision rules, baseline, rent effect, shortage estimates, ARO, offices, NAHB, people, an explicit "Game assumptions (not measured)" list, myths, data, and what's not modeled. Every source is a link.
- **Save tab:** autosave, named saves, share link (`#u3...`), plan code, and open a code.
- **Plan code `u3`:** `"u3"` + 39 area chars + tod, metra, corr, office, str, aro (one char each) + 3 base-32 chars of on/off bits in `BIT_KEYS` order (`build, stair, adu, lots, pre, permits, mpls, camb, small, park, vac, social, comm`) + goal. Only `[0-9a-v]`. **Append new on/off policies to the end of `BIT_KEYS`** so old codes still decode. `u2` and `u1` still decode.

## Handoff tasks for the desktop session (in priority order)

0. **Done in the cloud session already:** layout fixes, streets, Grant Park fix, policy sorting, town hall, walkthrough, fact check, visual QA in headless Chromium (desktop + phones).
1. **Illegal-to-build overlay.** Run `python3 tools/prep_zoning.py`. Check that zoning class names parse (look at a few features) and that the flagged share looks sane: Lake View and Logan Square should be high, new downtown low. Then make this the intro hook. When the game first opens, show the red "illegal today" buildings over the old 2- and 3-flat neighborhoods for a few seconds before the player starts.
2. **Real-device check** on an iPhone and a Mac browser (headless screenshots looked right; real GPUs may differ).
3. **Cinematic simulation:**
   - Replace the simple orbit with a camera path that flies over the neighborhoods gaining the most homes, year by year.
   - Add a before/after swipe slider comparing 2026 with 2041.
4. **Animation polish:**
   - Stagger buildings rising within a year, with easing.
   - Add unlock moments, counter tick-ups, and entrances for myth cards and comments.
   - Respect `prefers-reduced-motion`.
5. **Layout QA on a real phone and desktop:** HUD crowding, sheet height, tab overflow, tap targets, and the results card scrolling.
6. **Performance on a mid-range phone:**
   - Consider hiding buildings under ~800 sq ft at low zoom.
   - Parse the binaries in a Web Worker.
   - Prioritize loading what's in view.
7. **Copy pass** in the witty voice. Keep every number and source intact.
8. **Verify the two remaining unverified figures** (TRD permit counts, ACS B25004) by opening them in a normal browser.

## Constraints if republishing as a claude.ai artifact

- Scripts may load only from cdnjs, jsdelivr, unpkg, cdn.tailwindcss.com or code.jquery.com, pinned to exact versions. Stylesheets only from Google Fonts.
- No fetches to other hosts. All data ships as files next to the page; binary data must use a served type, which is why it's `.wasm`.
- No `alert`, `confirm` or `prompt`; no print; no downloads started by the page. `#` hash state reaches the page only as a plain token, which is why plan codes use only `[0-9a-v]` characters.
- The share link base is the constant `SHARE_BASE`. Change it if the game is hosted elsewhere.

## Key sources

**Shortage and production**
- Up for Growth 2024: https://upforgrowth.org/wp-content/uploads/2024/10/2024_Housing-Underproduction-in-the-U.S.-Report_Final-c-1.pdf
- Zillow deficit (via Mann Report): https://www.mannpublications.com/mannreport/2026/07/15/americas-housing-deficit-held-steady-at-4-7-million-units-for-the-first-time-in-years/
- NLIHC / Housing Action Illinois (via The Real Deal): https://therealdeal.com/chicago/2026/03/09/chicago-lacks-more-than-220k-affordable-homes
- Chicago permits, 2025 (TRD Data): https://therealdeal.com/data/chicago/2026/new-chicago-housing-units-up-12/

**Rent and wages**
- Rent growth (CoStar via Matthews): https://www.matthews.com/market_insights/chicago-il-multifamily-market-report-q4-2025
- Rent effect (Mense 2025): https://eprints.lse.ac.uk/127192/
- Wages (BLS ECI, June 2026): https://www.bls.gov/news.release/archives/eci_07312026.htm
- One-bedroom rent (Apartment List): https://www.apartmentlist.com/rent-report/il/chicago

**Zoning rules**
- Chicago Zoning Ordinance, Title 17: https://codelibrary.amlegal.com/codes/chicago/latest/chicagozoning_il/0-0-0-49197
- MPC zoning data, 2023: https://archive.metroplanning.org/news/10453/Data-Points-A-deep-dive-into-Chicagos-zoning-map-and-major-zoning-changes-in-the-last-two-decades
- MPC brief, 2025: https://metroplanning.org/wp-content/uploads/2025/03/ZLUA_Affordable-Housing-Data-Brief.pdf

**Policies**
- BUILD Act: https://www.dailyherald.com/20260607/real-estate/whats-next-for-pritzkers-stalled-housing-plan/
- Affordable requirement (ARO): https://www.chicago.gov/city/en/sites/affordable-requirements-ordinance/home/for-developers.html
- Terner Center inclusionary zoning modeling: https://ternercenter.berkeley.edu/wp-content/uploads/2024/04/Inclusionary-Zoning-Paper-April-2024-Final.pdf
- Cut the Tape: https://www.chicago.gov/city/en/depts/mayor/press_room/press_releases/2025/may/Cut-the-Tape-Year-of-Progress.html
- Mayer & Somerville: https://realestate.wharton.upenn.edu/wp-content/uploads/2017/03/331.pdf
- Short-term rentals (WTTW): https://news.wttw.com/2025/06/11/key-city-panel-advances-measure-would-allow-alderpeople-block-new-short-term-rentals
- Airbnb listings (AirDNA): https://www.airdna.co/vacation-rental-data/app/us/illinois/chicago/overview
- Single stair: https://www.thedailyline.com/chicago-city-council-zoning-committee-hearing-recap-single-stair-apartment-proposal-alderman-matt-martin-fire-buildings-department
- ADUs: https://news.wttw.com/2026/04/09/coach-house-ordinance-aimed-housing-affordability-crisis-takes-effect-chicago
- City-owned lots: https://www.illinoispolicy.org/press-releases/new-report-chicago-vacant-lots-fuel-crime-poverty-on-south-and-west-sides/

**Office conversions**
- Sun-Times: https://chicago.suntimes.com/other-views/2026/08/03/building-housing-affordable-requirements-ordinance-regulations-development-lylena-estabine
- WBEZ: https://www.wbez.org/real-estate-development/2025/04/25/office-residential-conversions-apartments-housing-downtown
- Cushman & Wakefield Q2 2026: https://content.cushmanwakefield.com/api/public/content/afebd680503f4418a7c6cb0b53fb9c03

**Interest-rate card**
- Terner Center, Making It Pencil: https://ternercenter.berkeley.edu/wp-content/uploads/2023/12/Making-It-Pencil-December-2023.pdf
- Census starts (FRED): https://fred.stlouisfed.org/data/HOUST5F
- Bisnow on Chicago building costs: https://www.bisnow.com/news/chicago/multifamily/why-doesnt-chicago-build-more-apartments-133834

**Myths:** Asquith, Mast & Reed; Li 2022; Mast 2023; Bratu et al. 2023; Barron et al. 2021; Jin et al. 2024; CHA 2025; A City That Works 2026; CMAP 2022; Twinam 2017; Ewing & Cervero 2010. All are linked in `MYTHS` in `index.html`.

**Data**
- City of Chicago building footprints: https://github.com/Chicago/osd-building-footprints
- City of Chicago street centerlines: https://github.com/Chicago/osd-street-center-line
- Zoning districts (Chicago Data Portal): https://data.cityofchicago.org/api/geospatial/dj47-wfun?method=export&format=GeoJSON

**Worked in other cities (not on the table in Chicago)**
- Minneapolis 2040 plan (Pew, 2024): https://www.pew.org/en/research-and-analysis/articles/2024/01/04/minneapolis-land-use-reforms-offer-a-blueprint-for-housing-affordability
- Cambridge multifamily zoning: https://www.cambridgema.gov/cdd/projects/zoning/multifamilyhousing and https://hoodline.com/2026/07/cambridge-cul-de-sac-showdown-zoning-revamp-ignites-teardowns-protests-and-lawsuits/
- Houston small lots: https://mercatus.org/research/policy-briefs/learning-houstons-townhouse-reforms and https://www.pew.org/en/research-and-analysis/issue-briefs/2023/09/lot-size-reform-unlocks-affordable-homeownership-in-houston
- Buffalo parking (Hess & Rehler, 2021): https://doi.org/10.1080/01944363.2020.1864225
- Austin rents (Pew, 2026): https://www.pew.org/en/research-and-analysis/articles/2026/03/18/austins-surge-of-new-housing-construction-drove-down-rents
- Texas SB 840 (Dallas Morning News, 2026): https://www.dallasnews.com/opinion/editorials/article/texas-sb-840-housing-apartments-report-22373676.php
- Vancouver empty-homes tax: https://vancouver.ca/files/cov/2025-empty-homes-tax-annual-report.pdf
- Chicago vacant homes (ACS 2024 B25004): https://data.census.gov/table/ACSDT1Y2024.B25004?g=160XX00US1714000
- Montgomery County Housing Production Fund: https://www.hocmc.org/about-us/innovations/housing-production-fund/ and https://www.naco.org/news/county-backed-loan-fund-unlocks-thousands-affordable-housing-units
