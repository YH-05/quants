"""
CA Strategy PoC — スコア分布 + KB2 パターン分析 統合プロット

レイアウト:
  上段: 採用 vs 非採用 スコア箱ひげ図（+ サマリー統計）
  中段: セクター × 採用ステータス 箱ひげ図
  下段: KB2 パターン別 マッチ頻度（採用 vs 非採用）
"""

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import seaborn as sns

plt.rcParams["font.family"] = [
    "Hiragino Sans",
    "YuGothic",
    "Arial Unicode MS",
    "DejaVu Sans",
]

BASE = Path(__file__).parent.parent.parent  # portfolios/topn → ca_strategy_poc_share

# ═══════════════════════════════════════════════════════════
# データ読み込み
# ═══════════════════════════════════════════════════════════

with (BASE / "scores/phase2_scored.json").open() as f:
    scored: dict[str, list] = json.load(f)

with (BASE / "config/universe.json").open() as f:
    universe = json.load(f)

top30: set[str] = set()
with (BASE / "portfolios/topn/top30_score_weighted.csv").open() as f:
    for row in csv.DictReader(f):
        top30.add(row["ticker"])

sector_map = {t["ticker"]: t["gics_sector"] for t in universe["tickers"]}
all_claims = [(t, c) for t, claims in scored.items() for c in claims]

# ─── 銘柄スコア DataFrame ────────────────────────────────────────

ticker_scores: dict[str, float] = {
    t: sum(c["final_confidence"] for c in cs) / len(cs)
    for t, cs in scored.items()
    if cs
}

