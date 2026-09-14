#!/usr/bin/env python3

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import scienceplots  # noqa: F401  (referenced by plt.style.use)

from plot_csv import (
    _UNSET,
    LEGEND_LOCS,
    PALETTES,
    apply_legend,
    apply_style,
    compute_figsize,
    merge_series_spec,
    resolve,
    resolve_legend_loc,
    resolve_palette,
    select_series,
)


# ==================== Edit the settings below ====================

CSV_PATH = Path("input.csv")            # Input CSV file

SERIES = {
    "Series1": {},
    "Series2": {},
    "Series3": {},
}
# Series to turn into histograms. Key: CSV column name. Value: dict of
# per-series overrides.
# Allowed keys: label, color, alpha
# Any key left unset falls back to the DEFAULT_* value below. If color is left
# unset, colors are assigned automatically from PALETTE.
# Example:
# SERIES = {
#     "Series1": {"label": "Series 1", "color": "tab:red", "alpha": 0.4},
#     "Series2": {},
# }

XLABEL = "X"                           # X-axis label
YLABEL = "Y"                           # Y-axis label

XMIN, XMAX = None, None                # X-axis (bin) range (None = inferred from the data)
YMIN, YMAX = None, None                # Y-axis range (None = inferred from the data)

XSCALE = "linear"                      # X-axis scale ("linear" or "log")
YSCALE = "linear"                      # Y-axis scale ("linear" or "log")

N_BINS = 100                           # Number of bins
DEFAULT_ALPHA = 0.6                    # Default histogram transparency when a series has no override

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

OUTPUT = None                          # Output file name. None = <CSV_PATH>_hist.pdf
DPI = 600                              # Output image DPI

# ===================================================================


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build a histogram from CSV columns. Any option left unset falls "
                    "back to the hardcoded value at the top of this file.",
    )
    parser.add_argument("csv", type=Path, nargs="?", default=_UNSET, help=f"Input CSV file (default: {CSV_PATH})")
    parser.add_argument(
        "--series", "-s", nargs="+", default=_UNSET,
        help="Series to turn into histograms (CSV column names). "
             "Per-series overrides from the SERIES dict are used when present",
    )
    parser.add_argument("--xlabel", default=_UNSET, help="X-axis label")
    parser.add_argument("--ylabel", default=_UNSET, help="Y-axis label")
    parser.add_argument("--xmin", type=float, default=_UNSET, help="X-axis (bin) minimum")
    parser.add_argument("--xmax", type=float, default=_UNSET, help="X-axis (bin) maximum")
    parser.add_argument("--ymin", type=float, default=_UNSET, help="Y-axis minimum")
    parser.add_argument("--ymax", type=float, default=_UNSET, help="Y-axis maximum")
    parser.add_argument("--xscale", choices=["linear", "log"], default=_UNSET, help="X-axis scale")
    parser.add_argument("--yscale", choices=["linear", "log"], default=_UNSET, help="Y-axis scale")
    parser.add_argument("--bins", type=int, default=_UNSET, dest="n_bins", help="Number of bins")
    parser.add_argument("--alpha", type=float, default=_UNSET, help="Default histogram transparency when a series has no override")
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
    n_bins = resolve(args.n_bins, N_BINS)
    default_alpha = resolve(args.alpha, DEFAULT_ALPHA)
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

    unknown = [s for s in series if s not in df.columns]
    if unknown:
        available = ", ".join(df.columns)
        raise SystemExit(f"Unknown series: {unknown}\nAvailable series: {available}")

    columns = list(series)
    bin_min = xmin if xmin is not None else df[columns].min().min()
    bin_max = xmax if xmax is not None else df[columns].max().max()
    if xscale == "log":
        if bin_min <= 0:
            raise SystemExit(f"xmin must be positive when xscale is log (xmin={bin_min})")
        ratio = bin_max / bin_min
        bin_edges = [bin_min * ratio ** (i / n_bins) for i in range(n_bins + 1)]
    else:
        bin_edges = [bin_min + i * (bin_max - bin_min) / n_bins for i in range(n_bins + 1)]

    defaults = {"color": None, "alpha": default_alpha}

    apply_style(style, palette)
    fig, ax = plt.subplots(figsize=compute_figsize(width_ratio, height_ratio))

    for col, overrides in series.items():
        spec = merge_series_spec(col, overrides, defaults)
        ax.hist(df[col], bins=bin_edges, alpha=spec["alpha"], color=spec["color"], label=spec["label"])

    ax.set_xlabel(xlabel)
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

    output = output if output is not None else csv_path.with_name(f"{csv_path.stem}_hist.pdf")
    fig.savefig(output, dpi=dpi)
    print(f"saved: {output}")


if __name__ == "__main__":
    main()
