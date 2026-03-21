---
name: alphaxiv-search
description: "alphaxiv MCP を使った効率的な学術論文検索のナレッジベース。コンテキスト爆発を防ぎつつ最大限の網羅性を実現するツール選択・バッチ戦略・Neo4j投入パターンを提供。学術論文リサーチ、情報ギャップ分析、ナレッジグラフ拡充時にプロアクティブに使用。alphaxiv MCPツールを呼ぶ前に必ず参照すること。"
---

# alphaxiv Search Skill

alphaxiv MCP を使った学術論文検索の効率化ナレッジベース。

## なぜこのスキルが必要か

alphaxiv MCP は 250万件超の arXiv 論文を検索できる強力なツールだが、
ツール選択を誤るとコンテキストウィンドウを一瞬で消費し、セッションが破綻する。
このスキルは **最小トークンで最大網羅性** を実現するための戦略を提供する。

## ツール選択ガイド（重要度順）

### Tier 1: `embedding_similarity_search` — 主力ツール

| 項目 | 値 |
|------|-----|
| 出力サイズ | ~200-400 tokens/件 × 最大25件 |
| 合計 | ~5,000-10,000 tokens |
| 用途 | コンセプト・手法・研究領域の意味的検索 |
| 推奨度 | **常に最初に使う** |

クエリは **2-3文の詳細な記述** が必要。キーワードではなく、研究領域を多角的に描写する。

```
良い例: "Research on transformer architectures using self-attention mechanisms
for sequence modeling. Papers covering attention-based neural networks,
positional encodings, and applications to NLP tasks like translation."

悪い例: "transformer attention"
```

**返却内容**: タイトル、著者、所属、Abstract冒頭、arXiv ID、訪問数/いいね数、公開日
→ Neo4j投入に必要な情報は **これだけで十分**。

### Tier 2: `full_text_papers_search` — 補助ツール（注意必要）

| 項目 | 値 |
|------|-----|
| 出力サイズ | ~500-2,000 tokens/件 × 最大20件 |
| 合計 | ~10,000-40,000 tokens |
| 用途 | 特定キーワード・手法名・著者名のピンポイント検索 |
| 推奨度 | **embedding_similarity_search で不足時のみ** |

「Matching Snippets」が含まれるためサイズが大きい。
クエリは **3-4語の短いキーワード** が最適。

```
良い例: "FinGPT BloombergGPT financial foundation model"
悪い例: "Research on financial foundation models that process text and numerical data..."
```

### Tier 3: `get_paper_content` — 詳細取得（厳選使用）

| 項目 | 値 |
|------|-----|
| 出力サイズ | ~5,000-30,000 tokens/件 |
| 合計 | 1件で巨大 |
| 用途 | 特定論文のMethod/Claim詳細抽出 |
| 推奨度 | **1セッションで最大2-3件** |

以下の場合のみ使用する:
- Neo4jに **詳細なClaim/PerformanceEvidence** を投入する必要がある
- 論文の **Method/Architectureの詳細** が不明
- ユーザーが **特定論文の内容を質問** している

### Tier 4: `agentic_paper_retrieval` — 原則使用しない

| 項目 | 値 |
|------|-----|
| 出力サイズ | 予測不能（マルチターン検索） |
| 合計 | 数千〜数万tokens、時間も不定 |
| 用途 | 公式は「他ツールと並列使用」推奨だが実用上リスク大 |
| 推奨度 | **使わない**。embedding_similarity_searchで代替 |

## バッチ戦略

### 並列数の制限

| ツール | 最大並列数 | 理由 |
|--------|----------|------|
| `embedding_similarity_search` | **4件** | 合計 ~40,000 tokens で安全圏 |
| `full_text_papers_search` | **2件** | snippets が重いため控えめに |
| `get_paper_content` | **1件** | 1件で数万tokens |
| 混合 | embedding×3 + full_text×1 | バランス型 |

### 多領域検索のパターン

8領域を検索する場合:

```
バッチ1: embedding_similarity_search × 4（領域1-4）
  ↓ 結果確認、重複排除
バッチ2: embedding_similarity_search × 4（領域5-8）
  ↓ 結果確認
バッチ3: full_text_papers_search × 2（カバー不足の領域のみ）
```

**原則**: 1バッチの合計推定トークンが 50,000 を超えないようにする。

## 検索ワークフロー

### Phase 1: ギャップ分析（Neo4j照会）

既存データを確認し、情報ギャップを特定する。

