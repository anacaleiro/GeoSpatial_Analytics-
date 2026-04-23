"""
02_transform.py — Spatial transformations: buffers, coverage ratio, frequency.

Reads:  data/processed/bus_stops.gpkg, parishes.gpkg
        CMET/stop_times.txt
Writes: data/processed/parishes_enriched.gpkg
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT = Path(__file__).resolve().parent.parent
CMET = PROJECT / "CMET"
PROCESSED = PROJECT / "data" / "processed"
CRS = "EPSG:3763"

# ---------------------------------------------------------------------------
# 1. Load preprocessed layers
# ---------------------------------------------------------------------------
print("=== 1. Loading layers ===")
gdf_stops = gpd.read_file(PROCESSED / "bus_stops.gpkg")
parishes = gpd.read_file(PROCESSED / "parishes.gpkg")
print(f"  Stops: {len(gdf_stops)}  |  Parishes: {len(parishes)}")

# ---------------------------------------------------------------------------
# 2. Buffer bus stops at 800 m → dissolve → unified coverage surface
# ---------------------------------------------------------------------------
print("=== 2. 800 m buffer + dissolve ===")
buffers = gdf_stops.copy()
buffers["geometry"] = gdf_stops.geometry.buffer(800)          # metres (EPSG:3763)
coverage_union = buffers.geometry.union_all()                  # single polygon
print("  Coverage surface computed.")

# ---------------------------------------------------------------------------
# 3. Coverage ratio per parish  (intersection area / parish area)
# ---------------------------------------------------------------------------
print("=== 3. Coverage ratio per parish ===")
parishes["coverage_area_m2"] = (
    parishes.geometry
    .intersection(coverage_union)
    .area
)
parishes["parish_area_m2"] = parishes.geometry.area
parishes["coverage_ratio"] = (
    parishes["coverage_area_m2"] / parishes["parish_area_m2"]
).clip(0, 1)

# ---------------------------------------------------------------------------
# 4. GTFS service frequency per stop  (07:00–21:00)
# ---------------------------------------------------------------------------
print("=== 4. GTFS frequency 07:00–21:00 ===")
stop_times = pd.read_csv(
    CMET / "stop_times.txt",
    usecols=["stop_id", "departure_time"],
    dtype={"stop_id": str},
)
# Convert "HH:MM:SS" strings to timedelta; GTFS allows >24 h for overnight trips
stop_times["departure_td"] = pd.to_timedelta(stop_times["departure_time"])
t_start = pd.Timedelta("07:00:00")
t_end = pd.Timedelta("21:00:00")
daytime = stop_times[
    (stop_times["departure_td"] >= t_start)
    & (stop_times["departure_td"] <= t_end)
]
freq_per_stop = (
    daytime.groupby("stop_id")
    .size()
    .rename("n_departures")
    .reset_index()
)
print(f"  Daytime departures counted for {len(freq_per_stop)} stops.")

# Join frequency back to stops GeoDataFrame
gdf_stops = gdf_stops.merge(
    freq_per_stop, on="stop_id", how="left"
)
gdf_stops["n_departures"] = gdf_stops["n_departures"].fillna(0)

# ---------------------------------------------------------------------------
# 5. Aggregate mean frequency per parish  (spatial join stops → parishes)
# ---------------------------------------------------------------------------
print("=== 5. Mean frequency per parish ===")
stops_in_parishes = gpd.sjoin(
    gdf_stops[["stop_id", "n_departures", "geometry"]],
    parishes[["DTMNFR21", "geometry"]],
    how="left",
    predicate="within",
)
mean_freq = (
    stops_in_parishes.groupby("DTMNFR21")["n_departures"]
    .mean()
    .rename("mean_departures")
    .reset_index()
)
parishes = parishes.merge(mean_freq, on="DTMNFR21", how="left")
parishes["mean_departures"] = parishes["mean_departures"].fillna(0)

# ---------------------------------------------------------------------------
# 6. Save enriched parishes
# ---------------------------------------------------------------------------
print("=== 6. Saving parishes_enriched.gpkg ===")
parishes.to_file(PROCESSED / "parishes_enriched.gpkg", driver="GPKG")
print("Done.")
print(parishes[["DTMNFR21", "coverage_ratio", "mean_departures"]].describe())
