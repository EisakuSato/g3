"""Shared plotting building blocks used across chart types and the GUI.

Everything here is presentation-agnostic (no Streamlit imports): color
palettes, scienceplots style application, figure sizing, and merging a
series's per-series overrides with its chart type's defaults. app.py handles
what's common to every chart type at the GUI level (data loading, axes,
legend, output); chart_types.py handles what differs per chart type (extra
per-series settings, the actual drawing code); this module is the common
ground both build on.
"""

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import scienceplots  # noqa: F401  (registers the "science"/"ieee"/... styles for plt.style.use)
from cycler import cycler

# Named color palette presets, shared by every chart type and the GUI so a
# graph looks identical everywhere. A palette is just a list of colors used
# for the automatic color cycle.
PALETTES = {
    "tableau": list(mcolors.TABLEAU_COLORS.values()),
    "okabe-ito": ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7", "#000000"],
    "set2": ["#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3", "#a6d854", "#ffd92f", "#e5c494", "#b3b3b3"],
    "dark2": ["#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#66a61e", "#e6ab02", "#a6761d", "#666666"],
    "grayscale": ["#000000", "#404040", "#808080", "#a6a6a6", "#d9d9d9"],
}

LEGEND_LOCS = [
    "best", "upper right", "upper left", "lower left", "lower right",
    "right", "center left", "center right", "lower center", "upper center", "center",
]


def merge_series_spec(col, overrides, defaults):
    """Merge per-series overrides into defaults to build the full set of plotting parameters."""
    spec = dict(defaults)
    spec["label"] = col
    spec.update(overrides)
    return spec


def apply_style(style, palette=None):
    """Apply a scienceplots style (fonts, etc.). If palette is given (a list of
    colors), it overrides the style's default color cycle; otherwise the
    style's own colors are left as-is.
    """
    plt.style.use(style)
    if palette is not None:
        plt.rcParams["axes.prop_cycle"] = cycler(color=palette)


def compute_figsize(width_ratio, height_ratio):
    """Return an explicit (width, height) figsize matching the width_ratio:height_ratio
    aspect ratio, keeping the currently active style's figure width. Returns None
    (meaning: leave the style's own figure size untouched) if either ratio is unset.
    """
    if not width_ratio or not height_ratio:
        return None
    base_width, _base_height = plt.rcParams["figure.figsize"]
    return (base_width, base_width * height_ratio / width_ratio)
