#!/usr/bin/env python3

import argparse
from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pandas as pd
import scienceplots  # noqa: F401  (referenced by plt.style.use)
from cycler import cycler


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
# unset, colors are assigned automatically from the Tableau palette.
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
    parser.add_argument("--output", "-o", type=Path, default=_UNSET, help="Output file name")
    parser.add_argument("--dpi", type=int, default=_UNSET, help="Output image DPI")
    return parser.parse_args()


def resolve(cli_value, hardcoded_value):
    return hardcoded_value if cli_value is _UNSET else cli_value


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


def apply_style(style):
    """Apply a scienceplots style (fonts, etc.) and set the default color cycle to the Tableau palette."""
    plt.style.use(style)
    plt.rcParams["axes.prop_cycle"] = cycler(color=list(mcolors.TABLEAU_COLORS.values()))


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

    apply_style(style)
    fig, ax = plt.subplots()

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
    ax.legend(frameon=False)

    fig.tight_layout()

    output = output if output is not None else csv_path.with_name(f"{csv_path.stem}_plot.pdf")
    fig.savefig(output, dpi=dpi)
    print(f"saved: {output}")


if __name__ == "__main__":
    main()
