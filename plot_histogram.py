#!/usr/bin/env python3

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import scienceplots  # noqa: F401  (plt.style.use が参照する)

from plot_csv import _UNSET, resolve, resolve_labels


# ==================== 各種設定はここで変更する ====================

CSV_PATH = Path("input.csv")            # 入力CSVファイル

SERIES = ["Series1", "Series2", "Series3"]         # ヒストグラム化する系列名(CSVの列名)
LABELS = None                          # 凡例名。Noneなら全てCSVの列名。数が足りない分もCSVの列名で補う

XLABEL = "X"                           # X軸ラベル
YLABEL = "Y"                           # Y軸ラベル

XMIN, XMAX = None, None                # X軸(ビン)の範囲 (Noneならデータから自動)
YMIN, YMAX = None, None                # Y軸の範囲 (Noneならデータから自動)

XSCALE = "linear"                      # X軸のスケール ("linear" または "log")
YSCALE = "linear"                      # Y軸のスケール ("linear" または "log")

N_BINS = 100                           # ビン数
ALPHA = 0.6                            # ヒストグラムの透過度

STYLE = ["science", "ieee"]            # scienceplotsのスタイル

OUTPUT = None                          # 出力ファイル名。Noneなら <CSV_PATH>_hist.pdf
DPI = 600                              # 出力画像のDPI

# ===================================================================


def parse_args():
    parser = argparse.ArgumentParser(
        description="CSVの列からヒストグラムを作成する。未指定の項目はファイル冒頭のハードコード値を使う。",
    )
    parser.add_argument("csv", type=Path, nargs="?", default=_UNSET, help=f"入力CSVファイル (デフォルト: {CSV_PATH})")
    parser.add_argument("--series", "-s", nargs="+", default=_UNSET, help="ヒストグラム化する系列名(CSVの列名)")
    parser.add_argument("--labels", "-l", nargs="+", default=_UNSET, help="凡例名")
    parser.add_argument("--xlabel", default=_UNSET, help="X軸ラベル")
    parser.add_argument("--ylabel", default=_UNSET, help="Y軸ラベル")
    parser.add_argument("--xmin", type=float, default=_UNSET, help="X軸(ビン)の最小値")
    parser.add_argument("--xmax", type=float, default=_UNSET, help="X軸(ビン)の最大値")
    parser.add_argument("--ymin", type=float, default=_UNSET, help="Y軸の最小値")
    parser.add_argument("--ymax", type=float, default=_UNSET, help="Y軸の最大値")
    parser.add_argument("--xscale", choices=["linear", "log"], default=_UNSET, help="X軸のスケール")
    parser.add_argument("--yscale", choices=["linear", "log"], default=_UNSET, help="Y軸のスケール")
    parser.add_argument("--bins", type=int, default=_UNSET, dest="n_bins", help="ビン数")
    parser.add_argument("--alpha", type=float, default=_UNSET, help="ヒストグラムの透過度")
    parser.add_argument("--style", nargs="+", default=_UNSET, help="scienceplotsのスタイル")
    parser.add_argument("--output", "-o", type=Path, default=_UNSET, help="出力ファイル名")
    parser.add_argument("--dpi", type=int, default=_UNSET, help="出力画像のDPI")
    return parser.parse_args()


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
    n_bins = resolve(args.n_bins, N_BINS)
    alpha = resolve(args.alpha, ALPHA)
    style = resolve(args.style, STYLE)
    output = resolve(args.output, OUTPUT)
    dpi = resolve(args.dpi, DPI)

    df = pd.read_csv(csv_path)

    unknown = [s for s in series if s not in df.columns]
    if unknown:
        available = ", ".join(df.columns)
        raise SystemExit(f"未知の系列名: {unknown}\n利用可能な系列: {available}")

    labels = resolve_labels(series, labels)

    bin_min = xmin if xmin is not None else df[series].min().min()
    bin_max = xmax if xmax is not None else df[series].max().max()
    if xscale == "log":
        if bin_min <= 0:
            raise SystemExit(f"xscaleがlogの場合、xminは正の値である必要がある (xmin={bin_min})")
        ratio = bin_max / bin_min
        bin_edges = [bin_min * ratio ** (i / n_bins) for i in range(n_bins + 1)]
    else:
        bin_edges = [bin_min + i * (bin_max - bin_min) / n_bins for i in range(n_bins + 1)]

    plt.style.use(style)
    fig, ax = plt.subplots()

    for col, label in zip(series, labels):
        ax.hist(df[col], bins=bin_edges, alpha=alpha, label=label)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xscale(xscale)
    ax.set_yscale(yscale)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.legend(frameon=False)

    fig.tight_layout()

    output = output if output is not None else csv_path.with_name(f"{csv_path.stem}_hist.pdf")
    fig.savefig(output, dpi=dpi)
    print(f"saved: {output}")


if __name__ == "__main__":
    main()
