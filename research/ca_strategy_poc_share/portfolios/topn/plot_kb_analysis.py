"""
CA Strategy PoC — KB スコアリング詳細分析
Plot A: KB2 パターン別 マッチ率 + 平均調整量（採用 vs 非採用）
Plot B: 主張数 vs 平均スコア 散布図（claim_type 内訳つき）
Plot C: KB1 ルール別 通過率 ヒートマップ（採用 vs 非採用）
"""

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

# 日本語フォント
plt.rcParams["font.family"] = [
    "Hiragino Sans",
    "YuGothic",
    "Arial Unicode MS",
    "DejaVu Sans",
]

BASE = Path(__file__).parent.parent.parent  # ca_strategy_poc_share

# ─── データ読み込み ───────────────────────────────────────────────

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


# ─── 正規化ヘルパー ───────────────────────────────────────────────


def normalize_kb2(pid: str) -> str | None:
    """KB2 pattern_id を A〜G / II〜V に正規化"""
    for roman in ["IV", "III", "II", "V"]:
        if re.search(r"[Pp]attern[_\s]?" + roman + r"(?![A-Z])", pid):
            return roman
    m = re.search(r"[Pp]attern[_\s]?([A-G])", pid)
    if m:
        return m.group(1)
    if "F-T" in pid:
        return "F"
    return None


def normalize_kb1(rid: str) -> str | None:
    """KB1 rule_id を rule_01〜rule_12 に正規化"""
    m = re.search(r"rule[_]?(\d+)", rid, re.IGNORECASE)
    if m:
        return f"rule_{int(m.group(1)):02d}"
    return None


# ─── 集計 ────────────────────────────────────────────────────────

# KB2: {pattern: {status: {count, matched, adj_sum}}}
kb2: dict[str, dict[str, dict]] = defaultdict(
    lambda: defaultdict(lambda: {"count": 0, "matched": 0, "adj_sum": 0.0})
)
# KB1: {rule: {status: {pass, total}}}
kb1: dict[str, dict[str, dict]] = defaultdict(
    lambda: defaultdict(lambda: {"pass": 0, "total": 0})
)
# ticker level
ticker_level: dict[str, dict] = defaultdict(
    lambda: {"scores": [], "n": 0, "ca": 0, "cagr": 0, "factual": 0}
)

for ticker, c in all_claims:
    status = "採用 (Top 30)" if ticker in top30 else "非採用"
    score = c["final_confidence"]

    ticker_level[ticker]["scores"].append(score)
    ticker_level[ticker]["n"] += 1
    ct = c.get("claim_type", "")
    if "competitive" in ct:
        ticker_level[ticker]["ca"] += 1
    elif "cagr" in ct.lower():
        ticker_level[ticker]["cagr"] += 1
    elif "factual" in ct.lower():
        ticker_level[ticker]["factual"] += 1

    for p in c.get("kb2_patterns", []):
        canon = normalize_kb2(p["pattern_id"])
        if canon:
            kb2[canon][status]["count"] += 1
            if p.get("matched"):
                kb2[canon][status]["matched"] += 1
                kb2[canon][status]["adj_sum"] += p.get("adjustment", 0.0)

    for ev in c.get("kb1_evaluations", []):
        canon = normalize_kb1(ev["rule_id"])
        if canon:
            kb1[canon][status]["total"] += 1
            if ev.get("result"):
                kb1[canon][status]["pass"] += 1

# ─── Plot A 用 DataFrame ─────────────────────────────────────────

NEGATIVE_PATTERNS = list("ABCDFG")  # E は件数極小なので除く
POSITIVE_PATTERNS = ["II", "III", "IV", "V"]
PATTERN_ORDER = NEGATIVE_PATTERNS + POSITIVE_PATTERNS

PATTERN_LABELS = {
    "A": "A\n結果→原因\n混同",
    "B": "B\n業界共通\n能力",
    "C": "C\n因果\n飛躍",
    "D": "D\n定性的\nのみ",
    "F": "F\n戦略\n混同",
    "G": "G\n競合比較\n欠如",
    "II": "II\nCAGR\n直接接続",
    "III": "III\n能力>\n結果",
    "IV": "IV\n構造的\n市場ポジション",
    "V": "V\nその他\n高評価",
}

