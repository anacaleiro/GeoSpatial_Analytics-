# Elderly Transit Accessibility in Lisbon

Geospatial analysis identifying parishes in Lisbon where elderly residents are most underserved by public transit, combining Census 2021 data, GTFS bus schedules, and OpenStreetMap health facilities into a composite criticality index.

## Research question

Which Lisbon parishes face the greatest gap between elderly population concentration and bus service availability?

## Data sources

| Dataset | Source | File(s) |
|---|---|---|
| GTFS bus network | Carris Metropolitana (CMET) | `CMET/stops.txt`, `stop_times.txt`, `trips.txt` |
| Census 2021 + BGRI polygons | INE / Statistics Portugal | `Census/BGRI21_CONT/BGRI21_CONT.gpkg` |
| Hospitals & clinics | OpenStreetMap via OSMnx | queried at runtime |

## Methodology

1. **Preprocessing** — GTFS stops clipped to Lisbon municipality boundary; BGRI census subsections dissolved to 24 parish polygons; OSMnx health facilities (hospitals, clinics, doctors) fetched and converted to points. All layers reprojected to EPSG:3763 (PT-TM06).

2. **Transformations** — Each bus stop buffered at 800 m (10-min walk threshold); buffers dissolved into a unified coverage surface; coverage ratio computed per parish as intersection area / parish area. GTFS departures filtered to 07:00–21:00 and counted per stop; mean frequency aggregated to parish level.

3. **Analysis** — Elderly share (65+ / total population) derived per parish. Three variables min-max normalised: elderly share, coverage ratio, mean departures. Equal-weight composite index:

   ```
   index = (elderly_share_norm + (1 - coverage_norm) + (1 - frequency_norm)) / 3
   ```

   Higher index = more critical (elderly people, low transit access). Jenks natural breaks (k=4) applied to classify parishes into Low / Moderate / High / Critical.

4. **Outputs** — Four 300 DPI maps and a ranked CSV exported for StoryMap use.

## Results

| Class | Parishes |
|---|---|
| Critical | 7 |
| High | 6 |
| Moderate | 8 |
| Low | 3 |

Peripheral parishes in south-west and east Lisbon score highest — combining above-average elderly shares with near-zero bus coverage and low service frequency.

## Project structure

```
.
├── CMET/                       # Raw GTFS data (Carris Metropolitana)
├── Census/                     # Raw INE Census 2021 + BGRI polygons
├── scripts/
│   ├── 01_preprocess.py        # Load, clean, save three input layers
│   ├── 02_transform.py         # Buffers, coverage ratio, frequency
│   ├── 03_analysis.py          # Composite index + Jenks classes
│   └── 04_outputs.py           # Maps (300 DPI PNG) + CSV table
├── data/
│   └── processed/              # Intermediate and final GeoPackages
└── outputs/                    # Final deliverables (maps + CSV)
```

## Reproducing the analysis

```bash
# Install dependencies
pip install geopandas osmnx mapclassify matplotlib

# Run pipeline in order
python scripts/01_preprocess.py
python scripts/02_transform.py
python scripts/03_analysis.py
python scripts/04_outputs.py
```

All scripts are run from the project root. Internet access is required for the OSMnx query in step 1.

## Limitations

- Bus coverage uses straight-line 800 m buffers, not actual pedestrian walksheds.
- GTFS departure counts treat all weekday service equally; actual frequency varies by day/season.
- Elderly share is at parish level — intra-parish variation is not captured.
- Health facility overlay is illustrative; proximity to hospitals is not included in the index.
