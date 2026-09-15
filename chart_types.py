"""Registry of chart type definitions.

app.py only handles the parts that are common to every chart type (data
loading, axes/style/legend/output). Everything that differs between chart
types (extra per-series settings, the actual drawing code) is kept in this
file.

To add a new chart type (scatter plot, CDF/CCDF, etc.), add one more
ChartType below, following the LINE / HIST pattern, and register it in
CHART_TYPES. app.py does not need to change.
"""

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd
import streamlit as st

from plotting import merge_series_spec

LINESTYLES = ["-", "--", "-.", ":", "None"]
MARKERS = ["o", "s", "^", "v", "D", "x", "+", "*", ".", "None"]

# Sample dataframes shown in the GUI to illustrate the CSV layout each chart type expects.
_XY_SAMPLE = pd.DataFrame({
    "x": [0, 1, 2, 3, 4],
    "SeriesA": [1.0, 1.5, 2.1, 2.0, 2.8],
    "SeriesB": [2.0, 1.8, 1.2, 1.6, 1.1],
})
_CATEGORY_SAMPLE = pd.DataFrame({
    "month": ["Jan.", "Feb.", "Mar."],
    "A": [1, 2, 3],
    "B": [2, 3, 4],
    "C": [4, 6, 8],
})
_VALUES_SAMPLE = pd.DataFrame({
    "SeriesA": [1.2, 2.3, 1.8, 2.5, 1.1, 2.0, 1.6],
    "SeriesB": [3.4, 2.9, 3.1, 3.6, 2.8, 3.0, 3.3],
})


@dataclass
class ChartType:
    key: str
    display: str
    uses_x_column: bool                           # True if the first column is used as the X axis (line, scatter, ...)
    needs_bins: bool                               # True if a bin count setting is needed (histogram, CDF, ...)
    series_defaults: dict                          # Defaults passed to merge_series_spec
    default_xlabel: Callable[[pd.DataFrame], str]  # df -> initial X-axis label
    default_ylabel: str
    series_fields: Callable[[str, str], dict]      # (col, key_prefix) -> extra per-series settings UI
    draw: Callable[[object, pd.DataFrame, dict, dict], None]  # (ax, df, series, ctx) -> None
    field_keys: dict                               # override key -> widget key suffix (see series_fields),
                                                    # used by app.py to restore a saved config into session_state
    csv_help: str                                  # one-line description of the expected CSV layout
    sample_df: pd.DataFrame                        # small example dataframe shown in the GUI
    categorical_x: bool = False                    # True if the X axis shows fixed category labels at integer
                                                    # positions (bar, ...) rather than a real numeric/log scale


# ==================== Line plot ====================

_LINE_FIELD_KEYS = {"linestyle": "ls", "linewidth": "lw", "marker": "marker", "markersize": "ms"}


def _line_series_fields(col: str, key_prefix: str) -> dict:
    c1, c2, c3, c4 = st.columns(4)
    return {
        "linestyle": c1.selectbox("Line style", LINESTYLES, index=0, key=f"{key_prefix}_{col}_{_LINE_FIELD_KEYS['linestyle']}"),
        "linewidth": c2.number_input("Line width", value=1.0, step=0.1, key=f"{key_prefix}_{col}_{_LINE_FIELD_KEYS['linewidth']}"),
        "marker": c3.selectbox("Marker", MARKERS, index=0, key=f"{key_prefix}_{col}_{_LINE_FIELD_KEYS['marker']}"),
        "markersize": c4.number_input("Marker size", value=4.0, step=0.5, key=f"{key_prefix}_{col}_{_LINE_FIELD_KEYS['markersize']}"),
    }


def _draw_line(ax, df: pd.DataFrame, series: dict, ctx: dict) -> None:
    x_col = ctx["x_col"]
    for col, overrides in series.items():
        spec = merge_series_spec(col, overrides, ctx["chart_defaults"])
        # Matplotlib treats linestyle=None as "use the rcParam default" (i.e. a solid line),
        # so the "None" (no line) choice must stay the string "None", unlike marker=None
        # which does mean "no marker".
        mk = None if spec["marker"] == "None" else spec["marker"]
        ax.plot(
            df[x_col], df[col],
            marker=mk, markersize=spec["markersize"],
            linewidth=spec["linewidth"], linestyle=spec["linestyle"],
            label=spec["label"], color=spec["color"],
        )


