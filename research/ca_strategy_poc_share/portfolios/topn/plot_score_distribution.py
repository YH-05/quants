"""
CA Strategy PoC — スコア分布 箱ひげ図
採用/非採用 × セクター別プロット
"""

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import seaborn as sns

# macOS 日本語フォント設定
plt.rcParams["font.family"] = [
    "Hiragino Sans",
    "YuGothic",
    "Arial Unicode MS",
    "DejaVu Sans",
]

BASE = Path(__file__).parent.parent.parent  # portfolios/topn → ca_strategy_poc_share

# ─── データ読み込み ───────────────────────────────────────────────

# 1. phase2_scored.json → 銘柄ごと平均確信度
with (BASE / "scores/phase2_scored.json").open() as f:
    scored: dict[str, list] = json.load(f)

ticker_scores: dict[str, float] = {}
for ticker, claims in scored.items():
    if claims:
        ticker_scores[ticker] = sum(c["final_confidence"] for c in claims) / len(claims)

# 2. universe.json → セクターマップ
with (BASE / "config/universe.json").open() as f:
    universe = json.load(f)

sector_map: dict[str, str] = {
    t["ticker"]: t["gics_sector"] for t in universe["tickers"]
}

# 3. top30_score_weighted.csv → 採用銘柄セット
top30: set[str] = set()
with (BASE / "portfolios/topn/top30_score_weighted.csv").open() as f:
    for row in csv.DictReader(f):
        top30.add(row["ticker"])

# ─── DataFrame 構築 ──────────────────────────────────────────────

rows = []
for ticker, score in ticker_scores.items():
    sector = sector_map.get(ticker, "Unknown")
    adopted = "採用 (Top 30)" if ticker in top30 else "非採用"
    rows.append({"ticker": ticker, "score": score, "sector": sector, "status": adopted})

df = pd.DataFrame(rows)

# セクター表示名を短縮
sector_labels = {
    "Information Technology": "IT",
    "Health Care": "Health",
    "Consumer Staples": "Staples",
    "Consumer Discretionary": "Discret.",
    "Financials": "Financials",
    "Industrials": "Industrials",
    "Utilities": "Utilities",
    "Energy": "Energy",
    "Materials": "Materials",
    "Telecommunication Services": "Telecom",
}
df["sector_short"] = df["sector"].map(sector_labels).fillna(df["sector"])

# セクターを採用数の多い順に並べる
sector_order = (
    df[df["status"] == "採用 (Top 30)"]
    .groupby("sector_short")
    .size()
    .sort_values(ascending=False)
    .index.tolist()
)
# 採用ゼロのセクターを後ろに追加
all_sectors = df["sector_short"].unique().tolist()
for s in all_sectors:
    if s not in sector_order:
        sector_order.append(s)

df["sector_short"] = pd.Categorical(
    df["sector_short"], categories=sector_order, ordered=True
)

# ─── カラーパレット ──────────────────────────────────────────────

PALETTE = {"採用 (Top 30)": "#E63946", "非採用": "#457B9D"}
CUTOFF = 0.657  # Top30 実カットオフライン（30位 META vs 31位 COL の境界）

# ─── Figure レイアウト ───────────────────────────────────────────

fig = plt.figure(figsize=(18, 12), facecolor="#F8F9FA")
fig.suptitle(
    "CA Strategy PoC — スコア分布（Phase 2 スコアリング結果）",
    fontsize=16,
    fontweight="bold",
    y=0.98,
)

# GridSpec: 上段=採用/非採用比較(全体), 下段=セクター別
gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.4], hspace=0.38, wspace=0.06)

ax_top_left = fig.add_subplot(gs[0, 0])  # 採用/非採用 箱ひげ
ax_top_right = fig.add_subplot(gs[0, 1])  # 採用/非採用 バイオリン
ax_bottom = fig.add_subplot(gs[1, :])  # セクター別 箱ひげ

# ─── Plot 1: 採用/非採用 箱ひげ図 ───────────────────────────────

sns.boxplot(
    data=df,
    x="status",
    y="score",
    hue="status",
    palette=PALETTE,
    order=["採用 (Top 30)", "非採用"],
    width=0.5,
    linewidth=1.5,
    flierprops=dict(marker="o", markersize=4, alpha=0.4),
    legend=False,
    ax=ax_top_left,
)
sns.stripplot(
    data=df,
    x="status",
    y="score",
    hue="status",
    palette=PALETTE,
    order=["採用 (Top 30)", "非採用"],
    size=4,
    alpha=0.35,
    jitter=True,
    legend=False,
    ax=ax_top_left,
)
ax_top_left.axhline(CUTOFF, color="gray", linestyle="--", linewidth=1.2, alpha=0.7)
ax_top_left.text(
    1.52,
    CUTOFF + 0.005,
    f"カットオフ {CUTOFF:.3f}\n(30位 META)",
    fontsize=8,
    color="gray",
)
ax_top_left.set_title("採用 vs 非採用 — スコア分布", fontsize=12, fontweight="bold")
ax_top_left.set_xlabel("")
ax_top_left.set_ylabel("平均確信度スコア", fontsize=10)
ax_top_left.set_ylim(0.10, 0.96)
ax_top_left.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))
ax_top_left.set_facecolor("#FFFFFF")
ax_top_left.grid(axis="y", alpha=0.3)

