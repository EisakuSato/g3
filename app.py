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

apply_style / apply_legend / compute_figsize / PALETTES are all reused
directly from plot_csv.py (also shared by plot_histogram.py), so the preview
here renders identically to what the CLI scripts produce. Once you've dialed
in values here, the "Config for the scripts" section at the bottom lets you
copy them back into plot_csv.py / plot_histogram.py's hardcoded settings.
"""

import io
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from cycler import cycler

from chart_types import CHART_TYPES
from config_io import ConfigParseError, parse_config_text
from plot_csv import LEGEND_LOCS, PALETTES, apply_legend, apply_style, compute_figsize

FONT_FAMILIES = ["sans-serif", "serif", "monospace"]
TICK_DIRECTIONS = ["out", "in", "inout"]

# "none" (mapped to PALETTE = None, i.e. leave the active style's own color
# cycle untouched) plus every named preset from plot_csv.PALETTES, so the GUI
# and CLI scripts always agree on what a palette name means.
PALETTE_CHOICES = ["none", *PALETTES]
PALETTE_LABELS = {
    "none": "(style default)",
    "tableau": "Tableau (tab10)",
    "okabe-ito": "Okabe-Ito (colorblind-safe)",
    "set2": "Set2",
    "dark2": "Dark2",
    "grayscale": "Grayscale",
}

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
    """Style the plot using plain matplotlib rcParams only, without scienceplots (i.e. no LaTeX).
    Leaves the color cycle untouched; the caller applies the chosen palette (see PALETTES).
    This manual mode has no equivalent in plot_csv.py/plot_histogram.py: it exists purely
    as a GUI convenience for previewing without a LaTeX install.
    """
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


# ==================== Per-series settings UI (common part + chart-type-specific part) ====================

def series_controls(columns, chart_type, key_prefix, palette_colors):
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
                default_hex = palette_colors[i % len(palette_colors)]
                overrides["color"] = st.color_picker("Color", value=default_hex, key=f"{key_prefix}_{col}_color")

            overrides.update(chart_type.series_fields(col, key_prefix))
            series[col] = overrides
    return series


# ==================== Loading a saved config ====================

def apply_saved_config(text: str, df: pd.DataFrame):
    """Parse a previously generated "Config for the scripts" block and push it
    into st.session_state so every widget picks it back up on the next run.
    Must run before any of the affected widgets are instantiated in this run
    (this function itself doesn't create any), and finishes with st.rerun()
    so they're re-created from the updated session_state.
    """
    if not text.strip():
        st.sidebar.error("Paste a config first.")
        return
    try:
        chart_key, values = parse_config_text(text, PALETTES)
    except ConfigParseError as e:
        st.sidebar.error(f"Could not load this config: {e}")
        return

    if chart_key not in CHART_TYPES:
        st.sidebar.error(
            "Could not tell which chart type this config is for (missing or unrecognized "
            "'# graph-tools config: chart_type=...' header)."
        )
        return
    chart_type = CHART_TYPES[chart_key]

    series = values.get("SERIES")
    if series is not None:
        candidate_cols = list(df.columns[1:]) if chart_type.uses_x_column else list(df.columns)
        missing = [col for col in series if col not in candidate_cols]
        if missing:
            st.sidebar.error(
                f"These columns from the saved config aren't in the currently loaded data: "
                f"{', '.join(missing)}. Load the matching CSV first."
            )
            return

    updates = {"chart_type_radio": chart_key, "use_scienceplots_checkbox": True}

    def set_if_present(config_key, session_key, transform=lambda v: v):
        if config_key in values:
            updates[session_key] = transform(values[config_key])

    set_if_present("XLABEL", "xlabel_input", lambda v: v if v is not None else "")
    set_if_present("YLABEL", "ylabel_input")
    set_if_present("XMIN", "xmin_input", lambda v: "" if v is None else str(v))
    set_if_present("XMAX", "xmax_input", lambda v: "" if v is None else str(v))
    set_if_present("YMIN", "ymin_input", lambda v: "" if v is None else str(v))
    set_if_present("YMAX", "ymax_input", lambda v: "" if v is None else str(v))
    set_if_present("XSCALE", "xscale_select")
    set_if_present("YSCALE", "yscale_select")
    set_if_present("STYLE", "style_input", lambda v: ", ".join(v) if isinstance(v, (list, tuple)) else str(v))
    if "PALETTE" in values:
        updates["palette_select"] = "none" if values["PALETTE"] is None else values["PALETTE"]
    if "LEGEND_LOC" in values:
        loc = values["LEGEND_LOC"]
        updates["legend_hidden_checkbox"] = loc is None
        if loc is not None:
            updates["legend_loc_select"] = loc
    set_if_present("LEGEND_NCOL", "legend_ncol_input", int)
    set_if_present("LEGEND_OUTSIDE", "legend_outside_checkbox", bool)
    if "WIDTH_RATIO" in values:
        updates["width_ratio_input"] = values["WIDTH_RATIO"] or 0.0
    if "HEIGHT_RATIO" in values:
        updates["height_ratio_input"] = values["HEIGHT_RATIO"] or 0.0
    set_if_present("GRID", "grid_checkbox", bool)
    if "TICK_FONTSIZE" in values:
        updates["tick_fontsize_input"] = values["TICK_FONTSIZE"] or 0.0
    set_if_present("DPI", "dpi_input", int)
    set_if_present("N_BINS", "n_bins_input", int)

    if series is not None:
        updates[f"{chart_key}_select"] = list(series.keys())
        for col, overrides in series.items():
            prefix = f"{chart_key}_{col}"
            updates[f"{prefix}_label"] = overrides.get("label", col)
            has_color = "color" in overrides
            updates[f"{prefix}_autocolor"] = not has_color
            if has_color:
                updates[f"{prefix}_color"] = overrides["color"]
            for override_key, suffix in chart_type.field_keys.items():
                if override_key in overrides:
                    updates[f"{prefix}_{suffix}"] = overrides[override_key]

    for key, value in updates.items():
        st.session_state[key] = value
    st.rerun()


def build_config_text(chart_type, series, settings: dict) -> str:
    """Build the "Config for the scripts" text: plain Python assignments,
    pasteable into plot_csv.py/plot_histogram.py as-is, and parseable by
    config_io.parse_config_text to restore this GUI session (see
    apply_saved_config) or to reconstruct the graph from a PDF it's later
    embedded into (see main()).
    """
    palette_expr = "None" if settings["palette_key"] == "none" else f"PALETTES[{settings['palette_key']!r}]"

    lines = [f"# graph-tools config: chart_type={chart_type.key}", "SERIES = {"]
    for col, overrides in series.items():
        items = ", ".join(f'"{k}": {v!r}' for k, v in overrides.items())
        lines.append(f'    "{col}": {{{items}}},')
    lines.append("}")
    lines.append(f"XLABEL = {settings['xlabel']!r}")
    lines.append(f"YLABEL = {settings['ylabel']!r}")
    lines.append(f"XMIN, XMAX = {settings['xmin']!r}, {settings['xmax']!r}")
    lines.append(f"YMIN, YMAX = {settings['ymin']!r}, {settings['ymax']!r}")
    lines.append(f"XSCALE = {settings['xscale']!r}")
    lines.append(f"YSCALE = {settings['yscale']!r}")
    lines.append(f"STYLE = {settings['style']!r}")
    lines.append(f"PALETTE = {palette_expr}")
    lines.append(f"LEGEND_LOC = {settings['legend_loc_value']!r}")
    lines.append(f"LEGEND_NCOL = {int(settings['legend_ncol'])!r}")
    lines.append(f"LEGEND_OUTSIDE = {settings['legend_outside']!r}")
    width_ratio_val = settings["width_ratio"] if settings["width_ratio"] > 0 else None
    height_ratio_val = settings["height_ratio"] if settings["height_ratio"] > 0 else None
    lines.append(f"WIDTH_RATIO, HEIGHT_RATIO = {width_ratio_val!r}, {height_ratio_val!r}")
    lines.append(f"GRID = {settings['grid_on']!r}")
    tick_fontsize_val = settings["tick_fontsize"] if settings["tick_fontsize"] > 0 else None
    lines.append(f"TICK_FONTSIZE = {tick_fontsize_val!r}")
    lines.append(f"DPI = {int(settings['dpi'])!r}")
    if chart_type.needs_bins:
        lines.append(f"N_BINS = {int(settings['n_bins'])!r}")
    return "\n".join(lines)


# ==================== Main ====================

def main():
    st.title("Graph Tools GUI")
    st.caption("A tool for tuning plot_csv.py / plot_histogram.py parameters interactively")

    df, source_name = load_dataframe()

    with st.sidebar.expander("Load a saved config", expanded=False):
        config_text = st.text_area(
            "Paste a previously generated \"Config for the scripts\" block", height=150, key="load_config_text",
        )
        if st.button("Apply config"):
            apply_saved_config(config_text, df)

    with st.expander("Preview loaded data", expanded=False):
        st.dataframe(df.head(20), width="stretch")

    chart_key = st.sidebar.radio(
        "2. Chart type", list(CHART_TYPES.keys()), format_func=lambda k: CHART_TYPES[k].display,
        key="chart_type_radio",
    )
    chart_type = CHART_TYPES[chart_key]

    st.sidebar.subheader("3. Axes & appearance")
    xlabel = st.sidebar.text_input("X-axis label", value=chart_type.default_xlabel(df), key="xlabel_input")
    ylabel = st.sidebar.text_input("Y-axis label", value=chart_type.default_ylabel, key="ylabel_input")
    c1, c2 = st.sidebar.columns(2)
    xscale = c1.selectbox("X scale", ["linear", "log"], key="xscale_select")
    yscale = c2.selectbox("Y scale", ["linear", "log"], key="yscale_select")

    c3, c4 = st.sidebar.columns(2)
    xmin_s = c3.text_input("Xmin (blank = auto)", value="", key="xmin_input")
    xmax_s = c4.text_input("Xmax (blank = auto)", value="", key="xmax_input")
    c5, c6 = st.sidebar.columns(2)
    ymin_s = c5.text_input("Ymin (blank = auto)", value="", key="ymin_input")
    ymax_s = c6.text_input("Ymax (blank = auto)", value="", key="ymax_input")

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
        key="use_scienceplots_checkbox",
    )
    manual_style_params = {}
    if use_scienceplots:
        style_str = st.sidebar.text_input(
            "scienceplots style (comma-separated)", value="science, ieee", key="style_input",
        )
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

    st.sidebar.subheader("Advanced settings")
    legend_hidden = st.sidebar.checkbox("Hide legend", value=False, key="legend_hidden_checkbox")
    legend_loc = st.sidebar.selectbox(
        "Legend location", LEGEND_LOCS, disabled=legend_hidden, key="legend_loc_select",
    )
    legend_ncol = st.sidebar.number_input(
        "Legend columns (fewer than the series count wraps into multiple rows)", min_value=1, value=1, step=1,
        key="legend_ncol_input",
    )
    legend_outside = st.sidebar.checkbox(
        "Place legend outside the plot (below)", value=False, key="legend_outside_checkbox",
    )
    c1, c2 = st.sidebar.columns(2)
    width_ratio = c1.number_input(
        "Aspect ratio: width (0 = auto)", value=0.0, step=0.5, min_value=0.0, key="width_ratio_input",
    )
    height_ratio = c2.number_input(
        "Aspect ratio: height (0 = auto)", value=0.0, step=0.5, min_value=0.0, key="height_ratio_input",
    )
    if (width_ratio > 0) != (height_ratio > 0):
        st.sidebar.warning("Set both width and height, or leave both at 0 for auto")
    palette_key = st.sidebar.selectbox(
        "Color palette", PALETTE_CHOICES, format_func=lambda k: PALETTE_LABELS[k],
        help="'(style default)' leaves the active style's own color cycle untouched",
        key="palette_select",
    )
    tick_fontsize = st.sidebar.number_input(
        "Tick label font size (0 = auto)", value=0.0, step=1.0, key="tick_fontsize_input",
    )
    grid_on = st.sidebar.checkbox("Show grid", value=False, key="grid_checkbox")
    n_bins = (
        st.sidebar.number_input("Number of bins", value=100, step=10, key="n_bins_input")
        if chart_type.needs_bins else None
    )
    dpi = st.sidebar.number_input("Output DPI", value=600, step=50, key="dpi_input")

    legend_loc_value = None if legend_hidden else legend_loc

    st.subheader("4. Series settings")
    x_col = df.columns[0] if chart_type.uses_x_column else None
    candidate_cols = list(df.columns[1:]) if chart_type.uses_x_column else list(df.columns)
    palette_colors = PALETTES[palette_key] if palette_key != "none" else PALETTES["tableau"]
    series = series_controls(candidate_cols, chart_type, chart_type.key, palette_colors)

    if not series:
        st.warning("Select at least one series")
        st.stop()

    # ==================== Rendering ====================
    plt.rcdefaults()  # reset every run so a previous style (scienceplots/manual) doesn't leak through
    palette = None if palette_key == "none" else PALETTES[palette_key]
    try:
        if use_scienceplots:
            apply_style(style, palette)
        else:
            apply_manual_style(manual_style_params)
            if palette is not None:
                plt.rcParams["axes.prop_cycle"] = cycler(color=palette)
    except Exception as e:  # noqa: BLE001 (prototype: report broadly to the UI)
        st.error(f"Failed to apply style ({style}): {e}\nIf the style requires LaTeX, this fails when LaTeX is not installed.")
        st.stop()

    fig, ax = plt.subplots(figsize=compute_figsize(width_ratio, height_ratio))

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
        apply_legend(ax, legend_loc_value, int(legend_ncol), legend_outside)
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

    config_text = build_config_text(chart_type, series, {
        "xlabel": xlabel, "ylabel": ylabel, "xmin": xmin, "xmax": xmax, "ymin": ymin, "ymax": ymax,
        "xscale": xscale, "yscale": yscale, "style": style, "palette_key": palette_key,
        "legend_loc_value": legend_loc_value, "legend_ncol": legend_ncol, "legend_outside": legend_outside,
        "width_ratio": width_ratio, "height_ratio": height_ratio, "grid_on": grid_on,
        "tick_fontsize": tick_fontsize, "dpi": dpi, "n_bins": n_bins,
    })

    buf = io.BytesIO()
    fig.savefig(
        buf, format="pdf", dpi=dpi,
        # Subject is a standard PDF Info-dict field, so any PDF tool (Preview/Explorer file
        # properties, Acrobat, exiftool, pdfinfo, ...) can read it back -- unlike a custom key,
        # which only specialized libraries pick up.
        metadata={"Keywords": "graph-tools", "Subject": config_text},
    )
    default_out = f"{Path(source_name).stem}_{chart_type.key}.pdf"
    st.download_button("Download PDF", data=buf.getvalue(), file_name=default_out, mime="application/pdf")

    with st.expander("Config for the scripts (plot_csv.py / plot_histogram.py)", expanded=False):
        st.code(config_text, language="python")
        st.caption(
            "Paste this whole block into the \"Load a saved config\" box (top of the sidebar) "
            "later to restore this exact graph, or into plot_csv.py/plot_histogram.py's "
            "hardcoded settings to reproduce it from the CLI."
        )
        st.caption(
            "It's also embedded in the downloaded PDF itself, in the standard 'Subject' field of "
            "the PDF's metadata -- so if you come back to a PDF later wanting to reproduce its "
            "style, you don't need to have kept this text separately. Any PDF tool can read it "
            "back (it's a standard field, not a custom one): file properties in Preview/Explorer, "
            "Acrobat, `exiftool file.pdf`, `pdfinfo file.pdf`, or `PdfReader(\"file.pdf\").metadata.subject` "
            "in Python (`pip install pypdf`). Paste the result back in here or into the CLI scripts -- "
            "if your tool only shows the raw '/Subject (...)' entry instead of clean text, pasting "
            "either the whole thing or just the part inside the parentheses both work."
        )

        if not use_scienceplots:
            st.caption(
                "Manual style settings (fonts, spines, tick direction, etc.) have no equivalent "
                "in plot_csv.py/plot_histogram.py, since they only ever style through scienceplots. "
                "With STYLE=[] as above, matplotlib's defaults are used there instead; set an "
                "explicit STYLE if you want a specific scienceplots look for the reproducible script."
            )


if __name__ == "__main__":
    main()