LINE = ChartType(
    key="line",
    display="Line plot",
    uses_x_column=True,
    needs_bins=False,
    series_defaults={"color": None, "linestyle": "-", "linewidth": 1.0, "marker": "o", "markersize": 4},
    default_xlabel=lambda df: df.columns[0],
    default_ylabel="Value",
    series_fields=_line_series_fields,
    draw=_draw_line,
    field_keys=_LINE_FIELD_KEYS,
    csv_help="First column = X values. Each remaining column = one series (its header becomes the series name).",
    sample_df=_XY_SAMPLE,
)


# ==================== Histogram ====================

_HIST_FIELD_KEYS = {"alpha": "alpha"}


def _hist_series_fields(col: str, key_prefix: str) -> dict:
    return {"alpha": st.slider("Transparency (alpha)", 0.0, 1.0, 0.6, key=f"{key_prefix}_{col}_{_HIST_FIELD_KEYS['alpha']}")}


def compute_bin_edges(value_min: float, value_max: float, xscale: str, n_bins: int) -> list:
    """Compute histogram bin edges. Also intended for reuse by other chart types
    (e.g. CDF/CCDF) that need to bin a range of values.
    """
    n_bins = int(n_bins)
    if xscale == "log":
        if value_min <= 0:
            raise ValueError(f"xmin must be positive when xscale is log (xmin={value_min})")
        ratio = value_max / value_min
        return [value_min * ratio ** (i / n_bins) for i in range(n_bins + 1)]
    return [value_min + i * (value_max - value_min) / n_bins for i in range(n_bins + 1)]


def _draw_hist(ax, df: pd.DataFrame, series: dict, ctx: dict) -> None:
    columns = list(series)
    bin_min = ctx["xmin"] if ctx["xmin"] is not None else df[columns].min().min()
    bin_max = ctx["xmax"] if ctx["xmax"] is not None else df[columns].max().max()
    bin_edges = compute_bin_edges(bin_min, bin_max, ctx["xscale"], ctx["n_bins"])
    for col, overrides in series.items():
        spec = merge_series_spec(col, overrides, ctx["chart_defaults"])
        ax.hist(df[col], bins=bin_edges, alpha=spec["alpha"], color=spec["color"], label=spec["label"])


HIST = ChartType(
    key="hist",
    display="Histogram",
    uses_x_column=False,
    needs_bins=True,
    series_defaults={"color": None, "alpha": 0.6},
    default_xlabel=lambda df: "Value",
    default_ylabel="Frequency (count)",
    series_fields=_hist_series_fields,
    draw=_draw_hist,
    field_keys=_HIST_FIELD_KEYS,
    csv_help="No X column needed. Each column = one series of raw values to bin (its header becomes the series name).",
    sample_df=_VALUES_SAMPLE,
)


# ==================== PDF / CDF / CCDF ====================
# All three reuse the histogram's bin-edge computation (compute_bin_edges) so
# they bin the same way histograms do, just with matplotlib's hist()
# density/cumulative options doing the normalization.

_PDF_FIELD_KEYS = {"alpha": "alpha"}


def _pdf_series_fields(col: str, key_prefix: str) -> dict:
    return {"alpha": st.slider("Transparency (alpha)", 0.0, 1.0, 0.6, key=f"{key_prefix}_{col}_{_PDF_FIELD_KEYS['alpha']}")}


def _draw_pdf(ax, df: pd.DataFrame, series: dict, ctx: dict) -> None:
    columns = list(series)
    bin_min = ctx["xmin"] if ctx["xmin"] is not None else df[columns].min().min()
    bin_max = ctx["xmax"] if ctx["xmax"] is not None else df[columns].max().max()
    bin_edges = compute_bin_edges(bin_min, bin_max, ctx["xscale"], ctx["n_bins"])
    for col, overrides in series.items():
        spec = merge_series_spec(col, overrides, ctx["chart_defaults"])
        ax.hist(df[col], bins=bin_edges, density=True, alpha=spec["alpha"], color=spec["color"], label=spec["label"])


