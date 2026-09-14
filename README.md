# graph-tools

Small helpers for turning a CSV into a publication-quality (IEEE-style)
matplotlib figure, without re-tuning legends, axis ranges and ticks by hand
every time.

- `plot_csv.py` - line plots
- `plot_histogram.py` - histograms
- `app.py` - a Streamlit GUI that wraps both, with a live preview, so you can
  find the right settings interactively before baking them into the scripts
  above (or just keep using the GUI - see "Reproducing a graph later" below)
- `chart_types.py` - the registry the GUI uses to add new chart types (see
  "Adding a new chart type" below)
- `config_io.py` - safely parses a saved/embedded config back into settings
  (used by the GUI's "Load a saved config" feature)

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

# Legend, color palette, aspect ratio, grid, ticks
python plot_csv.py data.csv --palette okabe-ito --legend-loc "lower center" \
  --legend-ncol 2 --legend-outside --width-ratio 16 --height-ratio 9 \
  --grid --tick-fontsize 8
```

Run `python plot_csv.py --help` / `python plot_histogram.py --help` for the
full list of flags. Both scripts share the same set of presets for
`--palette`/`PALETTE`: `tableau` (the default), `okabe-ito` (colorblind-safe),
`set2`, `dark2`, `grayscale`, or `none` to leave `STYLE`'s own colors
untouched.

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
- adjust labels, axis ranges/scales, legend (location, multiple columns for
  multi-row legends, placing it outside the plot), a color palette (or leave
  the style's own colors untouched), aspect ratio, grid, tick label size,
  DPI, and either a `scienceplots` style or manual font/spine/tick settings
  (no LaTeX required)
- see the plot update live and download it as a PDF

The GUI renders through the exact same `apply_style` / `apply_legend` /
`compute_figsize` / `PALETTES` functions the CLI scripts use (all defined in
`plot_csv.py`), so what you see in the preview matches what the CLI scripts
produce from the same settings.

## Reproducing a graph later

Every render has a "Config for the scripts" panel with the exact settings
used, as plain Python assignments. You can:

1. **Paste it into `plot_csv.py`/`plot_histogram.py`** - it's written in the
   same `SERIES = {...}` / `XLABEL = ...` shape as the hardcoded settings
   block, so it drops in directly.
2. **Paste it back into the GUI's "Load a saved config"** box (top of the
   sidebar) to restore that exact session - chart type, series, axes, style,
   legend, palette, everything. Keep the text somewhere (a notes file, a
   commit message, ...) if you want to get back to a specific graph later.
3. **Do nothing and come back to the PDF itself** - the same text is embedded
   in the downloaded PDF's standard `Subject` metadata field, so it survives
   even if you only kept the PDF. Read it back with any PDF tool (Preview/
   Explorer file properties, Acrobat, `exiftool file.pdf`, `pdfinfo file.pdf`,
   or `PdfReader("file.pdf").metadata.subject` via `pip install pypdf`) and
   paste the result into option 1 or 2 above. If your tool only shows the raw
   `/Subject (...)` entry instead of clean text, pasting either the whole
   thing or just the part inside the parentheses both work - the GUI
   auto-detects and un-escapes it.

The parser behind option 2/3 (`config_io.py`) only evaluates plain literals
via `ast.literal_eval` (plus one special case for `PALETTE = PALETTES[...]`);
it never executes the pasted text, so loading a config - even one you didn't
write yourself - can't run arbitrary code.

One limitation: the GUI's manual (non-`scienceplots`) style settings (font
family, spine visibility, tick direction) aren't part of this saved config,
since they have no equivalent in the CLI scripts. Everything else round-trips.

## Adding a new chart type

`app.py` only handles what's common to every chart type (data loading, axes,
style, legend, output). Chart-type-specific behavior (extra per-series
settings, the actual drawing code) lives in `chart_types.py` as a
`ChartType`. To add one (e.g. a scatter plot or CDF/CCDF), follow the `LINE`
/ `HIST` examples in that file and register it in `CHART_TYPES` - `app.py`
should not need to change. Give it a `field_keys` mapping (override key ->
widget key suffix) too, so its per-series settings can be restored by the
"Load a saved config" feature like the built-in chart types.
