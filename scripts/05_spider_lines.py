"""
05_spider_lines.py - Straight lines from each parish centroid to its nearest
                     health facility.

Reads:  data/processed/parishes_final.gpkg
        data/processed/health_facilities.gpkg
Writes: data/processed/spider_lines.gpkg
"""

from pathlib import Path

import geopandas as gpd
from shapely.geometry import LineString

PROJECT = Path(__file__).resolve().parent.parent
PROCESSED = PROJECT / "data" / "processed"
CRS = "EPSG:3763"
 
# 1. Load
print("=== 1. Loading layers ===")
parishes = gpd.read_file(PROCESSED / "parishes_final.gpkg")
health = gpd.read_file(PROCESSED / "health_facilities.gpkg")
print(f"  Parishes: {len(parishes)}  |  Health facilities: {len(health)}")

# Ensure health facilities are points (centroids already computed in preprocess,
# but guard against polygon geometries just in case)
if not health.geometry.geom_type.eq("Point").all():
    health = health.copy()
    health["geometry"] = health.geometry.centroid

 
# 2. Parish centroids 
print("=== 2. Computing parish centroids ===")
centroids = parishes[
    ["DTMNFR21", "elderly_share", "mean_departures",
     "coverage_ratio", "composite_index", "criticality_label", "geometry"]
].copy()
centroids["geometry"] = parishes.geometry.centroid


# 3 & 4. Nearest facility per parish + distance
print("=== 3. Finding nearest health facility per parish ===")
matched = gpd.sjoin_nearest(
    centroids,
    health[["geometry"]].reset_index(drop=True),
    how="left",
    distance_col="distance_to_facility",
)

# sjoin_nearest can return duplicate rows on equidistant ties; keep first match
matched = matched.drop_duplicates(subset="DTMNFR21").reset_index(drop=True)

 
# 5. Build LineString from centroid to facility point
print("=== 4. Building spider lines ===")
health_geom = health["geometry"].reset_index(drop=True)
matched["facility_geom"] = matched["index_right"].map(health_geom)

matched["geometry"] = matched.apply(
    lambda row: LineString([row["geometry"], row["facility_geom"]]),
    axis=1,
)
matched = matched.drop(columns=["facility_geom", "index_right"])

# Rename to requested field names
spider = gpd.GeoDataFrame(
    matched.rename(columns={
        "DTMNFR21":          "parish_code",
        "mean_departures":   "mean_frequency",
        "composite_index":   "index_score",
        "criticality_label": "criticality_class",
    }),
    crs=CRS,
)

 
# 6. Save 
print("=== 5. Saving spider_lines.gpkg ===")
spider.to_file(PROCESSED / "spider_lines.gpkg", driver="GPKG")
print(f"  Saved {len(spider)} lines.")

 
# 7. Summary
print("\n--- 5 parishes with longest distance to nearest facility ---")
print(
    spider.nlargest(5, "distance_to_facility")[
        ["parish_code", "distance_to_facility", "criticality_class"]
    ].to_string(index=False)
)

print("\n--- 5 parishes with lowest mean frequency ---")
print(
    spider.nsmallest(5, "mean_frequency")[
        ["parish_code", "mean_frequency", "criticality_class"]
    ].to_string(index=False)
)