PDF = ChartType(
    key="pdf",
    display="PDF",
    uses_x_column=False,
    needs_bins=True,
    series_defaults={"color": None, "alpha": 0.6},
    default_xlabel=lambda df: "Value",
    default_ylabel="Probability density",
    series_fields=_pdf_series_fields,
    draw=_draw_pdf,
    field_keys=_PDF_FIELD_KEYS,
    csv_help="No X column needed. Each column = one series of raw values to bin (its header becomes the series name).",
    sample_df=_VALUES_SAMPLE,
)


_CUM_FIELD_KEYS = {"linewidth": "lw"}


def _cum_series_fields(col: str, key_prefix: str) -> dict:
    return {
        "linewidth": st.slider(
            "Line width", 0.5, 5.0, 1.5, step=0.1, key=f"{key_prefix}_{col}_{_CUM_FIELD_KEYS['linewidth']}",
        ),
    }


def _draw_cdf(ax, df: pd.DataFrame, series: dict, ctx: dict) -> None:
    columns = list(series)
    bin_min = ctx["xmin"] if ctx["xmin"] is not None else df[columns].min().min()
    bin_max = ctx["xmax"] if ctx["xmax"] is not None else df[columns].max().max()
    bin_edges = compute_bin_edges(bin_min, bin_max, ctx["xscale"], ctx["n_bins"])
    for col, overrides in series.items():
        spec = merge_series_spec(col, overrides, ctx["chart_defaults"])
        ax.hist(
            df[col], bins=bin_edges, density=True, cumulative=True, histtype="step",
            linewidth=spec["linewidth"], color=spec["color"], label=spec["label"],
        )


CDF = ChartType(
    key="cdf",
    display="CDF",
    uses_x_column=False,
    needs_bins=True,
    series_defaults={"color": None, "linewidth": 1.5},
    default_xlabel=lambda df: "Value",
    default_ylabel="Cumulative probability",
    series_fields=_cum_series_fields,
    draw=_draw_cdf,
    field_keys=_CUM_FIELD_KEYS,
    csv_help="No X column needed. Each column = one series of raw values to bin (its header becomes the series name).",
    sample_df=_VALUES_SAMPLE,
)


def _draw_ccdf(ax, df: pd.DataFrame, series: dict, ctx: dict) -> None:
    columns = list(series)
    bin_min = ctx["xmin"] if ctx["xmin"] is not None else df[columns].min().min()
    bin_max = ctx["xmax"] if ctx["xmax"] is not None else df[columns].max().max()
    bin_edges = compute_bin_edges(bin_min, bin_max, ctx["xscale"], ctx["n_bins"])
    for col, overrides in series.items():
        spec = merge_series_spec(col, overrides, ctx["chart_defaults"])
        ax.hist(
            df[col], bins=bin_edges, density=True, cumulative=-1, histtype="step",
            linewidth=spec["linewidth"], color=spec["color"], label=spec["label"],
        )


CCDF = ChartType(
    key="ccdf",
    display="CCDF",
    uses_x_column=False,
    needs_bins=True,
    series_defaults={"color": None, "linewidth": 1.5},
    default_xlabel=lambda df: "Value",
    default_ylabel="P(X > x)",
    series_fields=_cum_series_fields,
    draw=_draw_ccdf,
    field_keys=_CUM_FIELD_KEYS,
    csv_help="No X column needed. Each column = one series of raw values to bin (its header becomes the series name).",
    sample_df=_VALUES_SAMPLE,
)


# ==================== Bar chart ====================
# Grouped (side-by-side) bars: one group per row of the first (X) column,
# one bar per selected series within the group.

_BAR_FIELD_KEYS = {"alpha": "alpha"}


