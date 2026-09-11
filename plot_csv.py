#!/usr/bin/env python3

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import scienceplots  # noqa: F401  (plt.style.use が参照する)


# ==================== 各種設定はここで変更する ====================

CSV_PATH = Path("ping.csv")            # 入力CSVファイル

SERIES = ["Sim-n78", "Sim-n257"]       # プロットする系列名(CSVの列名)。指定した系列のみプロットする
LABELS = None                          # 凡例名。Noneなら全てCSVの列名。数が足りない分もCSVの列名で補う
                                        # 例: LABELS = ["Sim n78", "Sim n257"]

XLABEL = None                          # X軸ラベル。Noneならデータから自動
YLABEL = "RTT (ms)"                    # Y軸ラベル

XMIN, XMAX = None, None                # X軸の範囲 (Noneならデータから自動)
YMIN, YMAX = 0, 100                    # Y軸の範囲 (Noneならデータから自動)

XSCALE = "linear"                      # X軸のスケール ("linear" または "log")
YSCALE = "linear"                      # Y軸のスケール ("linear" または "log")

MARKERSIZE = 4                         # マーカーサイズ
LINEWIDTH = 1.0                        # 線の太さ（0にするとマーカーのみ）
MARKER = "o"                           # マーカーの形状

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
    parser.add_argument("--series", "-s", nargs="+", default=_UNSET, help="プロットする系列名(CSVの列名)")
    parser.add_argument("--labels", "-l", nargs="+", default=_UNSET, help="凡例名")
    parser.add_argument("--xlabel", default=_UNSET, help="X軸ラベル")
    parser.add_argument("--ylabel", default=_UNSET, help="Y軸ラベル")
    parser.add_argument("--xmin", type=float, default=_UNSET, help="X軸の最小値")
    parser.add_argument("--xmax", type=float, default=_UNSET, help="X軸の最大値")
    parser.add_argument("--ymin", type=float, default=_UNSET, help="Y軸の最小値")
    parser.add_argument("--ymax", type=float, default=_UNSET, help="Y軸の最大値")
    parser.add_argument("--xscale", choices=["linear", "log"], default=_UNSET, help="X軸のスケール")
    parser.add_argument("--yscale", choices=["linear", "log"], default=_UNSET, help="Y軸のスケール")
    parser.add_argument("--markersize", type=float, default=_UNSET, help="マーカーサイズ")
    parser.add_argument("--linewidth", type=float, default=_UNSET, help="線の太さ（0でマーカーのみ）")
    parser.add_argument("--marker", default=_UNSET, help="マーカーの形状")
    parser.add_argument("--style", nargs="+", default=_UNSET, help="scienceplotsのスタイル")
    parser.add_argument("--output", "-o", type=Path, default=_UNSET, help="出力ファイル名")
    parser.add_argument("--dpi", type=int, default=_UNSET, help="出力画像のDPI")
    return parser.parse_args()


def resolve(cli_value, hardcoded_value):
    return hardcoded_value if cli_value is _UNSET else cli_value


def resolve_labels(series, labels):
    if labels is None:
        return list(series)
    if len(labels) > len(series):
        raise ValueError(f"labelsの数({len(labels)})がseriesの数({len(series)})より多い")
    return list(labels) + list(series[len(labels):])


def main():
    args = parse_args()

    csv_path = resolve(args.csv, CSV_PATH)
    series = resolve(args.series, SERIES)
    labels = resolve(args.labels, LABELS)
    xlabel = resolve(args.xlabel, XLABEL)
    ylabel = resolve(args.ylabel, YLABEL)
    xmin = resolve(args.xmin, XMIN)
    xmax = resolve(args.xmax, XMAX)
    ymin = resolve(args.ymin, YMIN)
    ymax = resolve(args.ymax, YMAX)
    xscale = resolve(args.xscale, XSCALE)
    yscale = resolve(args.yscale, YSCALE)
    markersize = resolve(args.markersize, MARKERSIZE)
    linewidth = resolve(args.linewidth, LINEWIDTH)
    marker = resolve(args.marker, MARKER)
    style = resolve(args.style, STYLE)
    output = resolve(args.output, OUTPUT)
    dpi = resolve(args.dpi, DPI)

    df = pd.read_csv(csv_path)
    x_col = df.columns[0]

    unknown = [s for s in series if s not in df.columns[1:]]
    if unknown:
        available = ", ".join(df.columns[1:])
        raise SystemExit(f"未知の系列名: {unknown}\n利用可能な系列: {available}")

    labels = resolve_labels(series, labels)

    plt.style.use(style)
    fig, ax = plt.subplots()

    for col, label in zip(series, labels):
        ax.plot(
            df[x_col], df[col],
            marker=marker, markersize=markersize, linewidth=linewidth,
            label=label,
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