SECTOR_LABELS = {
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

rows = []
for ticker, score in ticker_scores.items():
    sector = sector_map.get(ticker, "Unknown")
    status = "採用 (Top 30)" if ticker in top30 else "非採用"
    rows.append(
        {
            "ticker": ticker,
            "score": score,
            "sector_short": SECTOR_LABELS.get(sector, sector),
            "status": status,
        }
    )

df = pd.DataFrame(rows)

sector_order = (
    df[df["status"] == "採用 (Top 30)"]
    .groupby("sector_short")
    .size()
    .sort_values(ascending=False)
    .index.tolist()
)
for s in df["sector_short"].unique():
    if s not in sector_order:
        sector_order.append(s)

df["sector_short"] = pd.Categorical(
    df["sector_short"], categories=sector_order, ordered=True
)

# ─── KB2 集計 ────────────────────────────────────────────────────


def normalize_kb2(pid: str) -> str | None:
    for roman in ["IV", "III", "II", "V"]:
        if re.search(r"[Pp]attern[_\s]?" + roman + r"(?![A-Z])", pid):
            return roman
    m = re.search(r"[Pp]attern[_\s]?([A-G])", pid)
    if m:
        return m.group(1)
    if "F-T" in pid:
        return "F"
    return None


kb2: dict = defaultdict(lambda: defaultdict(lambda: {"count": 0, "matched": 0}))

for ticker, c in all_claims:
    status = "採用 (Top 30)" if ticker in top30 else "非採用"
    for p in c.get("kb2_patterns", []):
        canon = normalize_kb2(p["pattern_id"])
        if canon:
            kb2[canon][status]["count"] += 1
            if p.get("matched"):
                kb2[canon][status]["matched"] += 1

NEGATIVE_PATTERNS = list("ABCDFG")
POSITIVE_PATTERNS = ["II", "III", "IV", "V"]
PATTERN_ORDER = NEGATIVE_PATTERNS + POSITIVE_PATTERNS

PATTERN_LABELS = {
    "A": "A\n結果→原因混同",
    "B": "B\n業界共通能力",
    "C": "C\n因果の飛躍",
    "D": "D\n定性的のみ",
    "F": "F\n戦略混同",
    "G": "G\n競合比較欠如",
    "II": "II\nCAGR直接接続",
    "III": "III\n能力 > 結果",
    "IV": "IV\n構造的市場ポジション",
    "V": "V\nその他高評価",
}

STATUSES = ["採用 (Top 30)", "非採用"]
total_claims_by_status = Counter(
    "採用 (Top 30)" if t in top30 else "非採用" for t, _ in all_claims
)

rows_a = []
for pat in PATTERN_ORDER:
    for status in STATUSES:
        s = kb2[pat][status]
        n_claims = total_claims_by_status[status]
        match_rate = (s["matched"] / n_claims * 1000) if n_claims else 0
        rows_a.append(
            {
                "pattern": pat,
                "status": status,
                "match_rate_per1k": match_rate,
                "matched": s["matched"],
            }
        )

df_a = pd.DataFrame(rows_a)
df_a["pattern"] = pd.Categorical(
    df_a["pattern"], categories=PATTERN_ORDER, ordered=True
)

# ═══════════════════════════════════════════════════════════
# 定数
# ═══════════════════════════════════════════════════════════

PALETTE = {"採用 (Top 30)": "#E63946", "非採用": "#457B9D"}
CUTOFF = 0.657

# ═══════════════════════════════════════════════════════════
# Figure レイアウト
# ═══════════════════════════════════════════════════════════

fig = plt.figure(figsize=(17, 20), facecolor="#F8F9FA")
fig.suptitle(
    "CA Strategy PoC — スコア分布 & KB2 パターン分析（Phase 2）",
    fontsize=15,
    fontweight="bold",
    y=0.992,
)

gs = fig.add_gridspec(
    3,
    5,
    height_ratios=[1.05, 1.35, 1.2],
    hspace=0.42,
    wspace=0.05,
    left=0.07,
    right=0.97,
    top=0.97,
    bottom=0.04,
)

ax_box = fig.add_subplot(gs[0, 1:4])  # 採用/非採用 箱ひげ（中央寄せ）
ax_sector = fig.add_subplot(gs[1, :])  # セクター別 箱ひげ
ax_a1 = fig.add_subplot(gs[2, :])  # KB2 パターン頻度

# ═══════════════════════════════════════════════════════════
# 上段左: 採用 vs 非採用 箱ひげ図
# ═══════════════════════════════════════════════════════════

sns.boxplot(
    data=df,
    x="status",
    y="score",
    hue="status",
    palette=PALETTE,
    order=STATUSES,
    width=0.45,
    linewidth=1.6,
    flierprops=dict(marker="o", markersize=4, alpha=0.4),
    legend=False,
    ax=ax_box,
)
sns.stripplot(
    data=df,
    x="status",
    y="score",
    hue="status",
    palette=PALETTE,
    order=STATUSES,
    size=4,
    alpha=0.35,
    jitter=True,
    legend=False,
    ax=ax_box,
)

ax_box.axhline(CUTOFF, color="gray", ls="--", lw=1.3, alpha=0.7)
ax_box.text(
    1.52,
    CUTOFF + 0.006,
    f"カットオフ {CUTOFF:.3f}\n(30位 META)",
    fontsize=8,
    color="gray",
)

for i, status in enumerate(STATUSES):
    sub = df[df["status"] == status]["score"]
    ax_box.text(
        i,
        sub.max() + 0.018,
        f"n={len(sub)}\nμ={sub.mean():.3f}\nmed={sub.median():.3f}",
        ha="center",
        fontsize=8,
        color="#333333",
    )

ax_box.set_title("採用 vs 非採用 — スコア分布", fontsize=12, fontweight="bold")
ax_box.set_xlabel("")
ax_box.set_ylabel("平均確信度スコア", fontsize=10)
ax_box.set_ylim(0.10, 0.96)
ax_box.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))
ax_box.set_facecolor("#FFFFFF")
ax_box.grid(axis="y", alpha=0.3)

# ═══════════════════════════════════════════════════════════
# 中段: セクター × 採用ステータス 箱ひげ図
# ═══════════════════════════════════════════════════════════

sns.boxplot(
    data=df,
    x="sector_short",
    y="score",
    hue="status",
    hue_order=STATUSES,
    palette=PALETTE,
    order=sector_order,
    width=0.65,
    linewidth=1.2,
    flierprops=dict(marker="o", markersize=3.5, alpha=0.4),
    gap=0.15,
    ax=ax_sector,
)
sns.stripplot(
    data=df,
    x="sector_short",
    y="score",
    hue="status",
    hue_order=STATUSES,
    palette=PALETTE,
    order=sector_order,
    size=3.5,
    alpha=0.30,
    jitter=True,
    dodge=True,
    legend=False,
    ax=ax_sector,
)

ax_sector.axhline(CUTOFF, color="gray", ls="--", lw=1.2, alpha=0.8)
ax_sector.text(
    len(sector_order) - 0.5,
    CUTOFF + 0.013,
    f"カットオフ {CUTOFF:.3f} (30位 META)",
    fontsize=8,
    color="gray",
    ha="right",
)

