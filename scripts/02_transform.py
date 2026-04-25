"""
02_transform.py - Spatial transformations: network isochrones, coverage ratio, frequency.

Reads:  data/processed/bus_stops.gpkg
        data/processed/parishes.gpkg
        CMET/stop_times.txt
Writes: data/processed/parishes_enriched.gpkg
"""

from pathlib import Path

import geopandas as gpd
import networkx as nx
import osmnx as ox
import pandas as pd
from shapely.geometry import MultiPoint, Point

PROJECT = Path(__file__).resolve().parent.parent
CMET = PROJECT / "CMET"
PROCESSED = PROJECT / "data" / "processed"
CRS = "EPSG:3763"


# 1. Load preprocessed layers
print("=== 1. Loading layers ===")
gdf_stops = gpd.read_file(PROCESSED / "bus_stops.gpkg")
parishes = gpd.read_file(PROCESSED / "parishes.gpkg")
print(f"  Stops: {len(gdf_stops)}  |  Parishes: {len(parishes)}")


# 2. Download Lisbon pedestrian street network
# Straight-line circular buffers overestimate reachable area by up to 57%
# compared to service areas constrained to the actual street network (Apparicio
# et al. 2008). Network isochrones derived from the OSMnx pedestrian graph
# reflect the real paths a pedestrian can take, giving a more accurate picture
# of which residents can realistically reach a bus stop within a 10-minute walk.
print("=== 2. Downloading Lisbon pedestrian network ===")
lisbon_poly_4326 = (
    parishes.dissolve().to_crs("EPSG:4326").geometry.iloc[0].buffer(0.009)
)  # ~1 km buffer avoids edge effects for stops near the municipal boundary
G = ox.graph_from_polygon(lisbon_poly_4326, network_type="walk")
G_proj = ox.project_graph(G, to_crs=CRS)
print(f"  Network nodes: {len(G_proj.nodes)}  |  edges: {len(G_proj.edges)}")


# 3. 800 m walk isochrones per stop (convex hull of reachable nodes)
print("=== 3. Network walk isochrones (800 m) ===")
nearest_nodes = ox.distance.nearest_nodes(
    G_proj,
    X=gdf_stops.geometry.x.values,
    Y=gdf_stops.geometry.y.values,
)

isochrone_polys = []
for i, nn in enumerate(nearest_nodes):
    sub = nx.ego_graph(G_proj, nn, radius=800, distance="length")
    pts = [Point(data["x"], data["y"]) for _, data in sub.nodes(data=True)]
    if len(pts) >= 3:
        poly = MultiPoint(pts).convex_hull
    else:
        # Too few reachable nodes to form a polygon; fall back to circular buffer
        poly = gdf_stops.geometry.iloc[i].buffer(800)
    isochrone_polys.append(poly)
    if (i + 1) % 50 == 0:
        print(f"  {i + 1}/{len(nearest_nodes)} stops processed")

gdf_isochrones = gpd.GeoDataFrame(geometry=isochrone_polys, crs=CRS)
print(f"  Isochrones generated: {len(gdf_isochrones)}")
gdf_isochrones.to_file(PROCESSED / "stop_isochrones.gpkg", driver="GPKG")
print("  Individual isochrones saved.")


# 4. Dissolve -> unified coverage surface 
print("=== 4. Dissolving isochrones ===")
coverage_union = gdf_isochrones.geometry.union_all()
print("  Coverage surface computed.")

 
# 5. Coverage ratio per parish (intersection area / parish area) 
print("=== 5. Coverage ratio per parish ===")
parishes["coverage_area_m2"] = parishes.geometry.intersection(coverage_union).area
parishes["parish_area_m2"] = parishes.geometry.area
parishes["coverage_ratio"] = (
    parishes["coverage_area_m2"] / parishes["parish_area_m2"]
).clip(0, 1)

 
# 6. GTFS service frequency per stop (07:00-21:00) 
print("=== 6. GTFS frequency 07:00-21:00 ===")
stop_times = pd.read_csv(
    CMET / "stop_times.txt",
    usecols=["stop_id", "departure_time"],
    dtype={"stop_id": str},
)
# pd.to_timedelta handles GTFS times beyond 24:00 (overnight services)
stop_times["departure_td"] = pd.to_timedelta(stop_times["departure_time"])
daytime = stop_times[
    stop_times["departure_td"].between(
        pd.Timedelta("07:00:00"), pd.Timedelta("21:00:00")
    )
]
freq_per_stop = daytime.groupby("stop_id").size().rename("n_departures").reset_index()
print(f"  Daytime departures counted for {len(freq_per_stop)} stops.")

gdf_stops = gdf_stops.merge(freq_per_stop, on="stop_id", how="left")
gdf_stops["n_departures"] = gdf_stops["n_departures"].fillna(0)


# 7. Mean frequency per parish (spatial join stops -> parishes)
print("=== 7. Mean frequency per parish ===")
stops_in_parishes = gpd.sjoin_nearest(
    gdf_stops[["stop_id", "n_departures", "geometry"]],
    parishes[["DTMNFR21", "geometry"]],
    how="left",
)
mean_freq = (
    stops_in_parishes.groupby("DTMNFR21")["n_departures"]
    .mean()
    .rename("mean_departures")
    .reset_index()
)
parishes = parishes.merge(mean_freq, on="DTMNFR21", how="left")
parishes["mean_departures"] = parishes["mean_departures"].fillna(0)

 
# 8. Save
print("=== 8. Saving parishes_enriched.gpkg ===")
parishes.to_file(PROCESSED / "parishes_enriched.gpkg", driver="GPKG")
print("Done.")
print(parishes[["DTMNFR21", "coverage_ratio", "mean_departures"]].describe())