STATUSES = ["採用 (Top 30)", "非採用"]

# クレーム1000件あたりのマッチ率 & 平均調整量
total_claims_by_status = Counter(
    "採用 (Top 30)" if t in top30 else "非採用" for t, _ in all_claims
)

rows_a = []
for pat in PATTERN_ORDER:
    for status in STATUSES:
        s = kb2[pat][status]
        n_claims = total_claims_by_status[status]
        match_rate_per1k = (s["matched"] / n_claims * 1000) if n_claims else 0
        avg_adj = (s["adj_sum"] / s["matched"]) if s["matched"] else 0
        rows_a.append(
            {
                "pattern": pat,
                "label": PATTERN_LABELS.get(pat, pat),
                "status": status,
                "match_rate_per1k": match_rate_per1k,
                "avg_adj": avg_adj,
                "matched": s["matched"],
            }
        )

df_a = pd.DataFrame(rows_a)
df_a["pattern"] = pd.Categorical(
    df_a["pattern"], categories=PATTERN_ORDER, ordered=True
)

# ─── Plot B 用 DataFrame ─────────────────────────────────────────

rows_b = []
for ticker, d in ticker_level.items():
    if not d["scores"]:
        continue
    status = "採用 (Top 30)" if ticker in top30 else "非採用"
    avg_score = sum(d["scores"]) / len(d["scores"])
    total = d["n"]
    ca_ratio = d["ca"] / total if total else 0
    rows_b.append(
        {
            "ticker": ticker,
            "avg_score": avg_score,
            "n_claims": total,
            "ca": d["ca"],
            "cagr": d["cagr"],
            "factual": d["factual"],
            "ca_ratio": ca_ratio,
            "status": status,
        }
    )

df_b = pd.DataFrame(rows_b)

# ─── Plot C 用 DataFrame ─────────────────────────────────────────

KB1_LABELS = {
    "rule_01": "rule 01\n能力≠結果",
    "rule_03": "rule 03\nCornered\nResource",
    "rule_04": "rule 04\n定量的\nエビデンス",
    "rule_05": "rule 05\nCAGR\n接続",
    "rule_06": "rule 06\n構造的\nvs補完的",
    "rule_07": "rule 07\n競合との\n差別化",
    "rule_08": "rule 08\n戦略≠\n優位性",
    "rule_10": "rule 10\n時点制約\n(PoiT)",
    "rule_11": "rule 11\n業界構造\n適合",
    "rule_12": "rule 12\nメカニズム\n説明",
}

# 最低10件以上のルールのみ対象
TARGET_RULES = [
    r
    for r in sorted(kb1.keys())
    if sum(kb1[r][s]["total"] for s in STATUSES) >= 10 and r in KB1_LABELS
]

heatmap_data = {}
annot_data = {}
for rule in TARGET_RULES:
    heatmap_data[rule] = {}
    annot_data[rule] = {}
    for status in STATUSES:
        s = kb1[rule][status]
        rate = 100 * s["pass"] / s["total"] if s["total"] else float("nan")
        heatmap_data[rule][status] = rate
        annot_data[rule][status] = f"{rate:.0f}%\n({s['pass']}/{s['total']})"

df_c = pd.DataFrame(heatmap_data, index=STATUSES).T
df_c.index = [KB1_LABELS[r] for r in TARGET_RULES]

annot_df = pd.DataFrame(annot_data, index=STATUSES).T
annot_df.index = [KB1_LABELS[r] for r in TARGET_RULES]

# ─── Figure レイアウト ───────────────────────────────────────────

PALETTE = {"採用 (Top 30)": "#E63946", "非採用": "#457B9D"}

fig = plt.figure(figsize=(22, 20), facecolor="#F8F9FA")
fig.suptitle(
    "CA Strategy PoC — KB スコアリング詳細分析",
    fontsize=17,
    fontweight="bold",
    y=0.99,
)

