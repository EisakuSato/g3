#!/usr/bin/env python3
"""Streamlit prototype for tuning plot_csv.py / plot_histogram.py parameters
interactively, with a live preview.

Run:
    streamlit run app.py

This file only handles the parts that are common to every chart type (data
loading, axes/style/legend/output). Everything that differs between chart
types (extra per-series settings, the actual drawing code) lives in
chart_types.py; adding a new chart type (scatter plot, CDF/CCDF, etc.) only
means adding a ChartType there.

apply_style / merge_series_spec are reused directly from plot_csv.py, so
per-series color/line-style behavior matches the original CLI scripts. Once
you've dialed in values here, the "Config for the scripts" section at the
bottom lets you copy them back into plot_csv.py / plot_histogram.py's SERIES
dict or CLI flags.
"""

import io
from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from cycler import cycler

from chart_types import CHART_TYPES
from plot_csv import apply_style

TABLEAU = list(mcolors.TABLEAU_COLORS.values())
LEGEND_LOCS = [
    "best", "upper right", "upper left", "lower left", "lower right",
    "right", "center left", "center right", "lower center", "upper center", "center",
]
FONT_FAMILIES = ["sans-serif", "serif", "monospace"]
TICK_DIRECTIONS = ["out", "in", "inout"]

st.set_page_config(page_title="Graph Tools GUI", layout="wide")


# ==================== Data loading ====================

@st.cache_data(show_spinner=False)
def load_csv_from_path(path_str: str, mtime: float) -> pd.DataFrame:
    return pd.read_csv(path_str)


@st.cache_data(show_spinner=False)
def load_csv_from_bytes(data: bytes) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(data))


@st.cache_data(show_spinner=False)
def sample_dataframe() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    x = np.linspace(0, 10, 50)
    return pd.DataFrame({
        "x": x,
        "Series1": np.sin(x) + rng.normal(0, 0.05, size=x.size),
        "Series2": np.cos(x) + rng.normal(0, 0.05, size=x.size),
        "Series3": 0.5 * x + rng.normal(0, 0.3, size=x.size),
    })


def load_dataframe():
    st.sidebar.subheader("1. Data")
    uploaded = st.sidebar.file_uploader("Upload a CSV", type=["csv"])
    csv_path = st.sidebar.text_input("...or enter a CSV path", value="")
    use_sample = st.sidebar.checkbox("Use sample data", value=uploaded is None and not csv_path)

    if uploaded is not None:
        return load_csv_from_bytes(uploaded.getvalue()), uploaded.name
    if csv_path:
        path = Path(csv_path)
        if not path.exists():
            st.sidebar.error(f"File not found: {path}")
            return sample_dataframe(), "sample.csv"
        return load_csv_from_path(str(path), path.stat().st_mtime), path.name
    if use_sample:
        return sample_dataframe(), "sample.csv"
    st.sidebar.info("Upload a CSV or enter a path")
    st.stop()


# ==================== Style (scienceplots / manual) ====================

def apply_manual_style(params: dict):
    """Style the plot using plain matplotlib rcParams only, without scienceplots (i.e. no LaTeX)."""
    plt.rcParams.update({
        "font.size": params["font_size"],
        "font.family": params["font_family"],
        "axes.linewidth": params["axes_linewidth"],
        "xtick.direction": params["tick_direction"],
        "ytick.direction": params["tick_direction"],
        "axes.spines.top": params["show_top_spine"],
        "axes.spines.right": params["show_right_spine"],
        "legend.frameon": False,
        "text.usetex": False,
    })
    plt.rcParams["axes.prop_cycle"] = cycler(color=TABLEAU)


# ==================== Per-series settings UI (common part + chart-type-specific part) ====================