for i, sector in enumerate(sector_order):
    n_a = len(df[(df["sector_short"] == sector) & (df["status"] == "採用 (Top 30)")])
    n_t = len(df[df["sector_short"] == sector])
    ax_sector.text(i, 0.115, f"{n_a}/{n_t}", ha="center", fontsize=7.5, color="#555555")

ax_sector.text(
    -0.65,
    0.115,
    "採用/総数:",
    ha="center",
    fontsize=7.5,
    color="#555555",
    fontweight="bold",
)

ax_sector.set_title(
    "セクター別 × 採用ステータス — スコア分布", fontsize=12, fontweight="bold"
)
ax_sector.set_xlabel("セクター", fontsize=10)
ax_sector.set_ylabel("平均確信度スコア", fontsize=10)
ax_sector.set_ylim(0.08, 0.96)
ax_sector.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))
ax_sector.set_facecolor("#FFFFFF")
ax_sector.grid(axis="y", alpha=0.3)
ax_sector.tick_params(axis="x", rotation=15)
ax_sector.legend(title="ステータス", loc="upper right", fontsize=9)

# ═══════════════════════════════════════════════════════════
# 下段: KB2 パターン別 マッチ頻度
# ═══════════════════════════════════════════════════════════

n_neg = len(NEGATIVE_PATTERNS)
n_pos = len(POSITIVE_PATTERNS)

sns.barplot(
    data=df_a,
    x="pattern",
    y="match_rate_per1k",
    hue="status",
    hue_order=STATUSES,
    palette=PALETTE,
    width=0.72,
    order=PATTERN_ORDER,
    ax=ax_a1,
)

# 減点/加点ゾーン背景
ax_a1.axvspan(-0.5, n_neg - 0.5, color="#FFF0F0", alpha=0.55, zorder=0)
ax_a1.axvspan(n_neg - 0.5, n_neg + n_pos - 0.5, color="#F0FFF0", alpha=0.55, zorder=0)
ax_a1.axvline(n_neg - 0.5, color="#AAAAAA", lw=1.2, ls="--")

ymax = df_a["match_rate_per1k"].max() * 1.12
ax_a1.text(
    n_neg / 2 - 0.5,
    ymax * 0.97,
    "← 減点パターン（A〜G）",
    ha="center",
    fontsize=9.5,
    color="#C62828",
    fontweight="bold",
)
ax_a1.text(
    n_neg + n_pos / 2 - 0.5,
    ymax * 0.97,
    "加点パターン（II〜V）→",
    ha="center",
    fontsize=9.5,
    color="#2E7D32",
    fontweight="bold",
)

# 各バーに件数アノテーション
for bar_group in ax_a1.containers:
    ax_a1.bar_label(bar_group, fmt="%.0f", fontsize=7, padding=2, color="#444444")

ax_a1.set_xticks(range(len(PATTERN_ORDER)))
ax_a1.set_xticklabels(
    [PATTERN_LABELS.get(p, p) for p in PATTERN_ORDER],
    fontsize=8.5,
    ha="center",
)
ax_a1.set_title(
    "KB2 パターン別 マッチ頻度（1,000クレームあたり発動回数）\n"
    "採用銘柄は加点パターン(IV・III)が突出、非採用銘柄は減点パターン(A・B・D)が高頻度で発動",
    fontsize=11,
    fontweight="bold",
)
ax_a1.set_xlabel("KB2 パターン", fontsize=10)
ax_a1.set_ylabel("マッチ数 / 1,000クレーム", fontsize=10)
ax_a1.set_ylim(0, ymax * 1.08)
ax_a1.legend(title="", fontsize=9, loc="upper right")
ax_a1.set_facecolor("#FFFFFF")
ax_a1.grid(axis="y", alpha=0.3)

# ═══════════════════════════════════════════════════════════
# フッター
# ═══════════════════════════════════════════════════════════

fig.text(
    0.5,
    0.005,
    "データソース: CA Strategy PoC Phase 2 — scores/phase2_scored.json"
    "（330銘柄 / 2,548クレーム）｜スコア = 銘柄内全主張の final_confidence 単純平均",
    ha="center",
    fontsize=7.5,
    color="#888888",
)

# ═══════════════════════════════════════════════════════════
# 保存
# ═══════════════════════════════════════════════════════════

out_path = Path(__file__).parent / "combined.png"
plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Saved: {out_path}")
plt.close()