gs = fig.add_gridspec(
    3,
    12,
    height_ratios=[1.1, 1.0, 1.0],
    hspace=0.50,
    wspace=0.05,
    left=0.07,
    right=0.97,
    top=0.96,
    bottom=0.05,
)

ax_a1 = fig.add_subplot(gs[0, :6])  # A: マッチ率
ax_a2 = fig.add_subplot(gs[0, 6:])  # A: 平均調整量
ax_b = fig.add_subplot(gs[1, :])  # B: 散布図
ax_c = fig.add_subplot(gs[2, :9])  # C: ヒートマップ（通過率）
ax_cd = fig.add_subplot(gs[2, 9:11])  # C: 差分列


# ══════════════════════════════════════════════════════
# Plot A-1: KB2 パターン別 マッチ頻度（1000クレームあたり）
# ══════════════════════════════════════════════════════

neg_mask = df_a["pattern"].isin(NEGATIVE_PATTERNS)
pos_mask = df_a["pattern"].isin(POSITIVE_PATTERNS)

sns.barplot(
    data=df_a,
    x="pattern",
    y="match_rate_per1k",
    hue="status",
    hue_order=STATUSES,
    palette=PALETTE,
    width=0.7,
    order=PATTERN_ORDER,
    ax=ax_a1,
)

# 減点/加点ゾーンの背景色
n_neg = len(NEGATIVE_PATTERNS)
n_pos = len(POSITIVE_PATTERNS)
ax_a1.axvspan(-0.5, n_neg - 0.5, color="#FFECEC", alpha=0.4, zorder=0)
ax_a1.axvspan(n_neg - 0.5, n_neg + n_pos - 0.5, color="#E8F5E9", alpha=0.4, zorder=0)
ax_a1.axvline(n_neg - 0.5, color="gray", lw=1, ls="--", alpha=0.6)

ax_a1.text(
    n_neg / 2 - 0.5,
    ax_a1.get_ylim()[1] * 0.95,
    "← 減点パターン",
    ha="center",
    fontsize=9,
    color="#C62828",
    alpha=0.8,
)
ax_a1.text(
    n_neg + n_pos / 2 - 0.5,
    ax_a1.get_ylim()[1] * 0.95,
    "加点パターン →",
    ha="center",
    fontsize=9,
    color="#2E7D32",
    alpha=0.8,
)

ax_a1.set_title(
    "A-1. KB2 パターン別 マッチ頻度\n（1,000クレームあたり発動回数）",
    fontsize=11,
    fontweight="bold",
)
ax_a1.set_xlabel("KB2 パターン", fontsize=9)
ax_a1.set_ylabel("マッチ数 / 1,000クレーム", fontsize=9)
ax_a1.set_xticks(range(len(PATTERN_ORDER)))
ax_a1.set_xticklabels(
    [PATTERN_LABELS.get(p, p) for p in PATTERN_ORDER],
    fontsize=8,
    ha="center",
)
ax_a1.legend(title="", fontsize=8, loc="upper right")
ax_a1.set_facecolor("#FFFFFF")
ax_a1.grid(axis="y", alpha=0.3)


# ══════════════════════════════════════════════════════
# Plot A-2: KB2 パターン別 マッチ時平均調整量
# ══════════════════════════════════════════════════════

df_a_matched = df_a[df_a["matched"] > 0].copy()

sns.barplot(
    data=df_a_matched,
    x="pattern",
    y="avg_adj",
    hue="status",
    hue_order=STATUSES,
    palette=PALETTE,
    width=0.7,
    order=PATTERN_ORDER,
    ax=ax_a2,
)

ax_a2.axhline(0, color="black", lw=0.8)
ax_a2.axvspan(-0.5, n_neg - 0.5, color="#FFECEC", alpha=0.4, zorder=0)
ax_a2.axvspan(n_neg - 0.5, n_neg + n_pos - 0.5, color="#E8F5E9", alpha=0.4, zorder=0)
ax_a2.axvline(n_neg - 0.5, color="gray", lw=1, ls="--", alpha=0.6)