def series_controls(columns, chart_type, key_prefix):
    """Build the SERIES config through a collapsible UI per selected column.
    Label and color are common to every chart type; everything else is
    delegated to chart_type.series_fields.
    """
    selected = st.multiselect(
        "Columns to use as series (plotted in the order selected)", options=columns,
        default=columns[: min(3, len(columns))],
        key=f"{key_prefix}_select",
    )
    series = {}
    for i, col in enumerate(selected):
        with st.expander(f"Series: {col}", expanded=False):
            c1, c2 = st.columns(2)
            label = c1.text_input("Legend label", value=col, key=f"{key_prefix}_{col}_label")
            auto_color = c2.checkbox("Auto-assign color", value=True, key=f"{key_prefix}_{col}_autocolor")
            overrides = {"label": label}
            if not auto_color:
                default_hex = TABLEAU[i % len(TABLEAU)]
                overrides["color"] = st.color_picker("Color", value=default_hex, key=f"{key_prefix}_{col}_color")

            overrides.update(chart_type.series_fields(col, key_prefix))
            series[col] = overrides
    return series


# ==================== Main ====================

def main():
    st.title("Graph Tools GUI (prototype)")
    st.caption("A tool for tuning plot_csv.py / plot_histogram.py parameters interactively")

    df, source_name = load_dataframe()

    with st.expander("Preview loaded data", expanded=False):
        st.dataframe(df.head(20), width="stretch")

    chart_key = st.sidebar.radio(
        "2. Chart type", list(CHART_TYPES.keys()), format_func=lambda k: CHART_TYPES[k].display,
    )
    chart_type = CHART_TYPES[chart_key]

    st.sidebar.subheader("3. Axes & appearance")
    xlabel = st.sidebar.text_input("X-axis label", value=chart_type.default_xlabel(df))
    ylabel = st.sidebar.text_input("Y-axis label", value=chart_type.default_ylabel)
    c1, c2 = st.sidebar.columns(2)
    xscale = c1.selectbox("X scale", ["linear", "log"])
    yscale = c2.selectbox("Y scale", ["linear", "log"])

    c3, c4 = st.sidebar.columns(2)
    xmin_s = c3.text_input("Xmin (blank = auto)", value="")
    xmax_s = c4.text_input("Xmax (blank = auto)", value="")
    c5, c6 = st.sidebar.columns(2)
    ymin_s = c5.text_input("Ymin (blank = auto)", value="")
    ymax_s = c6.text_input("Ymax (blank = auto)", value="")

    def parse_opt_float(s):
        s = s.strip()
        return float(s) if s else None

    try:
        xmin, xmax = parse_opt_float(xmin_s), parse_opt_float(xmax_s)
        ymin, ymax = parse_opt_float(ymin_s), parse_opt_float(ymax_s)
    except ValueError:
        st.sidebar.error("Axis range values must be numbers")
        st.stop()

    use_scienceplots = st.sidebar.checkbox(
        "Use scienceplots", value=True,
        help="Turn off to use plain matplotlib settings (no LaTeX required), with fonts etc. adjustable individually",
    )
    manual_style_params = {}
    if use_scienceplots:
        style_str = st.sidebar.text_input("scienceplots style (comma-separated)", value="science, ieee")
        style = [s.strip() for s in style_str.split(",") if s.strip()]
    else:
        style = []
        with st.sidebar.expander("Manual style settings", expanded=True):
            c1, c2 = st.columns(2)
            manual_style_params["font_family"] = c1.selectbox("Font family", FONT_FAMILIES)
            manual_style_params["font_size"] = c2.number_input("Base font size", value=10.0, step=1.0)
            c3, c4 = st.columns(2)
            manual_style_params["axes_linewidth"] = c3.number_input("Axis line width", value=0.8, step=0.1)
            manual_style_params["tick_direction"] = c4.selectbox("Tick direction", TICK_DIRECTIONS)
            c5, c6 = st.columns(2)
            manual_style_params["show_top_spine"] = c5.checkbox("Show top spine", value=True)
            manual_style_params["show_right_spine"] = c6.checkbox("Show right spine", value=True)

    with st.sidebar.expander("Advanced settings"):
        legend_loc = st.selectbox("Legend location", ["(hidden)"] + LEGEND_LOCS)
        legend_ncol = st.number_input(
            "Legend columns (fewer than the series count wraps into multiple rows)", min_value=1, value=1, step=1,
        )
        legend_outside = st.checkbox("Place legend outside the plot (below)", value=False)
        fig_w = st.number_input("Figure width (inches, 0 = auto)", value=0.0, step=0.5)
        fig_h = st.number_input("Figure height (inches, 0 = auto)", value=0.0, step=0.5)
        tick_fontsize = st.number_input("Tick label font size (0 = auto)", value=0.0, step=1.0)
        grid_on = st.checkbox("Show grid", value=False)
        n_bins = st.number_input("Number of bins", value=100, step=10) if chart_type.needs_bins else None
        dpi = st.number_input("Output DPI", value=600, step=50)

    st.subheader("4. Series settings")
    x_col = df.columns[0] if chart_type.uses_x_column else None
    candidate_cols = list(df.columns[1:]) if chart_type.uses_x_column else list(df.columns)
    series = series_controls(candidate_cols, chart_type, chart_type.key)

    if not series:
        st.warning("Select at least one series")
        st.stop()

    # ==================== Rendering ====================
    plt.rcdefaults()  # reset every run so a previous style (scienceplots/manual) doesn't leak through
    try:
        if use_scienceplots:
            apply_style(style)
        else:
            apply_manual_style(manual_style_params)
    except Exception as e:  # noqa: BLE001 (prototype: report broadly to the UI)
        st.error(f"Failed to apply style ({style}): {e}\nIf the style requires LaTeX, this fails when LaTeX is not installed.")
        st.stop()

    figsize = (fig_w if fig_w > 0 else None, fig_h if fig_h > 0 else None)
    fig, ax = plt.subplots(figsize=figsize if all(figsize) else None)

    ctx = {
        "x_col": x_col,
        "xmin": xmin,
        "xmax": xmax,
        "xscale": xscale,
        "n_bins": n_bins,
        "chart_defaults": chart_type.series_defaults,
    }
    try:
        chart_type.draw(ax, df, series, ctx)

        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_xscale(xscale)
        ax.set_yscale(yscale)
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        if legend_loc != "(hidden)":
            legend_kwargs = {"frameon": False, "ncol": int(legend_ncol)}
            if legend_outside:
                legend_kwargs.update(loc="upper center", bbox_to_anchor=(0.5, -0.15))
            else:
                legend_kwargs["loc"] = legend_loc
            ax.legend(**legend_kwargs)
        if grid_on:
            ax.grid(True, alpha=0.3)
        if tick_fontsize > 0:
            ax.tick_params(labelsize=tick_fontsize)
        fig.tight_layout()
    except Exception as e:  # noqa: BLE001
        st.error(f"Failed to render the plot: {e}")
        st.stop()

    st.subheader("5. Preview")
    st.pyplot(fig, width="content")

    buf = io.BytesIO()
    fig.savefig(buf, format="pdf", dpi=dpi)
    default_out = f"{Path(source_name).stem}_{chart_type.key}.pdf"
    st.download_button("Download PDF", data=buf.getvalue(), file_name=default_out, mime="application/pdf")

    with st.expander("Config for the scripts (plot_csv.py / plot_histogram.py)", expanded=False):
        lines = ["SERIES = {"]
        for col, overrides in series.items():
            items = ", ".join(f'"{k}": {v!r}' for k, v in overrides.items())
            lines.append(f'    "{col}": {{{items}}},')
        lines.append("}")
        lines.append(f"XLABEL = {xlabel!r}")
        lines.append(f"YLABEL = {ylabel!r}")
        lines.append(f"XMIN, XMAX = {xmin!r}, {xmax!r}")
        lines.append(f"YMIN, YMAX = {ymin!r}, {ymax!r}")
        lines.append(f"XSCALE = {xscale!r}")
        lines.append(f"YSCALE = {yscale!r}")
        lines.append(f"STYLE = {style!r}")
        if chart_type.needs_bins:
            lines.append(f"N_BINS = {int(n_bins)!r}")
        st.code("\n".join(lines), language="python")
        if not use_scienceplots:
            st.caption(
                "Manual style settings (fonts, spines, tick direction, etc.) can't be "
                "represented in the current plot_csv.py/plot_histogram.py since "
                "'Use scienceplots' is off. With STYLE=[] as above, matplotlib's "
                "defaults are used instead."
            )


if __name__ == "__main__":
    main()
