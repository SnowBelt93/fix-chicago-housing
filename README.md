# Fix Chicago Housing

A fan-made browser game on a 3D model of Chicago's ~481,000 buildings. Rezone the city, flip real housing policies, and simulate 15 years to see whether you can close the region's housing shortage. Every number in the game links to its source or is labeled as a game assumption.

*A fan-made game. Not affiliated with the City of Chicago.*

## Run it
It's a static site with no build step: open `index.html` through any web server (for example `python3 -m http.server`) or deploy the folder to Cloudflare Pages / GitHub Pages.

## What's here
- `index.html`: the whole game (HTML, CSS, JS; loads deck.gl from unpkg)
- `meta.json`: community areas, stations, corridors, merged station zones, lake, street labels
- `b/*.wasm`: building and street binaries (not WebAssembly; named that way for an earlier host)
- `tools/`: Python scripts that rebuild the data from City of Chicago open data
- `CLAUDE.md`: full spec, model and sources

## Data
Building footprints and street centerlines: City of Chicago open data. Sources for every figure are listed in the game's "The math" tab.
