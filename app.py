#!/usr/bin/env python3
"""plot_csv.py / plot_histogram.py のパラメータをGUIで調整し、
リアルタイムプレビューしながら図を作るStreamlitプロトタイプ。

起動:
    streamlit run app.py

plot_csv.py / plot_histogram.py の apply_style / merge_series_spec を
そのまま再利用しているので、系列ごとの色・線種の決め方は元のCLIスクリプトと同じ。
GUIで追い込んだ値は、下部の「スクリプト用の設定」からコピーして
plot_csv.py / plot_histogram.py のSERIES辞書やCLI引数に戻せる。
"""

import io
from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from plot_csv import apply_style, merge_series_spec

TABLEAU = list(mcolors.TABLEAU_COLORS.values())
STYLE_PRESETS = ["science", "ieee", "no-latex", "grid", "bright", "high-vis", "notebook"]
LINESTYLES = ["-", "--", "-.", ":", "None"]
MARKERS = ["o", "s", "^", "v", "D", "x", "+", "*", ".", "None"]
LEGEND_LOCS = [
    "best", "upper right", "upper left", "lower left", "lower right",
    "right", "center left", "center right", "lower center", "upper center", "center",
]

st.set_page_config(page_title="Graph Tools GUI", layout="wide")


# ==================== データ読み込み ====================

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
    st.sidebar.subheader("1. データ")
    uploaded = st.sidebar.file_uploader("CSVをアップロード", type=["csv"])
    csv_path = st.sidebar.text_input("またはCSVのパスを指定", value="")
    use_sample = st.sidebar.checkbox("サンプルデータを使う", value=uploaded is None and not csv_path)

    if uploaded is not None:
        return load_csv_from_bytes(uploaded.getvalue()), uploaded.name
    if csv_path:
        path = Path(csv_path)
        if not path.exists():
            st.sidebar.error(f"ファイルが見つかりません: {path}")
            return sample_dataframe(), "sample.csv"
        return load_csv_from_path(str(path), path.stat().st_mtime), path.name
    if use_sample:
        return sample_dataframe(), "sample.csv"
    st.sidebar.info("CSVをアップロードするか、パスを入力してください")
    st.stop()


# ==================== 系列ごとの設定UI ====================

def series_controls(columns, mode, key_prefix):
    """選択された列ごとに、折りたたみ式のUIでSERIES設定を組み立てる。"""
    selected = st.multiselect(
        "系列に使う列(選んだ順にプロットされる)", options=columns, default=columns[: min(3, len(columns))],
        key=f"{key_prefix}_select",
    )
    series = {}
    for i, col in enumerate(selected):
        with st.expander(f"系列: {col}", expanded=False):
            c1, c2 = st.columns(2)
            label = c1.text_input("凡例ラベル", value=col, key=f"{key_prefix}_{col}_label")
            auto_color = c2.checkbox("色を自動割り当て", value=True, key=f"{key_prefix}_{col}_autocolor")
            overrides = {"label": label}
            if not auto_color:
                default_hex = TABLEAU[i % len(TABLEAU)]
                overrides["color"] = st.color_picker("色", value=default_hex, key=f"{key_prefix}_{col}_color")

            if mode == "line":
                c3, c4, c5, c6 = st.columns(4)
                overrides["linestyle"] = c3.selectbox("線種", LINESTYLES, index=0, key=f"{key_prefix}_{col}_ls")
                overrides["linewidth"] = c4.number_input("線の太さ", value=1.0, step=0.1, key=f"{key_prefix}_{col}_lw")
                overrides["marker"] = c5.selectbox("マーカー", MARKERS, index=0, key=f"{key_prefix}_{col}_marker")
                overrides["markersize"] = c6.number_input("マーカーサイズ", value=4.0, step=0.5, key=f"{key_prefix}_{col}_ms")
            else:
                overrides["alpha"] = st.slider("透過度(alpha)", 0.0, 1.0, 0.6, key=f"{key_prefix}_{col}_alpha")

            series[col] = overrides
    return series


# ==================== メイン ====================

