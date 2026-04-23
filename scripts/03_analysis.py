"""
03_analysis.py — Composite accessibility index + Jenks criticality classes.

Reads:  data/processed/parishes_enriched.gpkg
Writes: data/processed/parishes_final.gpkg
"""

from pathlib import Path

import geopandas as gpd
import mapclassify
import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT = Path(__file__).resolve().parent.parent
PROCESSED = PROJECT / "data" / "processed"

# ---------------------------------------------------------------------------
# 1. Load enriched parishes
# ---------------------------------------------------------------------------
print("=== 1. Loading parishes ===")
parishes = gpd.read_file(PROCESSED / "parishes_enriched.gpkg")
print(f"  Parishes loaded: {len(parishes)}")

# ---------------------------------------------------------------------------
# 2. Elderly population share
# ---------------------------------------------------------------------------
print("=== 2. Elderly share ===")
# Guard against zero-population parishes
parishes["elderly_share"] = np.where(
    parishes["N_INDIVIDUOS"] > 0,
    parishes["N_INDIVIDUOS_65_OU_MAIS"] / parishes["N_INDIVIDUOS"],
    0.0,
)
print(parishes["elderly_share"].describe())

# ---------------------------------------------------------------------------
# 3. Min-Max normalise the three variables
# ---------------------------------------------------------------------------
print("=== 3. Min-Max normalisation ===")

def minmax(series):
    lo, hi = series.min(), series.max()
    if hi == lo:
        return series * 0.0  # constant → all zeros
    return (series - lo) / (hi - lo)

parishes["elderly_share_norm"]   = minmax(parishes["elderly_share"])
parishes["coverage_ratio_norm"]  = minmax(parishes["coverage_ratio"])
parishes["mean_departures_norm"] = minmax(parishes["mean_departures"])

# ---------------------------------------------------------------------------
# 4. Composite index (equal weights)
#    High index = high vulnerability:
#      more elderly   +  less coverage  +  less frequency
# ---------------------------------------------------------------------------
print("=== 4. Composite index (equal weights) ===")
parishes["composite_index"] = (
    parishes["elderly_share_norm"]
    + (1 - parishes["coverage_ratio_norm"])
    + (1 - parishes["mean_departures_norm"])
) / 3.0

print(parishes["composite_index"].describe())

# ---------------------------------------------------------------------------
# 5. Jenks natural breaks -> 4 criticality classes
# ---------------------------------------------------------------------------
print("=== 5. Jenks natural breaks (k=4) ===")
classifier = mapclassify.NaturalBreaks(parishes["composite_index"], k=4)
print("  Breaks:", classifier.bins)
print("  Counts:", classifier.counts)

# classifier.yb gives integer bin labels (0..k-1) in the same row order
parishes["criticality_class"] = classifier.yb
# Label 0 = least critical, 3 = most critical
label_map = {0: "Low", 1: "Moderate", 2: "High", 3: "Critical"}
parishes["criticality_label"] = parishes["criticality_class"].map(label_map)

print(parishes["criticality_label"].value_counts())

# ---------------------------------------------------------------------------
# 6. Sort by criticality (most critical first) and rank
# ---------------------------------------------------------------------------
parishes = parishes.sort_values("composite_index", ascending=False).reset_index(drop=True)
parishes["rank"] = parishes.index + 1

# ---------------------------------------------------------------------------
# 7. Save
# ---------------------------------------------------------------------------
print("=== 7. Saving parishes_final.gpkg ===")
parishes.to_file(PROCESSED / "parishes_final.gpkg", driver="GPKG")
print("Done.")
