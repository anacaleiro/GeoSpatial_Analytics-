import geopandas as gpd                                    
from pathlib import Path    

gdf = gpd.read_file("data/processed/health_facilities.gpkg")

print(gdf[["name", "amenity"]].to_string())


import pandas as pd
from pathlib import Path

CMET = Path(r"C:\Users\X1605\Documents\GitHub\GeoSpatial_Analytics-\CMET")

stops = pd.read_csv(CMET / "stops.txt", dtype={"stop_id": str})
stop_times = pd.read_csv(CMET / "stop_times.txt", dtype={"stop_id": str},
                            usecols=["stop_id",
  "departure_time"])

orphan_stops = stops[~stops["stop_id"].isin(stop_times["stop_id"])]
print(f"Stops with no entries in stop_times at all:{len(orphan_stops)}")
print(orphan_stops[["stop_id", "stop_name"]].to_string())


bgri = gpd.read_file(r"C:\Users\X1605\Documents\GitHub\GeoSpatial_Analytics-\Census\BGRI21_CONT\BGRI21_CONT.gpkg")
print(bgri.columns.tolist())

parishes = gpd.read_file(r"C:\Users\X1605\Documents\GitHub\GeoSpatial_Analytics-\data\processed\parishes_final.gpkg")
print(parishes["DTMNFR21"].sort_values().tolist())

import geopandas as gpd                                               
from pathlib import Path

gpkg = r"C:\Users\X1605\Documents\GitHub\GeoSpatial_Analytics-\Census\BGRI21_CONT\BGRI21_CONT.gpkg"
print("Layers:", gpd.list_layers(gpkg))

census_dir = Path(r"C:\Users\X1605\Documents\GitHub\GeoSpatial_Analytics-\Census")
for f in census_dir.rglob("*"):
    if f.is_file():
        print(f.relative_to(census_dir))

import osmnx as ox                                         
import geopandas as gpd

gdf = ox.features_from_place(
      "Lisboa, Portugal",
      tags={"boundary": "administrative", "admin_level": "8"}
  )
cols = [c for c in ["name", "ref:ine"] if c in gdf.columns]
print(gdf[cols].dropna(subset=["name"]).to_string())
