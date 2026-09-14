#!/usr/bin/env python3

import argparse
from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pandas as pd
import scienceplots  # noqa: F401  (referenced by plt.style.use)
from cycler import cycler

# Named color palette presets, shared with plot_histogram.py and the GUI
# (app.py) so a graph looks identical everywhere. A palette is just a list of
# colors used for the automatic color cycle.
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


# ==================== Edit the settings below ====================

CSV_PATH = Path("input.csv")            # Input CSV file

SERIES = {
    "Series1": {},
    "Series2": {},
}
# Series to plot. Key: CSV column name (plotted in this order). Value: dict of
# per-series overrides.
# Allowed keys: label, color, linestyle, linewidth, marker, markersize
# Any key left unset falls back to the DEFAULT_* value below. If color is left
# unset, colors are assigned automatically from PALETTE.
# Example:
# SERIES = {
#     "Series1": {"label": "Series 1", "color": "tab:red", "marker": "s"},
#     "Series2": {"linestyle": "--", "linewidth": 0.5},
# }

XLABEL = None                          # X-axis label. None = inferred from the data
YLABEL = "None"                        # Y-axis label

XMIN, XMAX = None, None                # X-axis range (None = inferred from the data)
YMIN, YMAX = None, None                # Y-axis range (None = inferred from the data)

XSCALE = "linear"                      # X-axis scale ("linear" or "log")
YSCALE = "linear"                      # Y-axis scale ("linear" or "log")

DEFAULT_LINESTYLE = "-"                # Default line style when a series has no override
DEFAULT_LINEWIDTH = 1.0                # Default line width (0 for markers only)
DEFAULT_MARKER = "o"                   # Default marker shape when a series has no override
DEFAULT_MARKERSIZE = 4                 # Default marker size when a series has no override

STYLE = ["science", "ieee"]            # scienceplots style
PALETTE = PALETTES["tableau"]          # Color cycle: a list of colors, one of PALETTES[...],
                                        # or None to use STYLE's own colors unmodified

LEGEND_LOC = "best"                    # Legend location (matplotlib loc string), or None to hide it
LEGEND_NCOL = 1                        # Number of legend columns (< number of series wraps into multiple rows)
LEGEND_OUTSIDE = False                 # Place the legend below the plot instead of inside it

WIDTH_RATIO, HEIGHT_RATIO = None, None  # Aspect ratio as two numbers (e.g. 4, 3 for 4:3).
                                         # Keeps STYLE's figure width and scales the height to match.
                                         # None, None = use STYLE's own figure size unmodified
GRID = False                            # Show a background grid
TICK_FONTSIZE = None                    # Tick label font size. None = STYLE's own size

OUTPUT = None                          # Output file name. None = <CSV_PATH>_plot.pdf
DPI = 600                              # Output image DPI

# ===================================================================


_UNSET = object()  # sentinel used to detect whether a CLI argument was passed


def parse_args():
    parser = argparse.ArgumentParser(
        description="Plot selected series from a CSV file. Any option left unset falls "
                    "back to the hardcoded value at the top of this file.",
    )
    parser.add_argument("csv", type=Path, nargs="?", default=_UNSET, help=f"Input CSV file (default: {CSV_PATH})")
    parser.add_argument(
        "--series", "-s", nargs="+", default=_UNSET,
        help="Series to plot (CSV column names), plotted in this order. "
             "Per-series overrides from the SERIES dict are used when present",
    )
    parser.add_argument("--xlabel", default=_UNSET, help="X-axis label")
    parser.add_argument("--ylabel", default=_UNSET, help="Y-axis label")
    parser.add_argument("--xmin", type=float, default=_UNSET, help="X-axis minimum")
    parser.add_argument("--xmax", type=float, default=_UNSET, help="X-axis maximum")
    parser.add_argument("--ymin", type=float, default=_UNSET, help="Y-axis minimum")
    parser.add_argument("--ymax", type=float, default=_UNSET, help="Y-axis maximum")
    parser.add_argument("--xscale", choices=["linear", "log"], default=_UNSET, help="X-axis scale")
    parser.add_argument("--yscale", choices=["linear", "log"], default=_UNSET, help="Y-axis scale")
    parser.add_argument("--linestyle", default=_UNSET, help="Default line style when a series has no override")
    parser.add_argument("--linewidth", type=float, default=_UNSET, help="Default line width when a series has no override")
    parser.add_argument("--marker", default=_UNSET, help="Default marker shape when a series has no override")
    parser.add_argument("--markersize", type=float, default=_UNSET, help="Default marker size when a series has no override")
    parser.add_argument("--style", nargs="+", default=_UNSET, help="scienceplots style")
    parser.add_argument(
        "--palette", choices=[*PALETTES, "none"], default=_UNSET,
        help="Color palette preset ('none' = use STYLE's own colors unmodified)",
    )
    parser.add_argument(
        "--legend-loc", choices=[*LEGEND_LOCS, "none"], default=_UNSET,
        help="Legend location ('none' hides the legend)",
    )
    parser.add_argument("--legend-ncol", type=int, default=_UNSET, help="Number of legend columns")
    parser.add_argument(
        "--legend-outside", dest="legend_outside", action="store_true", default=_UNSET,
        help="Place the legend below the plot instead of inside it",
    )
    parser.add_argument("--width-ratio", type=float, default=_UNSET, help="Aspect ratio width component")
    parser.add_argument("--height-ratio", type=float, default=_UNSET, help="Aspect ratio height component")
    parser.add_argument("--grid", action="store_true", default=_UNSET, help="Show a background grid")
    parser.add_argument("--tick-fontsize", type=float, default=_UNSET, help="Tick label font size")
    parser.add_argument("--output", "-o", type=Path, default=_UNSET, help="Output file name")
    parser.add_argument("--dpi", type=int, default=_UNSET, help="Output image DPI")
    return parser.parse_args()


