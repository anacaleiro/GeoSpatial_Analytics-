"""
01_preprocess.py - Load, clean, and save the three raw datasets.

Outputs (EPSG:3763, GeoPackage):
  data/processed/bus_stops.gpkg         - GTFS stops clipped to Lisbon
  data/processed/parishes.gpkg          - Census stats dissolved to parish level
  data/processed/health_facilities.gpkg - OSMnx hospitals/clinics as points
"""

import sys
import io

# Force UTF-8 output so print() never trips on Unicode in filenames
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pathlib import Path

import geopandas as gpd
import osmnx as ox
import pandas as pd

# Paths
PROJECT = Path(__file__).resolve().parent.parent
CMET = PROJECT / "CMET"
BGRI_GPKG = PROJECT / "Census" / "BGRI21_CONT" / "BGRI21_CONT.gpkg"
PROCESSED = PROJECT / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

CRS = "EPSG:3763"
LISBON_MUN_CODE = "1106"

# 1. GTFS bus stops -> GeoDataFrame
print("=== 1. GTFS bus stops ===")
stops_df = pd.read_csv(CMET / "stops.txt", dtype={"stop_id": str})
gdf_stops = gpd.GeoDataFrame(
    stops_df,
    geometry=gpd.points_from_xy(stops_df["stop_lon"], stops_df["stop_lat"]),
    crs="EPSG:4326",
).to_crs(CRS)
print(f"  Total stops in CMET: {len(gdf_stops)}")

# 2. INE Census + BGRI polygons -> parish-level GeoDataFrame
print("=== 2. BGRI census polygons -> parishes ===")
bgri = gpd.read_file(BGRI_GPKG)  # already EPSG:3763
lisbon_bgri = bgri[bgri["DTMN21"] == LISBON_MUN_CODE].copy()
print(f"  Lisbon census subsections: {len(lisbon_bgri)}")

# Lisbon municipality boundary 
lisbon_boundary = lisbon_bgri.dissolve()

# Dissolve subsections -> parish polygons, summing population variables
pop_cols = [
    "N_INDIVIDUOS",
    "N_INDIVIDUOS_65_OU_MAIS",
    "N_INDIVIDUOS_0_14",
    "N_INDIVIDUOS_15_24",
    "N_INDIVIDUOS_25_64",
    "N_INDIVIDUOS_H",
    "N_INDIVIDUOS_M",
    "N_AGREGADOS_DOMESTICOS_PRIVADOS",
    "N_ALOJAMENTOS_FAMILIARES",
]
PARISH_NAMES = {
    "110601": "Ajuda",
    "110602": "Alcântara",
    "110607": "Beato",
    "110608": "Benfica",
    "110610": "Campolide",
    "110611": "Carnide",
    "110618": "Lumiar",
    "110621": "Marvila",
    "110633": "Olivais",
    "110639": "São Domingos de Benfica",
    "110654": "Alvalade",
    "110655": "Areeiro",
    "110656": "Arroios",
    "110657": "Avenidas Novas",
    "110658": "Belém",
    "110659": "Campo de Ourique",
    "110660": "Estrela",
    "110661": "Misericórdia",
    "110662": "Parque das Nações",
    "110663": "Penha de França",
    "110664": "Santa Clara",
    "110665": "Santa Maria Maior",
    "110666": "Santo António",
    "110667": "São Vicente",
}

agg = {col: "sum" for col in pop_cols}
parishes = (
    lisbon_bgri
    .dissolve(by="DTMNFR21", aggfunc=agg)
    .reset_index()
    [["DTMNFR21"] + pop_cols + ["geometry"]]
)
parishes["parish_name"] = parishes["DTMNFR21"].map(PARISH_NAMES)
print(f"  Parishes (freguesias): {len(parishes)}")


# 3. OSMnx health facilities -> clip to Lisbon
print("=== 3. OSMnx health facilities ===")
# OSMnx expects WGS84 geometry
lisbon_geom_4326 = lisbon_boundary.to_crs("EPSG:4326").geometry.iloc[0]

tags = {"amenity": ["hospital", "clinic"]}
try:
    gdf_health_raw = ox.features_from_polygon(lisbon_geom_4326, tags=tags)
    # Reproject to EPSG:3763 then take centroids (more accurate in projected CRS)
    gdf_health = gdf_health_raw.to_crs(CRS).copy()
    gdf_health["geometry"] = gdf_health.geometry.centroid
    gdf_health = gdf_health.reset_index(drop=True)
    keep = [c for c in ["amenity", "name", "geometry"] if c in gdf_health.columns]
    gdf_health = gpd.GeoDataFrame(gdf_health[keep], crs=CRS)
    print(f"  Health facilities found: {len(gdf_health)}")
except Exception as exc:
    print(f"  WARNING: OSMnx query failed ({exc}). Saving empty layer.")
    gdf_health = gpd.GeoDataFrame(
        columns=["amenity", "name", "geometry"],
        geometry="geometry",
        crs=CRS,
    )
 
# 4. Clip bus stops to Lisbon boundary 
print("=== 4. Clip stops to Lisbon ===")
lisbon_poly = lisbon_boundary.geometry.union_all()
gdf_stops_lisbon = gdf_stops[gdf_stops.geometry.within(lisbon_poly)].copy()
print(f"  Stops within Lisbon: {len(gdf_stops_lisbon)}")

 
# 5. Save GeoPackages 
print("=== 5. Saving GeoPackages ===")
gdf_stops_lisbon.to_file(PROCESSED / "bus_stops.gpkg", driver="GPKG")
print("  bus_stops.gpkg saved")
parishes.to_file(PROCESSED / "parishes.gpkg", driver="GPKG")
print("  parishes.gpkg saved")
gdf_health.to_file(PROCESSED / "health_facilities.gpkg", driver="GPKG")
print("  health_facilities.gpkg saved")
print("Done.")