def _bar_series_fields(col: str, key_prefix: str) -> dict:
    return {"alpha": st.slider("Transparency (alpha)", 0.0, 1.0, 1.0, key=f"{key_prefix}_{col}_{_BAR_FIELD_KEYS['alpha']}")}


def _draw_bar(ax, df: pd.DataFrame, series: dict, ctx: dict) -> None:
    x_col = ctx["x_col"]
    n = len(series)
    x = np.arange(len(df))
    width = 0.8 / n
    for i, (col, overrides) in enumerate(series.items()):
        spec = merge_series_spec(col, overrides, ctx["chart_defaults"])
        offset = (i - (n - 1) / 2) * width
        ax.bar(x + offset, df[col], width=width, alpha=spec["alpha"], color=spec["color"], label=spec["label"])
    ax.set_xticks(x)
    ax.set_xticklabels(df[x_col])


BAR = ChartType(
    key="bar",
    display="Bar chart",
    uses_x_column=True,
    needs_bins=False,
    series_defaults={"color": None, "alpha": 1.0},
    default_xlabel=lambda df: df.columns[0],
    default_ylabel="Value",
    series_fields=_bar_series_fields,
    draw=_draw_bar,
    field_keys=_BAR_FIELD_KEYS,
    csv_help="First column = X-axis category labels (one bar group per row). Header row's remaining column names become the series (legend) labels.",
    sample_df=_CATEGORY_SAMPLE,
    categorical_x=True,
)


# ==================== Stem plot ====================

_STEM_FIELD_KEYS = {"marker": "marker", "markersize": "ms", "linewidth": "lw"}


def _stem_series_fields(col: str, key_prefix: str) -> dict:
    c1, c2, c3 = st.columns(3)
    return {
        "marker": c1.selectbox(
            "Marker", [m for m in MARKERS if m != "None"], index=0, key=f"{key_prefix}_{col}_{_STEM_FIELD_KEYS['marker']}",
        ),
        "markersize": c2.number_input("Marker size", value=6.0, step=0.5, key=f"{key_prefix}_{col}_{_STEM_FIELD_KEYS['markersize']}"),
        "linewidth": c3.number_input("Stem width", value=1.0, step=0.1, key=f"{key_prefix}_{col}_{_STEM_FIELD_KEYS['linewidth']}"),
    }


def _draw_stem(ax, df: pd.DataFrame, series: dict, ctx: dict) -> None:
    x_col = ctx["x_col"]
    for col, overrides in series.items():
        spec = merge_series_spec(col, overrides, ctx["chart_defaults"])
        # ax.stem(), unlike plot/bar/hist, doesn't fall back to the axes' own color
        # cycle when no color is given (every call would come out "C0" blue), so
        # a manual color is picked here to match how every other chart type
        # auto-assigns a distinct color per series. The "k" in each fmt string
        # below is just a placeholder overwritten by set_color() right after --
        # it's there only so ax.stem() doesn't *also* pull a (throwaway, but
        # cycle-advancing) color of its own for any fmt that omits one.
        color = spec["color"] if spec["color"] is not None else ax._get_lines.get_next_color()
        markerline, stemlines, baseline = ax.stem(
            df[x_col], df[col], linefmt="k-", markerfmt=f"k{spec['marker']}", basefmt="k ",
            label=spec["label"],
        )
        markerline.set_color(color)
        markerline.set_markersize(spec["markersize"])
        stemlines.set_color(color)
        stemlines.set_linewidth(spec["linewidth"])


STEM = ChartType(
    key="stem",
    display="Stem plot",
    uses_x_column=True,
    needs_bins=False,
    series_defaults={"color": None, "marker": "o", "markersize": 6.0, "linewidth": 1.0},
    default_xlabel=lambda df: df.columns[0],
    default_ylabel="Value",
    series_fields=_stem_series_fields,
    draw=_draw_stem,
    field_keys=_STEM_FIELD_KEYS,
    csv_help="First column = X values. Each remaining column = one series (its header becomes the series name).",
    sample_df=_XY_SAMPLE,
)


CHART_TYPES = {ct.key: ct for ct in [LINE, BAR, HIST, PDF, CDF, CCDF, STEM]}
