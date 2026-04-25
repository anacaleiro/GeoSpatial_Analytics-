"""
03_analysis.py - Composite accessibility index + Jenks criticality classes.

Composite index (elderly share as demographic weight, range 0-1, higher = more critical):
  transit_deficit = ((1 - coverage_norm) + (1 - frequency_norm)) / 2
  index = elderly_share_norm * transit_deficit

Reads:  data/processed/parishes_enriched.gpkg
Writes: data/processed/parishes_final.gpkg
"""

from pathlib import Path

import geopandas as gpd
import mapclassify
import numpy as np

PROJECT = Path(__file__).resolve().parent.parent
PROCESSED = PROJECT / "data" / "processed"


# 1. Load
print("=== 1. Loading parishes ===")
parishes = gpd.read_file(PROCESSED / "parishes_enriched.gpkg")
print(f"  Parishes loaded: {len(parishes)}")
 
# 2. Elderly share
print("=== 2. Elderly share ===")
parishes["elderly_share"] = np.where(
    parishes["N_INDIVIDUOS"] > 0,
    parishes["N_INDIVIDUOS_65_OU_MAIS"] / parishes["N_INDIVIDUOS"],
    0.0,
)
print(parishes["elderly_share"].describe())


# 3. Min-Max normalise
print("=== 3. Min-Max normalisation ===")

def minmax(series):
    lo, hi = series.min(), series.max()
    if hi == lo:
        return series * 0.0
    return (series - lo) / (hi - lo)

parishes["elderly_share_norm"]   = minmax(parishes["elderly_share"])
parishes["coverage_ratio_norm"]  = minmax(parishes["coverage_ratio"])
parishes["mean_departures_norm"] = minmax(parishes["mean_departures"])

 
# 4. Composite index (elderly share as demographic weight)
print("=== 4. Composite index ===")
transit_deficit = (
    (1 - parishes["coverage_ratio_norm"])
    + (1 - parishes["mean_departures_norm"])
) / 2.0
parishes["composite_index"] = parishes["elderly_share_norm"] * transit_deficit
print(parishes["composite_index"].describe())


# 5. Jenks natural breaks -> 4 criticality classes
print("=== 5. Jenks natural breaks (k=4) ===")
classifier = mapclassify.NaturalBreaks(parishes["composite_index"], k=4)
print("  Breaks:", classifier.bins)
print("  Counts:", classifier.counts)

# classifier.yb gives integer bin labels (0 = least, 3 = most critical)
parishes["criticality_class"] = classifier.yb
label_map = {0: "Low", 1: "Moderate", 2: "High", 3: "Critical"}
parishes["criticality_label"] = parishes["criticality_class"].map(label_map)
print(parishes["criticality_label"].value_counts())

# 6. Rank and save
parishes = parishes.sort_values("composite_index", ascending=False).reset_index(drop=True)
parishes["rank"] = parishes.index + 1

print("=== 6. Saving parishes_final.gpkg ===")
parishes.to_file(PROCESSED / "parishes_final.gpkg", driver="GPKG")
print("Done.")