ax_a2.set_title(
    "A-2. KB2 パターン別 マッチ時平均調整量", fontsize=11, fontweight="bold"
)
ax_a2.set_xlabel("KB2 パターン", fontsize=9)
ax_a2.set_ylabel("平均 adjustment（確信度への加減算）", fontsize=9)
ax_a2.set_xticks(range(len(PATTERN_ORDER)))
ax_a2.set_xticklabels(
    [PATTERN_LABELS.get(p, p) for p in PATTERN_ORDER],
    fontsize=8,
    ha="center",
)
ax_a2.legend(title="", fontsize=8, loc="upper right")
ax_a2.set_facecolor("#FFFFFF")
ax_a2.grid(axis="y", alpha=0.3)
ax_a2.yaxis.set_major_formatter(mticker.FormatStrFormatter("%+.2f"))


# ══════════════════════════════════════════════════════
# Plot B: 主張数 vs 平均スコア 散布図
# ══════════════════════════════════════════════════════

# claim_type 積み上げ棒グラフ（インセット）
for status, grp in df_b.groupby("status"):
    color = PALETTE[status]
    marker = "D" if "採用" in status else "o"
    zorder = 5 if "採用" in status else 3
    ms = 80 if "採用" in status else 35
    ax_b.scatter(
        grp["n_claims"],
        grp["avg_score"],
        c=color,
        marker=marker,
        s=ms,
        alpha=0.75,
        edgecolors="white",
        linewidths=0.5,
        label=status,
        zorder=zorder,
    )

# 回帰線（全体・採用・非採用）
for status, grp in df_b.groupby("status"):
    if len(grp) < 3:
        continue
    color = PALETTE[status]
    x, y = grp["n_claims"].values, grp["avg_score"].values
    z = np.polyfit(x, y, 1)
    p = np.poly1d(z)
    xr = np.linspace(x.min(), x.max(), 100)
    ls = "-" if "採用" in status else "--"
    ax_b.plot(xr, p(xr), color=color, ls=ls, lw=1.5, alpha=0.8)

# カットオフ
CUTOFF = 0.657
ax_b.axhline(CUTOFF, color="gray", ls="--", lw=1.2, alpha=0.7)
ax_b.text(
    df_b["n_claims"].max() + 0.3,
    CUTOFF + 0.006,
    f"カットオフ {CUTOFF:.3f}",
    fontsize=8,
    color="gray",
)

# 注目銘柄ラベル
LABEL_TICKERS = {
    "PPL",
    "GOOG",
    "AAPL",
    "MHFI",
    "DIS",
    "BAYN",
    "NKE",
    "ROG",
    "NESN",
    "META",
}
for _, row in df_b.iterrows():
    if row["ticker"] in LABEL_TICKERS:
        ax_b.annotate(
            row["ticker"],
            (row["n_claims"], row["avg_score"]),
            xytext=(5, 3),
            textcoords="offset points",
            fontsize=7.5,
            color="#333333",
            arrowprops=dict(arrowstyle="-", color="gray", lw=0.5),
        )

ax_b.set_title(
    "B. 主張数 vs 平均スコア（銘柄別）\n"
    "◆ 採用, ● 非採用 ／ 回帰線: 実線=採用, 破線=非採用",
    fontsize=11,
    fontweight="bold",
)
ax_b.set_xlabel("主張数（claim_count）", fontsize=10)
ax_b.set_ylabel("平均確信度スコア", fontsize=10)
ax_b.set_ylim(0.08, 0.96)
ax_b.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))
ax_b.legend(fontsize=9, loc="upper right")
ax_b.set_facecolor("#FFFFFF")
ax_b.grid(alpha=0.25)

