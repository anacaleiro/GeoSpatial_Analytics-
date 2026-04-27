"""
04_outputs.py - Produce 4 maps (300 DPI) and a ranked parishes CSV.

Maps:
  1. Elderly population share per parish
  2. Transit coverage ratio (800 m buffer)
  3. Mean service frequency (07:00-21:00)
  4. Composite accessibility index - main deliverable

Reads:  data/processed/parishes_final.gpkg
        data/processed/health_facilities.gpkg
Writes: outputs/map1_elderly.png
        outputs/map2_coverage.png
        outputs/map3_frequency.png
        outputs/map4_index.png
        outputs/ranked_parishes.csv
"""

import matplotlib
matplotlib.use("Agg")  # non-interactive; no display required

from pathlib import Path

import geopandas as gpd
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

PROJECT = Path(__file__).resolve().parent.parent
PROCESSED = PROJECT / "data" / "processed"
OUTPUTS = PROJECT / "outputs"
OUTPUTS.mkdir(parents=True, exist_ok=True)

DPI = 300
FIG_SIZE = (10, 10)

COLORBAR_STYLE = {
    "orientation": "vertical",
    "shrink": 0.6,
    "pad": 0.02,
}


# Load 
print("Loading data...")
parishes = gpd.read_file(PROCESSED / "parishes_final.gpkg")
health = gpd.read_file(PROCESSED / "health_facilities.gpkg")


def save_map(fig, name):
    path = OUTPUTS / name
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved: {path.name}")



# Map 1 - Elderly population share
print("=== Map 1: Elderly distribution ===")
fig, ax = plt.subplots(figsize=FIG_SIZE)
parishes.plot(
    ax=ax,
    column="elderly_share",
    cmap="YlOrRd",
    legend=True,
    legend_kwds={
        "label": "Share of residents aged 65+ (%)",
        "format": "{x:.0%}",
        **COLORBAR_STYLE,
    },
    edgecolor="white",
    linewidth=0.4,
    missing_kwds={"color": "lightgrey", "label": "No data"},
)
ax.set_title(
    "Elderly Population Distribution\nLisbon Parishes - Census 2021",
    fontsize=14, fontweight="bold", pad=12,
)
ax.set_axis_off()
save_map(fig, "map1_elderly.png")

#Map 2 - Transit coverage ratio
print("=== Map 2: Transit coverage ===")
fig, ax = plt.subplots(figsize=FIG_SIZE)
parishes.plot(
    ax=ax,
    column="coverage_ratio",
    cmap="Blues",
    legend=True,
    legend_kwds={
        "label": "Parish area within 800 m of a bus stop",
        "format": "{x:.0%}",
        **COLORBAR_STYLE,
    },
    edgecolor="white",
    linewidth=0.4,
)
ax.set_title(
    "Bus Stop Coverage Ratio (800 m walk)\nLisbon Parishes",
    fontsize=14, fontweight="bold", pad=12,
)
ax.set_axis_off()
save_map(fig, "map2_coverage.png")


# Map 3 - Mean service frequency
print("=== Map 3: Service frequency ===")
fig, ax = plt.subplots(figsize=FIG_SIZE)
parishes.plot(
    ax=ax,
    column="mean_departures",
    cmap="Greens",
    legend=True,
    legend_kwds={
        "label": "Mean departures per stop (07:00-21:00)",
        **COLORBAR_STYLE,
    },
    edgecolor="white",
    linewidth=0.4,
)
ax.set_title(
    "Bus Service Frequency\nMean Daytime Departures per Stop",
    fontsize=14, fontweight="bold", pad=12,
)
ax.set_axis_off()
save_map(fig, "map3_frequency.png")


# Map 4 - Composite index (main output)
print("=== Map 4: Accessibility index ===")
class_colours = {
    "Low":      "#1a9641",
    "Moderate": "#fdae61",
    "High":     "#d7191c",
    "Critical": "#7b0707",
}
parishes["_colour"] = parishes["criticality_label"].map(class_colours).fillna("#cccccc")

fig, ax = plt.subplots(figsize=FIG_SIZE)
parishes.plot(ax=ax, color=parishes["_colour"], edgecolor="white", linewidth=0.4)

if len(health) > 0:
    health.plot(ax=ax, color="navy", markersize=12, marker="+")

patches = [mpatches.Patch(facecolor=c, label=lbl) for lbl, c in class_colours.items()]
if len(health) > 0:
    patches.append(
        plt.Line2D([0], [0], color="navy", marker="+", linestyle="None",
                   markersize=8, label="Hospital/Clinic")
    )
ax.legend(handles=patches, title="Criticality Class", loc="lower left", fontsize=10)
ax.set_title(
    "Elderly Transit Accessibility Index\nLisbon Parishes - Jenks Natural Breaks (4 classes)",
    fontsize=14, fontweight="bold", pad=12,
)
ax.set_axis_off()
save_map(fig, "map4_index.png")
parishes.drop(columns=["_colour"], inplace=True)


# Ranked parishes table
print("=== Table: Ranked parishes ===")
table = (
    parishes[[
        "rank", "DTMNFR21", "parish_name", "criticality_label", "composite_index",
        "elderly_share", "coverage_ratio", "mean_departures",
        "N_INDIVIDUOS", "N_INDIVIDUOS_65_OU_MAIS",
    ]]
    .rename(columns={
        "DTMNFR21":              "parish_code",
        "criticality_label":     "criticality",
        "composite_index":       "index",
        "elderly_share":         "elderly_share_pct",
        "mean_departures":       "mean_daily_departures",
        "N_INDIVIDUOS":          "total_population",
        "N_INDIVIDUOS_65_OU_MAIS": "pop_65plus",
    })
    .assign(
        elderly_share_pct=lambda d: (d["elderly_share_pct"] * 100).round(1),
        index=lambda d: d["index"].round(4),
        coverage_ratio=lambda d: d["coverage_ratio"].round(4),
        mean_daily_departures=lambda d: d["mean_daily_departures"].round(1),
    )
)
table.to_csv(OUTPUTS / "ranked_parishes.csv", index=False)
print(f"  Saved ranked_parishes.csv ({len(table)} rows)")
print("\nAll outputs saved to outputs/")
