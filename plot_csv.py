#!/usr/bin/env python3

import argparse
from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pandas as pd
import scienceplots  # noqa: F401  (plt.style.use が参照する)
from cycler import cycler


# ==================== 各種設定はここで変更する ====================

CSV_PATH = Path("input.csv")            # 入力CSVファイル

SERIES = {
    "Series1": {},
    "Series2": {},
}
# プロットする系列。キー: CSVの列名 (この順にプロットする)、値: 系列ごとに上書きする設定の辞書。
# 指定できるキー: label, color, linestyle, linewidth, marker, markersize
# 未指定のキーは下のDEFAULT_*の値を使う。colorを指定しなければTableau配色から自動で割り当てる。
# 例:
# SERIES = {
#     "Series1": {"label": "系列1", "color": "tab:red", "marker": "s"},
#     "Series2": {"linestyle": "--", "linewidth": 0.5},
# }

XLABEL = None                          # X軸ラベル。Noneならデータから自動
YLABEL = "None"                        # Y軸ラベル

XMIN, XMAX = None, None                # X軸の範囲 (Noneならデータから自動)
YMIN, YMAX = None, None                # Y軸の範囲 (Noneならデータから自動)

XSCALE = "linear"                      # X軸のスケール ("linear" または "log")
YSCALE = "linear"                      # Y軸のスケール ("linear" または "log")

DEFAULT_LINESTYLE = "-"                # 系列ごとに指定がない場合の線種
DEFAULT_LINEWIDTH = 1.0                # 系列ごとに指定がない場合の線の太さ（0にするとマーカーのみ）
DEFAULT_MARKER = "o"                   # 系列ごとに指定がない場合のマーカーの形状
DEFAULT_MARKERSIZE = 4                 # 系列ごとに指定がない場合のマーカーサイズ

STYLE = ["science", "ieee"]            # scienceplotsのスタイル

OUTPUT = None                          # 出力ファイル名。Noneなら <CSV_PATH>_plot.pdf
DPI = 600                              # 出力画像のDPI

# ===================================================================


_UNSET = object()  # コマンドライン引数が指定されたかどうかを判定するための番人


def parse_args():
    parser = argparse.ArgumentParser(
        description="CSVから系列を選んでグラフを作成する。未指定の項目はファイル冒頭のハードコード値を使う。",
    )
    parser.add_argument("csv", type=Path, nargs="?", default=_UNSET, help=f"入力CSVファイル (デフォルト: {CSV_PATH})")
    parser.add_argument(
        "--series", "-s", nargs="+", default=_UNSET,
        help="プロットする系列名(CSVの列名)。この順にプロットする。SERIES辞書にあれば系列ごとの設定を使う",
    )
    parser.add_argument("--xlabel", default=_UNSET, help="X軸ラベル")
    parser.add_argument("--ylabel", default=_UNSET, help="Y軸ラベル")
    parser.add_argument("--xmin", type=float, default=_UNSET, help="X軸の最小値")
    parser.add_argument("--xmax", type=float, default=_UNSET, help="X軸の最大値")
    parser.add_argument("--ymin", type=float, default=_UNSET, help="Y軸の最小値")
    parser.add_argument("--ymax", type=float, default=_UNSET, help="Y軸の最大値")
    parser.add_argument("--xscale", choices=["linear", "log"], default=_UNSET, help="X軸のスケール")
    parser.add_argument("--yscale", choices=["linear", "log"], default=_UNSET, help="Y軸のスケール")
    parser.add_argument("--linestyle", default=_UNSET, help="線種(系列ごとに指定がない場合のデフォルト)")
    parser.add_argument("--linewidth", type=float, default=_UNSET, help="線の太さ(系列ごとに指定がない場合のデフォルト)")
    parser.add_argument("--marker", default=_UNSET, help="マーカーの形状(系列ごとに指定がない場合のデフォルト)")
    parser.add_argument("--markersize", type=float, default=_UNSET, help="マーカーサイズ(系列ごとに指定がない場合のデフォルト)")
    parser.add_argument("--style", nargs="+", default=_UNSET, help="scienceplotsのスタイル")
    parser.add_argument("--output", "-o", type=Path, default=_UNSET, help="出力ファイル名")
    parser.add_argument("--dpi", type=int, default=_UNSET, help="出力画像のDPI")
    return parser.parse_args()


def resolve(cli_value, hardcoded_value):
    return hardcoded_value if cli_value is _UNSET else cli_value


def select_series(series, selected_columns):
    """CLIで--seriesが指定された場合、その並び順・部分集合に絞り込む。
    SERIES辞書に無い列名は、系列ごとの上書き設定なし(デフォルトのみ)として扱う。
    """
    if selected_columns is None:
        return series
    return {col: series.get(col, {}) for col in selected_columns}


def merge_series_spec(col, overrides, defaults):
    """系列ごとの上書き設定(overrides)をdefaultsにマージし、描画に使うパラメータ一式を作る。"""
    spec = dict(defaults)
    spec["label"] = col
    spec.update(overrides)
    return spec


def apply_style(style):
    """scienceplotsのスタイル(フォント等)を適用しつつ、デフォルトの配色をTableauパレットにする。"""
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
        raise SystemExit(f"未知の系列名: {unknown}\n利用可能な系列: {available}")

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