# インセット: claim_type 構成比（採用 vs 非採用 積み上げ棒グラフ）
ax_ins = ax_b.inset_axes([0.72, 0.05, 0.26, 0.45])
ct_data = df_b.groupby("status")[["ca", "cagr", "factual"]].sum()
ct_data_pct = ct_data.div(ct_data.sum(axis=1), axis=0) * 100
ct_data_pct = ct_data_pct.rename(
    columns={"ca": "competitive_advantage", "cagr": "CAGR接続", "factual": "factual"}
)
ct_data_pct.T.plot(
    kind="bar",
    stacked=True,
    color={"採用 (Top 30)": "#E63946", "非採用": "#457B9D"},
    ax=ax_ins,
    width=0.5,
    legend=False,
)
ax_ins.set_title("claim_type\n構成比 (%)", fontsize=7.5, pad=3)
ax_ins.set_xlabel("")
ax_ins.set_ylabel("")
ax_ins.tick_params(axis="x", labelsize=6.5, rotation=30)
ax_ins.tick_params(axis="y", labelsize=6.5)
ax_ins.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
ax_ins.set_facecolor("#FAFAFA")
ax_ins.grid(axis="y", alpha=0.3)


# ══════════════════════════════════════════════════════
# Plot C: KB1 ルール別 通過率 ヒートマップ
# ══════════════════════════════════════════════════════

# 差分列を追加（採用 - 非採用の通過率差）
df_c_plot = df_c[["採用 (Top 30)", "非採用"]].copy()
df_c_plot["採用優位\n(採用−非採用)"] = df_c_plot["採用 (Top 30)"] - df_c_plot["非採用"]

# 表示用アノテーション（同じ形状で差分列は pp 表示）
annot_full = annot_df[["採用 (Top 30)", "非採用"]].copy()
diff_vals = df_c_plot["採用優位\n(採用−非採用)"]
annot_full["採用優位\n(採用−非採用)"] = diff_vals.apply(
    lambda x: f"{x:+.1f}pp" if pd.notna(x) else "N/A"
)

# ヒートマップ本体（通過率列）
vmin, vmax = 30, 100
cmap_main = sns.light_palette("#2E7D32", as_cmap=True)

hm = sns.heatmap(
    df_c_plot[["採用 (Top 30)", "非採用"]],
    annot=annot_full[["採用 (Top 30)", "非採用"]],
    fmt="",
    cmap=cmap_main,
    vmin=vmin,
    vmax=vmax,
    linewidths=0.8,
    linecolor="white",
    annot_kws={"size": 9, "weight": "bold"},
    cbar_kws={"label": "通過率 (%)", "shrink": 0.7},
    ax=ax_c,
)

# 差分列：独立サブプロット
diff_values = df_c_plot["採用優位\n(採用−非採用)"].values
diff_annot = diff_values.reshape(-1, 1)
diff_labels = np.array([[f"{v:+.1f}pp"] for v in diff_values])

cmap_div = sns.diverging_palette(240, 10, as_cmap=True)
sns.heatmap(
    diff_annot,
    annot=diff_labels,
    fmt="",
    cmap=cmap_div,
    center=0,
    vmin=-50,
    vmax=50,
    linewidths=0.8,
    linecolor="white",
    annot_kws={"size": 9.5, "weight": "bold"},
    cbar=False,
    yticklabels=False,
    xticklabels=["採用−非採用\n通過率差"],
    ax=ax_cd,
)
ax_cd.tick_params(axis="x", labelsize=8.5, rotation=0)
ax_cd.set_ylabel("")

ax_c.set_title(
    "C. KB1 ルール別 通過率ヒートマップ（採用 vs 非採用）\n"
    "※ 通過率差が大きいルール = 採用/不採用を分ける判断軸",
    fontsize=11,
    fontweight="bold",
)
ax_c.set_xlabel("")
ax_c.set_ylabel("")
ax_c.tick_params(axis="x", labelsize=9, rotation=0)
ax_c.tick_params(axis="y", labelsize=8, rotation=0)


# ─── フッター ─────────────────────────────────────────────────────

fig.text(
    0.5,
    0.005,
    "データソース: CA Strategy PoC Phase 2 — scores/phase2_scored.json（330銘柄 / 2,548クレーム）",
    ha="center",
    fontsize=8,
    color="#888888",
)

# ─── 保存 ─────────────────────────────────────────────────────────

out_path = Path(__file__).parent / "kb_analysis.png"
plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Saved: {out_path}")
plt.close()