def resolve(cli_value, hardcoded_value):
    return hardcoded_value if cli_value is _UNSET else cli_value


def resolve_palette(cli_value, hardcoded_palette):
    """Like resolve(), but the CLI value is a PALETTES key (or 'none') rather
    than a literal color list, so it needs mapping before use.
    """
    if cli_value is _UNSET:
        return hardcoded_palette
    return None if cli_value == "none" else PALETTES[cli_value]


def resolve_legend_loc(cli_value, hardcoded_loc):
    if cli_value is _UNSET:
        return hardcoded_loc
    return None if cli_value == "none" else cli_value


def select_series(series, selected_columns):
    """When --series is given on the CLI, restrict/reorder to that subset.
    Column names not present in the SERIES dict are treated as having no
    per-series overrides (defaults only).
    """
    if selected_columns is None:
        return series
    return {col: series.get(col, {}) for col in selected_columns}


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


def apply_legend(ax, loc, ncol, outside):
    """Draw the legend the same way everywhere (CLI scripts and the GUI). loc=None hides it."""
    if loc is None:
        return
    kwargs = {"frameon": False, "ncol": ncol}
    if outside:
        kwargs.update(loc="upper center", bbox_to_anchor=(0.5, -0.15))
    else:
        kwargs["loc"] = loc
    ax.legend(**kwargs)


def main():
    args = parse_args()

    csv_path = resolve(args.csv, CSV_PATH)
    series = select_series(SERIES, resolve(args.series, None))
    xlabel = resolve(args.xlabel, XLABEL)
    ylabel = resolve(args.ylabel, YLABEL)
    xmin = resolve(args.xmin, XMIN)
    xmax = resolve(args.xmax, XMAX)
    ymin = resolve(args.ymin, YMIN)
    ymax = resolve(args.ymax, YMAX)
    xscale = resolve(args.xscale, XSCALE)
    yscale = resolve(args.yscale, YSCALE)
    default_linestyle = resolve(args.linestyle, DEFAULT_LINESTYLE)
    default_linewidth = resolve(args.linewidth, DEFAULT_LINEWIDTH)
    default_marker = resolve(args.marker, DEFAULT_MARKER)
    default_markersize = resolve(args.markersize, DEFAULT_MARKERSIZE)
    style = resolve(args.style, STYLE)
    palette = resolve_palette(args.palette, PALETTE)
    legend_loc = resolve_legend_loc(args.legend_loc, LEGEND_LOC)
    legend_ncol = resolve(args.legend_ncol, LEGEND_NCOL)
    legend_outside = resolve(args.legend_outside, LEGEND_OUTSIDE)
    width_ratio = resolve(args.width_ratio, WIDTH_RATIO)
    height_ratio = resolve(args.height_ratio, HEIGHT_RATIO)
    grid = resolve(args.grid, GRID)
    tick_fontsize = resolve(args.tick_fontsize, TICK_FONTSIZE)
    output = resolve(args.output, OUTPUT)
    dpi = resolve(args.dpi, DPI)

    df = pd.read_csv(csv_path)
    x_col = df.columns[0]

    unknown = [s for s in series if s not in df.columns[1:]]
    if unknown:
        available = ", ".join(df.columns[1:])
        raise SystemExit(f"Unknown series: {unknown}\nAvailable series: {available}")

    defaults = {
        "color": None,
        "linestyle": default_linestyle,
        "linewidth": default_linewidth,
        "marker": default_marker,
        "markersize": default_markersize,
    }

    apply_style(style, palette)
    fig, ax = plt.subplots(figsize=compute_figsize(width_ratio, height_ratio))

    for col, overrides in series.items():
        spec = merge_series_spec(col, overrides, defaults)
        ax.plot(
            df[x_col], df[col],
            marker=spec["marker"], markersize=spec["markersize"],
            linewidth=spec["linewidth"], linestyle=spec["linestyle"],
            label=spec["label"], color=spec["color"],
        )

    ax.set_xlabel(xlabel if xlabel is not None else x_col)
    ax.set_ylabel(ylabel)
    ax.set_xscale(xscale)
    ax.set_yscale(yscale)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    apply_legend(ax, legend_loc, legend_ncol, legend_outside)
    if grid:
        ax.grid(True, alpha=0.3)
    if tick_fontsize is not None:
        ax.tick_params(labelsize=tick_fontsize)

    fig.tight_layout()

    output = output if output is not None else csv_path.with_name(f"{csv_path.stem}_plot.pdf")
    fig.savefig(output, dpi=dpi)
    print(f"saved: {output}")


if __name__ == "__main__":
    main()
