# graph-tools

Small helpers for turning a CSV into a publication-quality (IEEE-style)
matplotlib figure, without re-tuning legends, axis ranges and ticks by hand
every time.

- `plot_csv.py` - line plots
- `plot_histogram.py` - histograms
- `app.py` - a Streamlit GUI that wraps both, with a live preview, so you can
  find the right settings interactively before baking them into the scripts
  above
- `chart_types.py` - the registry the GUI uses to add new chart types (see
  "Adding a new chart type" below)

## Requirements

- Python 3.10+
- A LaTeX installation (e.g. TeX Live) if you want to use the `scienceplots`
  styles (`science`, `ieee`, ...). If you don't have LaTeX, use the CLI
  scripts with `STYLE = []` / `--style` omitted, or use the GUI's "Use
  scienceplots" toggle to turn it off and adjust fonts/spines/ticks manually
  instead.

## Setup

```bash
git clone <this repo>
cd graph-tools
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage: CLI scripts

Each script has settings hardcoded near the top of the file (`SERIES`,
`XLABEL`, `STYLE`, ...) with comments explaining each one, plus command-line
flags that override them for one-off runs. Anything you don't pass on the
command line falls back to the hardcoded value.

```bash
# Uses the hardcoded CSV_PATH / SERIES / etc. in the file
python plot_csv.py

# Override from the command line
python plot_csv.py data.csv --series Series1 Series2 --xlabel "Time (s)" --output out.pdf

python plot_histogram.py data.csv --series Series1 Series2 --bins 50 --xscale log
```

Run `python plot_csv.py --help` / `python plot_histogram.py --help` for the
full list of flags.

CSV format:
- `plot_csv.py` treats the first column as the X axis and every other
  selected column as a series to plot against it.
- `plot_histogram.py` treats every selected column as an independent
  distribution to histogram (no dedicated X column).

To customize a series (label, color, line style, marker, alpha, ...), edit
the `SERIES` dict at the top of the file - see the comment block above it in
each script for the available keys.

## Usage: GUI

```bash
streamlit run app.py
```

This opens a browser tab where you can:
- load a CSV (upload, or point at a path), or try it with generated sample
  data
- pick a chart type, choose which columns to plot and in what order
- adjust labels, axis ranges/scales, legend (including multi-row legends),
  figure size, DPI, and either a `scienceplots` style or manual
  font/spine/tick settings
- see the plot update live, download it as a PDF, and copy the resulting
  `SERIES` / `XLABEL` / ... values back into `plot_csv.py` /
  `plot_histogram.py` for reproducible, scripted runs later

## Adding a new chart type

`app.py` only handles what's common to every chart type (data loading, axes,
style, legend, output). Chart-type-specific behavior (extra per-series
settings, the actual drawing code) lives in `chart_types.py` as a
`ChartType`. To add one (e.g. a scatter plot or CDF/CCDF), follow the `LINE`
/ `HIST` examples in that file and register it in `CHART_TYPES` - `app.py`
should not need to change.