def main():
    st.title("Graph Tools GUI (prototype)")
    st.caption("plot_csv.py / plot_histogram.py のパラメータをその場で調整して確認するためのツール")

    df, source_name = load_dataframe()

    with st.expander("読み込んだデータのプレビュー", expanded=False):
        st.dataframe(df.head(20), width="stretch")

    mode_label = st.sidebar.radio("2. グラフの種類", ["折れ線グラフ (plot_csv)", "ヒストグラム (plot_histogram)"])
    mode = "line" if mode_label.startswith("折れ線") else "hist"

    st.sidebar.subheader("3. 軸・見た目")
    xlabel = st.sidebar.text_input("X軸ラベル", value=(df.columns[0] if mode == "line" else "Value"))
    ylabel = st.sidebar.text_input("Y軸ラベル", value="Value" if mode == "line" else "Frequency (count)")
    c1, c2 = st.sidebar.columns(2)
    xscale = c1.selectbox("Xスケール", ["linear", "log"])
    yscale = c2.selectbox("Yスケール", ["linear", "log"])

    c3, c4 = st.sidebar.columns(2)
    xmin_s = c3.text_input("Xmin (空欄で自動)", value="")
    xmax_s = c4.text_input("Xmax (空欄で自動)", value="")
    c5, c6 = st.sidebar.columns(2)
    ymin_s = c5.text_input("Ymin (空欄で自動)", value="")
    ymax_s = c6.text_input("Ymax (空欄で自動)", value="")

    def parse_opt_float(s):
        s = s.strip()
        return float(s) if s else None

    try:
        xmin, xmax = parse_opt_float(xmin_s), parse_opt_float(xmax_s)
        ymin, ymax = parse_opt_float(ymin_s), parse_opt_float(ymax_s)
    except ValueError:
        st.sidebar.error("軸範囲は数値で入力してください")
        st.stop()

    style_str = st.sidebar.text_input("scienceplotsスタイル(カンマ区切り)", value="science, ieee")
    style = [s.strip() for s in style_str.split(",") if s.strip()]

    with st.sidebar.expander("詳細設定"):
        legend_loc = st.selectbox("凡例の位置", ["(表示しない)"] + LEGEND_LOCS)
        fig_w = st.number_input("図の幅 (inch, 0で自動)", value=0.0, step=0.5)
        fig_h = st.number_input("図の高さ (inch, 0で自動)", value=0.0, step=0.5)
        tick_fontsize = st.number_input("目盛りフォントサイズ (0で自動)", value=0.0, step=1.0)
        grid_on = st.checkbox("グリッド表示", value=False)
        n_bins = st.number_input("ビン数 (ヒストグラムのみ)", value=100, step=10) if mode == "hist" else 100
        dpi = st.number_input("出力DPI", value=600, step=50)

    st.subheader("4. 系列の設定")
    if mode == "line":
        x_col = df.columns[0]
        candidate_cols = list(df.columns[1:])
        series = series_controls(candidate_cols, "line", "line")
    else:
        x_col = None
        candidate_cols = list(df.columns)
        series = series_controls(candidate_cols, "hist", "hist")

    if not series:
        st.warning("系列を1つ以上選択してください")
        st.stop()

    # ==================== 描画 ====================
    try:
        apply_style(style)
    except Exception as e:  # noqa: BLE001 (プロトタイプなので幅広く捕捉してUIに出す)
        st.error(f"スタイル適用に失敗しました ({style}): {e}\nLaTeXが必要なスタイルの場合、環境にLaTeXが無いと失敗します。")
        st.stop()

    figsize = (fig_w if fig_w > 0 else None, fig_h if fig_h > 0 else None)
    fig, ax = plt.subplots(figsize=figsize if all(figsize) else None)

    try:
        if mode == "line":
            defaults = {"color": None, "linestyle": "-", "linewidth": 1.0, "marker": "o", "markersize": 4}
            for col, overrides in series.items():
                spec = merge_series_spec(col, overrides, defaults)
                ls = None if spec["linestyle"] == "None" else spec["linestyle"]
                mk = None if spec["marker"] == "None" else spec["marker"]
                ax.plot(
                    df[x_col], df[col],
                    marker=mk, markersize=spec["markersize"],
                    linewidth=spec["linewidth"], linestyle=ls,
                    label=spec["label"], color=spec["color"],
                )
            ax.set_xlabel(xlabel)
        else:
            columns = list(series)
            bin_min = xmin if xmin is not None else df[columns].min().min()
            bin_max = xmax if xmax is not None else df[columns].max().max()
            if xscale == "log":
                if bin_min <= 0:
                    raise ValueError(f"xscaleがlogの場合、xminは正の値である必要がある (xmin={bin_min})")
                ratio = bin_max / bin_min
                bin_edges = [bin_min * ratio ** (i / n_bins) for i in range(int(n_bins) + 1)]
            else:
                bin_edges = [bin_min + i * (bin_max - bin_min) / n_bins for i in range(int(n_bins) + 1)]

            defaults = {"color": None, "alpha": 0.6}
            for col, overrides in series.items():
                spec = merge_series_spec(col, overrides, defaults)
                ax.hist(df[col], bins=bin_edges, alpha=spec["alpha"], color=spec["color"], label=spec["label"])
            ax.set_xlabel(xlabel)

        ax.set_ylabel(ylabel)
        ax.set_xscale(xscale)
        ax.set_yscale(yscale)
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        if legend_loc != "(表示しない)":
            ax.legend(frameon=False, loc=legend_loc)
        if grid_on:
            ax.grid(True, alpha=0.3)
        if tick_fontsize > 0:
            ax.tick_params(labelsize=tick_fontsize)
        fig.tight_layout()
    except Exception as e:  # noqa: BLE001
        st.error(f"描画に失敗しました: {e}")
        st.stop()

    st.subheader("5. プレビュー")
    st.pyplot(fig, width="content")

    buf = io.BytesIO()
    fig.savefig(buf, format="pdf", dpi=dpi)
    default_out = f"{Path(source_name).stem}_{'plot' if mode == 'line' else 'hist'}.pdf"
    st.download_button("PDFをダウンロード", data=buf.getvalue(), file_name=default_out, mime="application/pdf")

    with st.expander("スクリプト用の設定 (plot_csv.py / plot_histogram.py 用)", expanded=False):
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
        if mode == "hist":
            lines.append(f"N_BINS = {int(n_bins)!r}")
        st.code("\n".join(lines), language="python")


if __name__ == "__main__":
    main()