```cypher
-- 既存Source一覧（URL/タイトル）
MATCH (s:Source) WHERE s.source_type = 'paper'
RETURN s.title, s.url ORDER BY s.title

-- Topic別カバレッジ
MATCH (t:Topic)<-[:TAGGED]-(s:Source)
RETURN t.name, count(s) AS sources ORDER BY sources DESC

-- Method分布
MATCH (m:Method) RETURN m.method_type, count(m) ORDER BY count(m) DESC
```

### Phase 2: 検索実行

1. ギャップ領域ごとに `embedding_similarity_search` のクエリを作成
2. 4件以下の並列バッチで実行
3. 結果からNeo4jに未登録のarXiv IDを抽出

### Phase 3: 重複排除

検索結果の arXiv ID を既存Source.urlと照合:

```cypher
MATCH (s:Source)
WHERE s.url CONTAINS '2402.12659'  -- arXiv IDで部分一致
RETURN s.title, s.url
```

### Phase 4: Neo4j投入

`embedding_similarity_search` の結果から直接投入可能なフィールド:

| 検索結果フィールド | Neo4j Source プロパティ |
|------------------|----------------------|
| title（論文タイトル） | `title` |
| arXiv Id | `source_id`（`src-{arXivId}`形式）、`url`（`https://arxiv.org/abs/{arXivId}`） |
| Abstract | `abstract` |
| Authors | `authors` |
| Organizations | → Entity ノードに分割投入 |
| Published | `published` |

**MERGE ベースで冪等投入**:

```cypher
UNWIND $papers AS p
MERGE (s:Source {source_id: p.id})
SET s.title = p.title, s.url = p.url, s.source_type = 'paper',
    s.authors = p.authors, s.abstract = p.abstract,
    s.created_at = datetime()
```

### Phase 5: リレーション構築

- `Source -[:TAGGED]-> Topic` — テーマタグ付け
- `Source -[:MAKES_CLAIM]-> Claim` — 主要知見（Abstractから抽出）
- `Source -[:USES_METHOD]-> Method` — 使用手法

## クエリテンプレート

### embedding_similarity_search 用クエリの書き方

**構造**: [研究領域の説明 1文] + [含めるべきキー手法/概念 1文] + [応用文脈 1文]

```
テンプレート:
"Research on {メイン手法/テーマ} for {応用領域}.
Papers covering {関連手法1}, {関連手法2}, and {関連手法3}
applied to {具体的タスク1} and {具体的タスク2}."
```

### 分野別クエリ例

| 分野 | クエリ |
|------|--------|
| ポートフォリオ構築 | "LLM-driven portfolio construction and asset allocation optimization. Research on using language models to generate investor views for Black-Litterman model, AI-based portfolio rebalancing, and end-to-end portfolio management with LLM agents." |
| リスク管理 | "AI and machine learning for financial risk management in investment portfolios. Research on deep learning for VaR and CVaR estimation, tail risk prediction, and AI-driven dynamic hedging strategies." |
| 市場レジーム | "Market regime detection using machine learning for investment strategy adaptation. Hidden Markov models, change-point detection with deep learning, and LLM-based regime classification from macroeconomic data." |
| 約定最適化 | "Optimal trade execution and market microstructure with AI agents. RL for order execution minimizing market impact, transaction cost analysis with ML, and smart order routing." |

## アンチパターン

| やってはいけないこと | 代わりにすること |
|---------------------|----------------|
| `get_paper_content` を5件以上並列呼び出し | 本当に必要な1-2件だけ取得 |
| `agentic_paper_retrieval` を使う | `embedding_similarity_search` で代替 |
| 8領域を全部同時に検索 | 4件ずつ2バッチに分割 |
| `full_text_papers_search` に長文クエリ | 3-4語のキーワードに絞る |
| 検索結果をそのまま会話に展開 | 必要なメタデータだけ抽出してNeo4j投入 |
| 既存DBとの重複チェックなしで投入 | arXiv IDでMERGE |

## 使用判断フロー

```
ユーザーの要求
  ├─ 「論文を調べて」「リサーチして」「ギャップを埋めて」
  │   → Phase 1-5 の全ワークフロー実行
  │
  ├─ 「この論文の詳細を教えて」（特定のarXiv ID指定）
  │   → get_paper_content × 1件のみ
  │
  ├─ 「〜に関する論文ある？」（軽い質問）
  │   → embedding_similarity_search × 1件のみ
  │
  └─ 「Neo4jを論文で拡充して」
      → Phase 1 でギャップ特定 → Phase 2-5
```
