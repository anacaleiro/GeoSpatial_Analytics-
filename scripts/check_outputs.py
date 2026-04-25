"""
check_outputs.py - Validate outputs of 01_preprocess.py and 02_transform.py.

Run after both scripts:
    python scripts/01_preprocess.py
    python scripts/02_transform.py
    python scripts/check_outputs.py
"""

from pathlib import Path
import geopandas as gpd

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"
CRS = "EPSG:3763"
EXPECTED_PARISHES = 24
PASS, FAIL = "  PASS", "  FAIL"

errors = []

def check(condition, label, detail=""):
    status = PASS if condition else FAIL
    print(f"{status}  {label}" + (f" — {detail}" if detail else ""))
    if not condition:
        errors.append(label)


# 01_preprocess outputs
print("\n=== bus_stops.gpkg ===")
f = PROCESSED / "bus_stops.gpkg"
check(f.exists(), "file exists")
if f.exists():
    stops = gpd.read_file(f)
    check(stops.crs.to_epsg() == 3763, "CRS is EPSG:3763", stops.crs)
    check(len(stops) > 0, "has rows", f"{len(stops)} stops")
    check(stops.geometry.notna().all(), "no null geometries")
    check(stops.geometry.is_valid.all(), "all geometries valid")
    check("stop_id" in stops.columns, "stop_id column present")
    # Lisbon approx bbox in EPSG:3763: x roughly -97000 to -82000, y roughly -106000 to -93000
    bounds = stops.total_bounds  # minx, miny, maxx, maxy
    in_lisbon = (-100_000 < bounds[0]) and (bounds[2] < -78_000)
    check(in_lisbon, "stops within Lisbon bbox", f"x: {bounds[0]:.0f} to {bounds[2]:.0f}")

print("\n=== parishes.gpkg ===")
f = PROCESSED / "parishes.gpkg"
check(f.exists(), "file exists")
if f.exists():
    parishes = gpd.read_file(f)
    check(parishes.crs.to_epsg() == 3763, "CRS is EPSG:3763", parishes.crs)
    check(len(parishes) == EXPECTED_PARISHES, f"exactly {EXPECTED_PARISHES} parishes", f"found {len(parishes)}")
    check(parishes.geometry.notna().all(), "no null geometries")
    check(parishes.geometry.is_valid.all(), "all geometries valid")
    check("DTMNFR21" in parishes.columns, "parish code column present")
    census_cols = [
        "N_INDIVIDUOS", "N_INDIVIDUOS_65_OU_MAIS", "N_INDIVIDUOS_0_14",
        "N_INDIVIDUOS_15_24", "N_INDIVIDUOS_25_64",
    ]
    for col in census_cols:
        check(col in parishes.columns, f"census column: {col}")
    check((parishes["N_INDIVIDUOS"] > 0).all(), "all parishes have population")

print("\n=== health_facilities.gpkg ===")
f = PROCESSED / "health_facilities.gpkg"
check(f.exists(), "file exists")
if f.exists():
    health = gpd.read_file(f)
    check(health.crs.to_epsg() == 3763, "CRS is EPSG:3763", health.crs)
    check(len(health) > 0, "has rows", f"{len(health)} facilities")
    check(health.geometry.notna().all(), "no null geometries")
    check(health.geometry.geom_type.eq("Point").all(), "all geometries are points")
    if "amenity" in health.columns:
        unexpected = set(health["amenity"].unique()) - {"hospital", "clinic"}
        check(len(unexpected) == 0, "only hospital/clinic amenity tags", f"unexpected: {unexpected}")

 
# 02_transform output
print("\n=== parishes_enriched.gpkg ===")
f = PROCESSED / "parishes_enriched.gpkg"
check(f.exists(), "file exists")
if f.exists():
    enriched = gpd.read_file(f)
    check(enriched.crs.to_epsg() == 3763, "CRS is EPSG:3763", enriched.crs)
    check(len(enriched) == EXPECTED_PARISHES, f"exactly {EXPECTED_PARISHES} parishes", f"found {len(enriched)}")
    check("coverage_ratio" in enriched.columns, "coverage_ratio column present")
    check("mean_departures" in enriched.columns, "mean_departures column present")
    check(enriched["coverage_ratio"].between(0, 1).all(), "coverage_ratio in [0, 1]",
          f"min={enriched['coverage_ratio'].min():.3f} max={enriched['coverage_ratio'].max():.3f}")
    check((enriched["mean_departures"] >= 0).all(), "mean_departures non-negative",
          f"min={enriched['mean_departures'].min():.1f} max={enriched['mean_departures'].max():.1f}")
    check(enriched["coverage_ratio"].notna().all(), "no nulls in coverage_ratio")
    check(enriched["mean_departures"].notna().all(), "no nulls in mean_departures")
    check((enriched["coverage_ratio"] > 0).any(), "at least one parish has transit coverage")


# Summarys
print(f"\n{'='*45}")
if errors:
    print(f"FAILED ({len(errors)} checks):")
    for e in errors:
        print(f"  - {e}")
else:
    print("All checks passed.")
