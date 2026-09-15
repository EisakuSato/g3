# G3: GUI Graph Generator

*Create beautiful Matplotlib plots visually.*

A Streamlit GUI for turning a CSV into a publication-quality (IEEE-style)
matplotlib figure, without re-tuning legends, axis ranges and ticks by hand
every time.

- `app.py` - the Streamlit GUI: load a CSV, pick a chart type, adjust
  axes/style/legend/output with a live preview, and download the result. See
  "Usage" below.
- `chart_types.py` - the registry the GUI uses to add new chart types (Line
  plot, Histogram, PDF, CDF, CCDF) - see "Adding a new chart type" below
- `plotting.py` - presentation-agnostic building blocks shared by every chart
  type: color palettes, scienceplots style application, figure sizing, and
  series-override merging
- `config_io.py` - safely parses a saved/embedded config back into settings
  (used by the GUI's "Load a saved config" feature)
- `Dockerfile` / `docker-compose.yml` - run the GUI as a shared service (see
  "Deploying with Docker" below)

## Requirements

- Python 3.10+
- A LaTeX installation (e.g. TeX Live) if you want to use the `scienceplots`
  styles (`science`, `ieee`, ...). If you don't have LaTeX, use the GUI's
  "Use scienceplots" toggle to turn it off and adjust fonts/spines/ticks
  manually instead.

## Setup

```bash
git clone <this repo>
cd g3
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
streamlit run app.py
```

This opens a browser tab where you can:
- load a CSV (upload, or point at a path), or try it with generated sample
  data
- pick a chart type (Line plot, Histogram, PDF, CDF, CCDF), choose which
  columns to plot and in what order
- adjust labels, axis ranges/scales, legend (location, multiple columns for
  multi-row legends, placing it outside the plot), a color palette (or leave
  the style's own colors untouched), aspect ratio, grid, tick label size,
  DPI, and either a `scienceplots` style or manual font/spine/tick settings
  (no LaTeX required)
- see the plot update live and download it as a PDF, PNG, SVG, EPS, or TIFF

Line plots treat the first column as the X axis and every other selected
column as a series to plot against it. Histogram/PDF/CDF/CCDF treat every
selected column as an independent distribution (no dedicated X column).

### Secondary axis

Turn on "Add a secondary axis (right)" to overlay a second chart type on a
right-hand y-axis sharing the same x-axis - e.g. a PDF on the left and a CDF
on the right, or any other combination of chart types. Both axes get their
own chart type, columns, y-axis label/scale/range; the x-axis (label, scale,
range) is shared. The two axes' legends are merged into one, and the
secondary axis's auto-assigned colors are offset from the primary axis's so
they don't collide.

This is a GUI-only feature: the saved-config text and the config embedded in
the downloaded file only ever describe the primary (left) axis, so a graph
using a secondary axis can't be fully restored via "Load a saved config"
(loading a config always turns the secondary axis back off).

### Output format

"Output format" (in the sidebar, near DPI) switches the downloaded file
between PDF, PNG, SVG, EPS, and TIFF. PDF, SVG, and EPS are vector (DPI only
affects any raster elements embedded in them); PNG and TIFF are raster, so
DPI sets their resolution directly.

EPS and TIFF can't carry the embedded saved-config text described below
(TIFF's matplotlib writer rejects custom metadata outright; EPS only has a
single-line `Creator` field, too small for this multi-line text, and
stuffing it in there anyway would corrupt the file's PostScript header). Use
PDF/PNG/SVG instead if you want that self-contained round-trip, or just keep
the config text yourself for an EPS/TIFF render.

## Reproducing a graph later

Every render has a "Saved config" panel with the exact settings used, as
plain Python assignments. You can:

1. **Paste it back into the GUI's "Load a saved config"** box (top of the
   sidebar) to restore that exact session - chart type, series, axes, style,
   legend, palette, everything. Keep the text somewhere (a notes file, a
   commit message, ...) if you want to get back to a specific graph later.
2. **Do nothing and come back to the downloaded file itself** (PDF/PNG/SVG
   only - see "Output format" above for why EPS/TIFF can't do this) - the
   same text is embedded in its metadata, so it survives even if you only
   kept the image: PDF's standard `Subject` field, or PNG/SVG's `Description`
   field (SVG's Dublin Core `dc:description`). Read it back with:
   - PDF: any PDF tool (Preview/Explorer file properties, Acrobat,
     `exiftool file.pdf`, `pdfinfo file.pdf`, or
     `PdfReader("file.pdf").metadata.subject` via `pip install pypdf`)
   - PNG: `exiftool file.png`, or `Image.open("file.png").text["Description"]`
     via `pip install pillow`
   - SVG: `exiftool file.svg`, or just open the file as text/XML and look for
     `<dc:description>`

   Then paste the result into option 1 above. For PDF, if your tool only
   shows the raw `/Subject (...)` entry instead of clean text, pasting either
   the whole thing or just the part inside the parentheses both work - the
   GUI auto-detects and un-escapes it.

The parser behind this (`config_io.py`) only evaluates plain literals via
`ast.literal_eval` (plus one special case for `PALETTE = PALETTES[...]`); it
never executes the pasted text, so loading a config - even one you didn't
write yourself - can't run arbitrary code.

One limitation: the GUI's manual (non-`scienceplots`) style settings (font
family, spine visibility, tick direction) aren't part of this saved config.
Everything else round-trips.

## Deploying with Docker

To run the GUI as a shared service (e.g. so a team can all reach it over the
internal network instead of everyone running `streamlit run` locally):

```bash
docker compose up -d --build
# or without compose:
docker build -t g3 .
docker run -d -p 8501:8501 -v "$(pwd)/data:/data:ro" g3
```

Open `http://<host>:8501`. `docker-compose.yml` mounts `./data` (on the host)
read-only to `/data` (in the container) so the GUI's "...or enter a CSV path"
field can point at CSVs the whole team shares (e.g. `/data/results.csv`) --
that field reads paths inside the container, not on each user's own machine,
so without a shared mount it's only really useful via "Upload a CSV" instead.
Point the mount at wherever your team already keeps result CSVs, or drop it.

Two things to know before rolling this out internally:
- **Image size**: the `Dockerfile` installs TeX Live so the `scienceplots`
  styles (`science`, `ieee`, ...) work, which makes the image ~1.9GB. If you
  don't need those styles, remove that `apt-get install` layer from the
  `Dockerfile` for a much smaller image -- the GUI's "Use scienceplots"
  toggle already lets users fall back to LaTeX-free manual styling either way.
- **No built-in auth**: Streamlit itself doesn't authenticate users. This
  setup relies on the container only being reachable from inside the
  corporate network (VPN/intranet, a firewalled host, ...). If you need
  per-user auth, put it in front (e.g. an internal reverse proxy with SSO)
  rather than in the app.
- Sessions (widget state) are per-browser-tab and independent between users,
  but everyone shares the same container process/resources -- fine for a
  small internal team, but not load-tested for heavy concurrent use.

## Adding a new chart type

`app.py` only handles what's common to every chart type (data loading, axes,
style, legend, output). Chart-type-specific behavior (extra per-series
settings, the actual drawing code) lives in `chart_types.py` as a
`ChartType`. To add one (e.g. a scatter plot), follow the `LINE` / `HIST` /
`PDF` examples in that file and register it in `CHART_TYPES` - `app.py`
should not need to change. Give it a `field_keys` mapping (override key ->
widget key suffix) too, so its per-series settings can be restored by the
"Load a saved config" feature like the built-in chart types.

Because `ChartType.draw` only ever receives the `ax` it should draw on, any
chart type also works as a secondary axis for free - the secondary-axis
overlay in the GUI just calls `draw` a second time on `ax.twinx()`.
