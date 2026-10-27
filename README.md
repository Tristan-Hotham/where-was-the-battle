# Where Was the Battle?

Lost battlefields of early Britain. 88 places proposed for 18 battles, from Boudica's last stand to Assandun, each placed on the map from a cited source, measured on the ground, and scored against the clues the early texts actually give.

**Interactive version:** https://tristan-hotham.github.io/where-was-the-battle/

This repository holds the interactive page, the candidate sites with their sources, the measurements and checks, and the analysis code for the data study *Where Was the Battle? Lost battlefields of early Britain* by Dr Tristan Hotham (Independent researcher, ORCID 0000-0003-4931-9349).

## Headline results

- The 15 lost battles with more than one proposed site have theories a median of 89 km apart (farthest pair). Four span more than 300 km: Camlann (679 km), Badon (580 km), Brunanburh (386 km) and Boudica's last battle (325 km).
- The tightest cluster is the Battle of Whalley (798) in Lancashire: all five proposed sites lie within 3.5 km. Only Billington meets both of the texts' clues (near Whalley, on a hill-spur).
- The texts give only 31 testable clues across 18 battles; Catraeth and Degsastan give none. Of 85 scored sites, 20 meet every clue for their battle and 4 meet none. In 9 of 16 scored battles, two or more sites tie for the best fit.
- For Badon ("the siege of Badon Hill"), four hillforts on high ground meet both clues; Bath, Geoffrey of Monmouth's answer and Wikidata's pin, meets neither.
- Wikidata gives one exact coordinate to 12 of the 17 lost battles; nine sit within 2 km of a proposed site, while Mons Graupius is pinned 41.5 km from the nearest proposal and Edington 20.8 km from the site in Wikipedia's own article.

## Files

- `index.html`: the interactive page (Leaflet maps, charts). `header.png`: social card.
- `data/candidates.csv`: one row per proposed site: battle, site, proposer as the source reports it, kind of case, source URL, latitude and longitude, precision (site, village, area) and where the point came from.
- `data/candidates_scored.csv`: the same with every measurement (height, local height rank, relief within 1 and 3 km, distance to the sea, a named river, a named lake, a Roman road, the nearest hillfort, the Humber and Liddel Water), the fit score and its rank within the battle.
- `data/checks.csv`: one row per site and check: the measured value and the score (1, 0.5, 0).
- `data/battles.csv`: one row per battle: number of sites, number of checks, spread (farthest pair and median pair distance), best fit and the sites that reach it, and Wikidata's coordinate.
- `data/unplaced.csv`: proposals too vague to place (a county, a ridge).
- `data/coast_bi.geojson`: simplified coastline of Great Britain, Ireland and Man used for the distance to the sea and the maps.
- `data/results.json`: every number quoted on the page, the paper, the blog post and the collage, plus the text of each battle's clues and checks.
- `code/`: run in order `01_candidates.py`, `02_measure.py`, `03_analyse.py`, `04_site_layers.py`, `05_build_site.py`, `06_header.py`. `dem.py` reads the elevation tiles. The shared inputs (OS Open Names, OS Open Rivers, the elevation tiles, Itiner-e, the Atlas of Hillforts, Pleiades, Wikidata, Natural Earth) are not included; paths are set at the top of each script.

## Method in brief

For each battle I list the clues the early texts give about the place and turn each into a check with a stated threshold: a hill (the site, or the highest ground within 1 km, in the top 10% of ground within 2 to 3 km; top 25% loosely), steep ground (relief within 3 km), open ground (little relief within 1 km), the sea, a river, a lake, a hillfort to besiege, a Roman road, or a named place nearby. A check scores 1 if met, 0.5 if met loosely, 0 if not; a site's fit is the average. Proposed sites come from each battle's English Wikipedia article (80 of 88) and from the Victoria County History of Lancashire, ScARF, The Modern Antiquarian and TheCollector. No coordinate is guessed: each comes from OS Open Names (62), the Atlas of Hillforts (8), a grid reference (7) or coordinate (6) in a source, OS Open Rivers (4) or Pleiades (1).

Caveats: this is a tally, not a verdict. It ignores place-name, archaeological and charter evidence, which drive most identifications; it weighs late chronicles the same as early ones; many points stand for a village or a river rather than a field; lakes have been drained and the 90 m elevation model smooths summits; the list of proposals is what Wikipedia's editors chose to include; and Wikidata's coverage differs by country.

## Sources and licences

- Proposed sites and clues: English Wikipedia articles on each battle (CC BY-SA 4.0), retrieved October 2026; Farrer, W. and Brownbill, J. (eds) 1911, *A History of the County of Lancaster*, vol. 6, via British History Online (https://www.british-history.ac.uk/vch/lancs/vol6/pp349-360 and https://www.british-history.ac.uk/node/44977); ScARF (https://scarf.scot/); The Modern Antiquarian, Loe Hill (https://www.themodernantiquarian.com/site/3015/loe-hill); TheCollector, on Camlann; List of Historic Place Names of Wales (RCAHMW).
- OS Open Names and OS Open Rivers: contains OS data © Crown copyright and database right 2026, Open Government Licence v3.
- Atlas of Hillforts: Lock, G. and Ralston, I. 2017, *Atlas of Hillforts of Britain and Ireland*, https://hillforts.arch.ox.ac.uk (CC BY-SA 4.0).
- Roman roads: de Soto, P., Pažout, A., Brughmans, T. and others 2025, *Itiner-e: a high-resolution dataset of roads of the Roman Empire*, Zenodo 17122148 (CC BY 4.0), with a datum correction.
- Pleiades (CC BY 3.0). Wikidata (CC0). Natural Earth (public domain).
- Elevation: AWS Terrain Tiles by Mapzen/Tilezen (terrarium, zoom 10), built from SRTM, GMTED2010, ETOPO1 and national datasets. Attribution: https://github.com/tilezen/joerd/blob/master/docs/attribution.md
- Base map tiles on the page: Esri. Map library: Leaflet.

Because the candidate lists draw on Wikipedia and the Atlas of Hillforts, the derived data and the page text are released under CC BY-SA 4.0. Code is MIT (see `LICENSE`).

## Citation

Hotham, T. 2026. *Where Was the Battle? Lost battlefields of early Britain.* Zenodo. https://doi.org/10.5281/zenodo.23677163

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