# 統計注釈
for i, status in enumerate(["採用 (Top 30)", "非採用"]):
    sub = df[df["status"] == status]["score"]
    ax_top_left.text(
        i,
        sub.max() + 0.015,
        f"n={len(sub)}\nμ={sub.mean():.3f}\nmed={sub.median():.3f}",
        ha="center",
        fontsize=7.5,
        color="#333333",
    )

# ─── Plot 2: 採用/非採用 バイオリン図 ───────────────────────────

sns.violinplot(
    data=df,
    x="status",
    y="score",
    hue="status",
    palette=PALETTE,
    order=["採用 (Top 30)", "非採用"],
    inner="quartile",
    linewidth=1.2,
    legend=False,
    ax=ax_top_right,
)
ax_top_right.axhline(CUTOFF, color="gray", linestyle="--", linewidth=1.2, alpha=0.7)
ax_top_right.set_title(
    "採用 vs 非採用 — スコア密度分布", fontsize=12, fontweight="bold"
)
ax_top_right.set_xlabel("")
ax_top_right.set_ylabel("")
ax_top_right.set_ylim(0.10, 0.96)
ax_top_right.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))
ax_top_right.set_facecolor("#FFFFFF")
ax_top_right.grid(axis="y", alpha=0.3)

# ─── Plot 3: セクター × 採用ステータス 箱ひげ図 ─────────────────

sns.boxplot(
    data=df,
    x="sector_short",
    y="score",
    hue="status",
    hue_order=["採用 (Top 30)", "非採用"],
    palette=PALETTE,
    order=sector_order,
    width=0.65,
    linewidth=1.2,
    flierprops=dict(marker="o", markersize=3.5, alpha=0.4),
    gap=0.15,
    ax=ax_bottom,
)
sns.stripplot(
    data=df,
    x="sector_short",
    y="score",
    hue="status",
    hue_order=["採用 (Top 30)", "非採用"],
    palette=PALETTE,
    order=sector_order,
    size=4,
    alpha=0.30,
    jitter=True,
    dodge=True,
    legend=False,
    ax=ax_bottom,
)

# カットオフライン
ax_bottom.axhline(CUTOFF, color="gray", linestyle="--", linewidth=1.2, alpha=0.8)
ax_bottom.text(
    len(sector_order) - 0.5,
    CUTOFF + 0.012,
    f"カットオフ {CUTOFF:.3f} (30位 META)",
    fontsize=8,
    color="gray",
    ha="right",
)

# セクター別採用数の注釈
for i, sector in enumerate(sector_order):
    n_adopted = len(
        df[(df["sector_short"] == sector) & (df["status"] == "採用 (Top 30)")]
    )
    n_total = len(df[df["sector_short"] == sector])
    ax_bottom.text(
        i,
        0.115,
        f"{n_adopted}/{n_total}",
        ha="center",
        fontsize=7.5,
        color="#555555",
    )

ax_bottom.text(
    -0.6,
    0.115,
    "採用/総数:",
    ha="center",
    fontsize=7.5,
    color="#555555",
    fontweight="bold",
)

ax_bottom.set_title(
    "セクター別 × 採用ステータス — スコア分布", fontsize=12, fontweight="bold"
)
ax_bottom.set_xlabel("セクター", fontsize=10)
ax_bottom.set_ylabel("平均確信度スコア", fontsize=10)
ax_bottom.set_ylim(0.08, 0.96)
ax_bottom.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))
ax_bottom.set_facecolor("#FFFFFF")
ax_bottom.grid(axis="y", alpha=0.3)
ax_bottom.tick_params(axis="x", rotation=20)
ax_bottom.legend(title="ステータス", loc="upper right", fontsize=9)

# ─── フッター注釈 ─────────────────────────────────────────────────

fig.text(
    0.5,
    0.01,
    "データソース: CA Strategy PoC Phase 2 — scores/phase2_scored.json（330銘柄）｜"
    "スコア = 銘柄内全主張の final_confidence 単純平均",
    ha="center",
    fontsize=8,
    color="#888888",
)

# ─── 保存 ─────────────────────────────────────────────────────────

out_path = Path(__file__).parent / "score_distribution.png"
plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Saved: {out_path}")
plt.close()
