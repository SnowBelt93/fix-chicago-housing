# Fix Chicago Housing — project spec and handoff

A free, browser-based game on a real 3D model of Chicago's ~485,000 buildings. Players change zoning and flip on real housing policies, then simulate 15 years to see whether they close the region's housing shortage and what happens to rent.

**Goals, in order:** teach people the real causes of the housing crisis, let them try to fix it, and make it fun. It's a for-fun project, not a policy tool. It must never feel bloated.

**Owner:** Kyle (urban planner / housing finance background; doesn't code; directs Claude to build).

**Live version:** a private claude.ai artifact at https://claude.ai/artifact/XHPMwjqFSW9C4Rbmg8Xe81. Republishing needs the claude.ai Artifact tool. Otherwise host the folder anywhere static: it's plain HTML plus data files, with no build step.

## Decisions already made (don't relitigate)

- **Name:** "Fix Chicago Housing."
- **Voice:** witty, a little edgy, mild language at most. Myth cards and public comments carry the humor; numbers stay straight and sourced.
- **Devices:** phone and desktop equally.
- **Look:** "City Hall" only (Kyle picked it over Ballpark Scoreboard and Lakefront at Night). It's a civic look inspired by chicago.gov: nav blue #2b5da0, flag blue #41b6e6, red six-point stars #e4002b, blue score band, Big Shoulders Display + Public Sans + Source Serif 4. Guardrails: no city seal, logo or "official" banner, and the line "Not affiliated with the City of Chicago." stays visible. The old "Playful" look and Style button are gone (`setLook("model")` is still called once to set legend colors). The three prototypes live in a claude.ai design canvas: https://claude.ai/artifact/HnniCGdUrGZfhKYKB7qgAR (artboard "Main" = A).
- **Citations:** every number in the game is either linked to a source or listed under "Game assumptions (not measured)" in The math tab. Keep it that way: no new number without a link or an assumption label.
- **Accounts:** none. Saving is browser storage plus share links and plan codes that encode the whole plan.
- **Not included, on purpose:**
  - A transfer tax / "mansion tax" as a pro-housing lever (Kyle: shown to reduce development, as in LA). Since Oct 12, 2026 it appears only in "Ones that cut supply," as an example of what not to do.
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
- **Chance it rebuilds within 15 years (since v28):** `rebuildRate(demand)` = `UPZONE_LIFT` (2, assumption) × `REBUILD_OBS`, Chicago's observed 2013–2025 teardown-and-rebuild rate on small pre-2000 home lots that today's zoning already allowed to hold more homes, interpolated by the neighborhood demand factor (0.3–2.5×, from each area's share of buildings built since 1990): 0.42% / 0.71% / 3.04% / 6.10% / 7.36% per 15 years at demand 0.38 / 0.66 / 0.97 / 1.40 / 2.40, flat outside. So a rezoned lot's chance is ~0.8% in the softest areas, ~6% at average demand, ~15% in the hottest; capped at 60%. Reproduce with `tools/calibrate_rebuild.py`. Policy multipliers stack on top:
  - Prerogative reform: +15%.
  - Faster permits: +10% chance, and homes arrive about 7 months sooner (`PERMIT_SHIFT` 0.6 yr; assumption).
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
  - Starting shortage: the selected estimate (Up for Growth 165,687 by default; Zillow 115,282; NLIHC 224,445; or Chicago's share of Up for Growth, 54,141, which also grows only 32.7% as fast).
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
- **Fact check (Oct 11, 2026):** an independent pass verified ~50 figures and fixed: ARO factor 1.30/0.70 (Terner ~30%), Airbnb entire-home share 80.2% (AirDNA supply page), HUD prerogative finding dated 2023 and withdrawn 2025, $70B affordable math, Houston assessed values and lot sizes, ADU details, rate-card labeling, Vancouver/Cambridge/Minneapolis wording, and missing source links. Persona wages are BLS OEWS May 2025 medians (home aide is SOC 31-1120). Verified Oct 12, 2026 in a normal browser: TRD Data says Chicago OK'd "more than 4,900" units in 2025 (2023: ~9,500; first half of 2026 up 12%); ACS 2024 B25004 "other vacant" = 60,223 ±5,165 of 109,793 vacant.
- **Motion (v11):** modals rise in / sink out (`hideModal()`), panes fade, details slide open, grade pops on change. Simulation: one year = `YEAR_MS` (700 ms); buildings rise continuously (elevation transition = one year, linear); neighborhoods update in a 6-frame ripple (`recomputeWave`); camera does one smooth eased 70° orbit with a slight pitch arc (`orbit()`). All motion is off under prefers-reduced-motion.
- **Myths (v11):** each card is myth quote → one-line verdict (`a`) → plain-language explanation (`b`) → sources.
- **Goal explained (v11):** intro shows 165,687 today + 131,400 growth = 297,087; the Missions tab shows the same equation for whichever shortage estimate is selected.
- **v12:** station zones are pre-merged shapes (`meta.json` ringL/ringM/ringLM from `tools/prep_rings.py`) so overlapping circles read as one zone; camera buttons (zoom, spin, 2D/3D, reset) plus a walkthrough step; zoom limited to the city region; basemap presets in `BASES` (island / region / night, default region) with an extended Lake Michigan shape and neighboring-town labels; policies that add nothing explain why (`ZERO`); ARO card explains the tradeoff and that real-world evidence is mixed.
- **v13 (branch `next`):** disclaimer now just "Not affiliated with the City of Chicago."; share links + preview image on fixchicagohousing.com; keyboard camera (WASD/arrows, Q/E, R/F, +/-); new levers: suburban Metra stations (`plan.sub`, 168 stations × game-model per-station homes × 0.3, assumption) and "Get the megaprojects built" (`p.mega`, `MEGA` list of 6 projects, 31,094 planned homes × 0.5 (North Union corrected to 2,007 left, Oct 2026), assumption) with purple map pins and a "Big projects in the pipeline" section in The math; plan code `u4` (= u3 + suburban tier; `mega` appended to BIT_KEYS); OpenFreeMap/MapLibre vector basemap under the deck canvas (camera synced in `onAfterRender`), only on our own domain, falling back to the built-in basemap elsewhere; zoning flags merged (96,392 of 481,262 buildings, 20.0%, with lots estimated as max(2× footprint, 3,125 sq ft)) and a first-visit intro hook that shows them red (`introHook`).
- **v14:** intro opens with an Axios Chicago headline clipping; results screen has "Do something about it" (copy-a-note + ward lookup, ILGA members, Abundant Housing Illinois, Housing Action Illinois) and "Add it to the community"; the Save tab is now **Share** with "What other players chose", a plan gallery (newest / most liked / my neighborhood, open-to-remix, likes) and an "I live in" picker; policy cards show "% of players turn this on" once 20+ plans exist. Backend: `worker/index.js` (Workers + one SQLite Durable Object `Community`), config in `wrangler.jsonc` (static assets from the repo root, `.assetsignore` keeps tools/docs private, custom domains fixchicagohousing.com + www). Finished simulations are counted anonymously; posting to the gallery is opt-in; no free text is stored, so nothing needs moderation; rate limit 40 plans per hashed IP per day. Community UI hides itself where there's no /api (claude.ai preview).
- **Expand mode (v15):** desktop "⤢ Expand" button widens the tool panel next to the score card (cards in a grid, Build tab in two columns); "⤡ Collapse" returns to the sidebar; remembered per browser (`fch-wide`).
- **v16 polish:** frosted (90% + blur) panels; sliding switch knobs (transform) and sliding highlight on segmented controls (`syncSeg` via MutationObserver); controls update instantly and the city recomputes a frame later (`later()`); policy "+homes" numbers computed one policy per tick so the page never freezes; comment bubble centered over the map; affordable homes shown in the score band, Impact and results (ARO + 30% of social housing + 20% of megaprojects); expand/collapse animated; expanded tabs organized (even card grids, Build cards, Share in two columns, Impact/Math use the width).
- **v17:** public comments are cards in a stack (`#comment` positions; each `.cbox` animates with the Web Animations API): newest on top, older ones slide down (`flipCards`) on desktop or tuck in behind as peeks on phones, max 3, each stays until its × / Escape / Simulate, 1.2 s throttle; it appears a couple of frames after the map redraws (`showComment` → `showCommentNow`) so it never stutters; confetti (`celebrate` + `fxFrame`, shared `fxParts`) fires from both bottom corners, lands on the bottom edge of the window, rests 2.6–5 s, then dissolves; expand mode centers the tabs, Build's odd last card and Impact cards, and The math runs in two columns.
- **v18:** first run goes intro → walkthrough (the illegal myth waits for the overlay toggle); compact desktop score panel (number + goal on one row, two-line title); neighborhood banner sits above the map credit; tabs fit the sidebar ("Math"); counter progress clamped so it never shows negatives; deck + MapLibre capped at 2× pixel ratio and no panel blur on phones; basemap redraws in the same frame as deck (`bmap.redraw()` in `syncBasemap`) so streets don't trail buildings; cinematic simulation (`cinema()`: flies to the 3 spread-out neighborhoods gaining the most, hovers with a caption `#cineCap`, ends on a city-wide shot; dragging the map hands the camera back; `orbit()` is the fallback); the timeline under Simulate is a slider (`#yrRange`, `scrubTo()`) to see any year 2026–2041, any change snaps back to 2041, and the results screen has "See 2026 vs. 2041".
- **v19:** "Ones that cut supply · see what not to do" (Policies tab, collapsed; `group:"worse"`, red switches): downzoning (`down`), parking minimums back (`pmin`, turns off `park`), moratoriums/extra review (`mora`, projects 25% later, some slip past 2041), rent control incl. new buildings (`rentc`, framed as a tradeoff), mansion tax (`xfer`). Each cuts a share of the ~4,900/yr Chicago builds anyway (`WORSE_BASE`, combined multiplicatively in `baseCut()`) and some cut rezoned projects; totals can go negative (`parts.worse`), rent rises above no-change, grade F. City budget: Impact "Jobs, taxes and the city budget" (`#impBudget`) and a results tile compare NAHB local revenue with the city's $882M 2027 gap (`BUDGET_GAP`, WTTW). Plan code `u5` = u4 with a 4th on/off char (BIT_KEYS + down, pmin, mora, rentc, xfer); the worker accepts u4 and u5. Negative plans aren't submitted to the community.
- **v20:** simulation headlines (`planHeadlines`, `#ticker`, 5 per run, all numbers from the model); shareable result image (`makeShareCard`, 1200×630, map captured in the same frame via `captureMap`/`grabMap` in `syncBasemap`; Web Share on phones, download elsewhere); Tower level (TIERS[5], L only, `plan.tod === 5`: 30 fl / 40 homes per std lot within ¼ mi of the 26 busiest L stations, `META.busy`; high-rise elsewhere; capped at 6,500/yr via `towerScale` in `fitTowers`; color code 7; myth `tower`); vacant-lot gap financing (`p.vland`: 15% of ~31,370 private vacant parcels × 2 homes, soft-market projects +50%; green dots from `b/vacant.wasm`, city-owned lots purple when `lots` is on); Impact "Riders for the CTA" (ETOD 2020 commute shares, CTA FY2026 $1.24/ride) and "Your ward" (per-building ward from `b/extra.wasm`, `META.wardStats`, outline from `wards.json`). Data comes from `tools/prep_extra.py` over `tools/raw/` (downloaded by `.github/workflows/fetch-data.yml`, since the cloud workspace can't reach the data portals). Plan code u5 allows tod 5; BIT_KEYS + `vland`.
- **v21:** neighborhood types (`meta.json` per-area `type`: 0 downtown core = Loop, Near North, Near West, Near South; 2 single-family = 70%+ of residential buildings hold one home; 1 mixed = the rest; set in `tools/prep_extra.py`) with a Build tool "Zone by neighborhood type" (`#tool-types`, `setTypeTier`); Tower is allowed only in core areas (`areaMaxTier`). Tapping a neighborhood opens an on-map card (`#hoodBanner.hoodcard`, `#hbTiers`) to rezone it right there; the tier callback captures the area number so a deferred update can't hit the wrong neighborhood. Policy scopes: `SCOPED` policies (build, adu, mpls, camb, small, park, vland, down, pmin, mora) get a "Where" picker (citywide or one neighborhood type), stored in `plan.scope`, checked with `inScope()`, and baseline cuts scale by `scopeShare()`. Build timing ramp: projects start slowly, peak in years 4–9 and taper (`RAMP_W`, `rampYear`, `rampFrac`; assumption, listed in The math). Results screen is a newspaper front page ("The Chicago Plan", dated Oct 12, 2041, headline + deck from the model, map photo of the top 3 areas via `frontPage()`/`captureMap`, "By the numbers", two charts side by side in `.charts2`), and the share image (`makeShareCard`) matches it. Plan code `u6` = "u6" + 77 area chars (0–5, one per area, so core areas can hold Tower) + tod, metra, corr, office, str, aro + 4 base-32 bit chars + goal + sub + 10 scope chars (`SCOPED` order); u5/u4/u3 still decode; the worker accepts u6. **BIT_KEYS now holds 20 keys, which fills the 4 bit chars:** the next on/off policy needs a 5th char and a new code version.
- **v22 (QA pass, Oct 12, 2026):** ARO dial has "None" (stored as aro = 3 so old codes keep 0–2; ×1.70 from Terner's no-requirement scenario, 398,800 vs ~233,000 homes at 20%, interpolated; 0 affordable); Tower rings pre-merged (`meta.json` ringBusy from `tools/prep_rings.py`, ¼ mile) and drawn under buildings, half-mile zone uses the high-rise color under Tower; height-specific comment pools (`mid`, `high`, `tower`, via `tallKind`); `money()` shows billions as $1.0B; myths queue while the walkthrough is up and show when it ends; picking an L level advances the walkthrough; intro buttons are sticky on short screens; phones: map key above the credit line, compact neighborhood card, map key hidden while it's open; expanded panel goes one column under 1280px and comments sit under the score card; each tab keeps its own scroll (`paneScroll`).
- **Map registration fix (Oct 12, 2026):** the prep scripts had written building and street offsets with 110,574 m per degree of latitude, but deck.gl's METER_OFFSETS reads them at 111,319.49 m per degree (its Web Mercator sphere), so everything sat 0.67% too close to each file's origin north-south (up to ~15 m inside a community area, ~130 m at the city's edges for streets). `tools/rescale_meters.py` rescaled the stored offsets once (`meta.json` "meterScale": "deck"), and every prep script now uses KX = 111,319.49·cos(lat0), KY = 111,319.49.
- **Data vintage (checked Oct 12, 2026):** the building footprints (stories, units, year built) are the city's **February 2013** release (`osd-building-footprints` CHANGELOG v20130201); the portal copy `syp8-uezg` was last updated in 2015, so there is no newer city version. Since v22, `tools/prep_extra.py` sets extra bit 64 ("gone") on 5,195 small pre-2000 buildings that contain a parcel point that is vacant today (Cook County class 100, 2025, or city-owned land): they're hidden (`col` 8, transparent), skipped by zoning, excluded from the illegal count and ward stats, and subtracted from "homes today" (`meta.areas[].gone`). **2022 update (v23):** `.github/workflows/fetch-footprints.yml` + `tools/fetch_cook_2022.py` download Cook County's 2022 footprints with LiDAR heights (1.26M in the city's bounding box) into `tools/raw/cook_bldg_2022.bin.gz`; `tools/prep_fresh.py` compares them with the 2013 buildings (idempotent from `meta.areas[].n13/v13`): 2013 buildings under 30% covered in 2022, mostly covered by a brand-new building, or low-rise and rebuilt much taller with a different outline go to `tools/raw/fresh_gone.json` (prep_extra turns them into the gone bit; 14,563 gone in total with the vacant-parcel rule, 17,855 homes); 2022 buildings that barely overlap any 2013 building (under 20%) and aren't garage-sized are appended to the end of each area file (18,694; flag 8, units 0, stories = (height − 4 ft) / 13); 2013 buildings with 0 stories get LiDAR stories when the outlines match (IoU 0.4+). Then run `tools/prep_extra.py`. Homes inside post-2013 buildings aren't counted (no unit data). Other sources are current: wards 2023, CTA ridership 2025, vacant parcels 2025, city land inventory, zoning map, L stations (incl. Damen Green Line, 2024).
- **v24 (independent number check, Oct 12–13, 2026):** two separate agents re-checked sources and the model. Fixed: "near transit" share no longer counts suburban Metra homes (could exceed 100%; also inflated CTA riders); `SUB_PER_STATION` refreshed from the current model ([0,52,228,514,1234]); faster permits now shift homes ~7 months earlier instead of compressing 15 years into 12, and moratorium delays scale a continuous year (no empty years); `marginal()` respects the parking pair; supply-cut cards show the marginal cost given the others (`baseCost`); score-band affordable line is computed per year and never negative; "Affordable push" mission counts the requirement only (`affReq`); fitTowers also caps Tower set by neighborhood; ward "(city: X%)" computed; torn-down buildings excluded from coach-house lots and the rezoned share (`A.goneN`); towers (10+ stories) are never marked gone by the 2022 diff (the county data misses some, e.g. Lake Point Tower). Text: 606/Pilsen fee ($20,000 per home or $60,000 per building since 2024), Missing Middle 2025–26, North Union 2,007 left (megaprojects total 31,094), Foundry Park/The 78/Bronzeville/1901 sources, downtown 2021 absorption 6,500–6,800, St. Paul permits, parking $621 for car-free renters, downzoning "higher-valued", South Works "slated to become", data wording. Audit harness: `scratchpad/audit/harness2.js` (line ranges must be updated when index.html changes).
- **v25 (realistic massing, Oct 13, 2026):** land assembly in `compute()`: projects at mid-rise / high-rise / tower need `SITE_MIN` = 5,000 / 7,500 / 15,000 sq ft of lot (about 2 / 3 / 6 city lots), so the anchor buys eligible neighbors within `SITE_R` 35 m (same block face; `nearby()` over a 25 m grid built lazily by `siteGrid()`, cached per building), up to 10 lots; lots that are vacant today (gone) can join. The site's level is capped by the lowest-zoned member, downgraded if the land falls short, and high-rise / tower need the site's narrow side ≥ `SITE_WIDTH` 12 / 20 m. Calibration: the anchor passes `u < p`, gathers its site, then is accepted only if `u < p × lot / siteLot`, so each lot's redevelopment rate stays 6% × demand. Drawn buildings (`siteBox` + `siteShape`): a box over the site lined up with the block face (or the building for one lot), lot depth ≈ site area ÷ frontage; footprint × stories = gross homes × `SQFT_HOME` 1,026 sq ft (the office-conversion figure), with varied heights (`drawnStories`) that go up to the zoning limit before spreading out; towers = 4-story podium over the box + a tower of at least 18 m holding the homes. Shapes are cached per area (`A.projKey`) so year-to-year updates only change heights (no re-tessellation). Members are tracked in `A.claimed`; built projects hide their old buildings (col 8) and draw in a per-area `p<num>` layer from `A.proj`. Totals vs. before massing: mid-rise at L +1%, high-rise −3%, combo −3%, core tower −8%. `SUB_PER_STATION` = [0,52,228,521,1199]. The Tower busy-station wash and its invisible ridership layer were removed (Kyle didn't want circles); half-mile zones for high-rise/tower use a lighter wash with thinner outlines, and every station zone fades to a faint tint with no outline at close zoom (`zoomBandNow === 2`). Live check on Kyle's Mac (Oct 13): simulation 58 fps (p90 33 ms), one ~150 ms task per zoning change; totals vs. the 2013-data version are lower mainly because of the 2022 data refresh (e.g. high-rise at L 173k → 153k), then −3% from land assembly. Audit harness: `scratchpad/audit/harness4.js` (ROOT env var; finds code ranges by markers); `size.js` checks floor area per home and slivers, `cmpver.js` compares plan totals across versions.
- **v26 (empty land, Oct 13, 2026):** `b/land.wasm` (from `tools/prep_extra.py`; format at the top of that script) holds, per area, `open[N]` (1 = a gone building whose lot is empty in 2022 or holds a vacant parcel; city-owned lots excluded) and k private vacant parcels (Cook County class 100, 2025) not under any footprint (25,678), with local x/y, flags (L/Metra/corridor/busy-station bits) and ward. `loadLand()` runs inside `loadExtra()`. In `compute()` empty land is buildable when rezoned: open lots of torn-down homes or small shops (footprint ≤ 6,000 sq ft) and parcels (indices n..n+k−1, `VAC_LOT` 3,125 sq ft) build with no homes replaced, at `VAC_EASE` 1.5× the chance (assumption), and can be assembled into sites; `A.vacUsed` counts empty lots used, and the vacant-lot policy uses `vacantLeft()` so parcels aren't counted twice. `compute()` was restructured for speed (plain locals, inline tier function `tierF` matching `tierFlags`, candidate logic in `tryAt`); `siteBox` results are cached per area (`A.boxC`); policy "+homes" passes only run while the Policies tab is open (`gainsStale`). Totals: high-rise at L 148.7k → 174.3k, mid-rise 64.6k → 78.1k, strong combo 275.5k → 317.8k (goal 297,087). `SUB_PER_STATION` = [0,87,299,630,1406]. Harness: `scratchpad/audit/harness5.js`.
- **v27 (buildings square to streets, Oct 13, 2026):** Kyle saw new buildings turned at angles and sitting on streets. Causes: a site's direction came from the anchor-to-farthest-member line, sites could jump across side streets, and buildings stretched evenly both ways. Now:
  - Each lot has street axes (`axesOf`, cached in `A.ax`): the face runs perpendicular to the footprint's longest edge unless the neighbors line up along it; vacant parcels borrow the nearest building's edges.
  - A site only takes lots on the same block face (`rowOf`, within `ROW_TOL` 10 m along the depth) that touch the site so far (`SITE_GAP` 9 m along the face).
  - `siteBox0` is the members' footprints boxed in the anchor's axes. It's trimmed off any street centerline inside it (margin = half-width − 4 m; a 2 m fallback; half-widths in `STREET_HALF`: 20 expressway, 13 arterial, 11 collector, 10 local). It grows only toward the back of the lot (`back`, `room` ≤ 24 m), stopping 8 m short of buildings behind and 1 m short of the property line.
  - Streets live in one citywide segment grid (`streetSegs`, 50 m cells), queried with `streetPtsIn`. `boot()` awaits the streets before the first full compute, so totals don't depend on load order.
  - Mid-rise now needs a site at least 9 m wide (`SITE_WIDTH[3]`).
  - `tools/prep_extra.py` drops 397 vacant-parcel points that sit inside a street right-of-way (land.wasm parcels 25,282).
  - Speed: `prepStatic` (per-building tier key, eligibility and lot size; tier lookup table `LUT`), `pUB` early reject, a scratch site buffer (`MB`), and a signature fast path (`A.sig` → `showYear`) for year-only changes.
  - `html{background:#fff}` so iOS Safari's bar areas are white rather than the gray `--table` color.
  - Checks (`scratchpad/audit/harness6.js`, which loads streets): shapes overlapping a drawn street went from 6.3% to 0–0.03% (existing buildings: 0.17%); shapes within 3° of the nearest street's direction went from 43% to 95% (existing buildings: 95%); no centerline inside any new shape; no tall slivers; floor area per home median 1,026 sq ft.
  - Totals (node harness and the live page agree for zoning): L mid-rise 74,994, L high-rise 165,173, strong combo 305,037 in the live game (goal 297,087), core tower 183,575. The harness skips the live game's coach-house recount that drops torn-down buildings (382,338 lots → 3,785 coach houses, vs 3,877 in the harness), so harness totals with ADUs on run ~92 homes high. Add `?perf` to the URL to log each recompute's time to the console (`[fch]`); a full recompute at load took ~0.5 s on Kyle's Mac. `SUB_PER_STATION` = [0,86,297,605,1332].
  - Scripts: `align.js` (orientation and drawn-street overlap), `streetcheck.js`, `size.js`, `cmpver.js`, `sub.js`.
- **Methodology doc (Oct 13, 2026):** Claude Docs "Fix Chicago Housing — Methodology" (https://claude.ai/artifact/4WrcNW4PZMB1fctMezrLph) explains every calculation, with a sensitivity table and a Tough questions section (sensitivity as of v28, L high-rise 157,669: lift 1.5 / 2.5 → −23% / +23%; no lift → −47%; rebuilds that add homes only → −39%; lot 1.5× footprint → −25%; no land assembly → +12%; empty-land ease 1.0 → −4%; one citywide rate with no demand gradient → +3%, strong combo +31%). An independent review found, and the game now fixes: the tower cap is a 15-year total (`TOWER_CAP` = 97,500), and the 6,500/yr is Integra's mid-2021 *forecast* for downtown, not an actual year (Math tab and tower myth reworded); St. Paul permits dated 2022–23. **Still open for Kyle:** (1) `ELASTICITY` 0.19 is cited to Mense 2025 as "per 1% of stock", but Mense measures a 1% increase in the yearly *flow* of new completions (Germany, short run), so either relabel 0.19 as a conservative assumption or switch to a stock-based estimate (literature −0.4 to −0.5 demand elasticity → 2–2.5% lower rent per 1% more homes); (2) the model doesn't subtract redevelopment already legal under today's zoning, so low-level totals overlap the ~4,900/yr baseline; ~~(3) metro goal vs. city plan~~ done: city-only goal option (v28); ~~(4) uncalibrated 6% base rate~~ done: calibrated to Chicago permits (v28).
- **v28 (Oct 13, 2026):** city-only goal: 4th `TARGETS` entry = Up for Growth's metro shortage × `CITY_SHARE` (1,282,248 / 3,924,020 homes, ACS 2024 = 32.7%) = 54,141 today, growing 2,862/yr (8,760 × 32.7%, `gapGrowth()`), goal 97,078; suburban Metra homes don't count toward it; u6 goal char now 0–3 (game and worker). Rebuild rate calibrated (see Model): `.github/workflows/fetch-permits.yml` downloaded city building permits (new construction + wrecking, 2013 on) and the zoning map to `tools/raw/`; `tools/calibrate_rebuild.py` matches residential new-construction permit points to the nearest 2013 building within 5 m (finds 87% of known teardown-rebuilds, i.e. a wrecking permit plus new construction at the same address) and measures rebuild rates by demand band on lots where today's map allows more homes. Findings: the old flat 6% × demand overstated soft markets ~5× vs observed; rate rises with demand (corr 0.45) but not with how many extra homes are allowed; 2013–19 ran faster than 2020–25 (4.6% vs 3.5%); within a demand band, lots that allow more were rebuilt 1.5–2.2× as often as lots that don't, except the hottest band (0.94×). `UPZONE_LIFT` 2 also leans on Auckland (upzoned-area permits ~3,000/yr in 2016 → ~14,500 in 2021; 21,808 extra over 5 years, Greenaway-McGrevy & Phillips 2023). Caveat: the zoning map is today's, so lots rezoned for a project during 2013–2025 count as "already allowed". Totals now: L mid-rise 71,647, L high-rise 157,669, strong combo 279,886 (harness), core tower 175,497, BUILD 3-flat 15,328; South Side share falls most (combo South 86,200 → 70,805). Every mission is still winnable. `SUB_PER_STATION` = [0,83,287,578,1272]. Mockups for a less generic UI are in the design canvas https://claude.ai/artifact/Jf9BFp7SjPJcxC5qFJkcp6 (before/after main screen, council-docket policies, comment slips + map key + drawn icons, newspaper results page, phone); UI Teardown doc lists the changes. Not built yet.
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
8. ~~Verify the two remaining unverified figures~~ Done Oct 12, 2026 (both match).

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
