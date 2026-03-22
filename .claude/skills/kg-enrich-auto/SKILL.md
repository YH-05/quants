---
name: kg-enrich-auto
description: alphaxiv MCP で学術論文を自動検索し Neo4j KG に継続投入するスキル。指定終了時刻まで「ギャップ分析→検索→投入→接続→最適化」サイクルを繰り返す。/kg-enrich-auto コマンドで使用。
allowed-tools: Read, Bash, Glob, Grep
---

# kg-enrich-auto スキル

alphaxiv MCP から学術論文を自動検索し、Neo4j KG に継続投入する自律スキル。
指定された END_TIME まで「ギャップ分析→検索→投入→接続→最適化」サイクルを **決して停止せず** 繰り返す。

## 前提スキル参照

**実行前に必ず以下を読み込むこと:**
- `alphaxiv-search` スキル（ツール選択・バッチ戦略）

## 使用 MCP ツール

| ツール | 用途 |
|--------|------|
| `mcp__neo4j-cypher__read_neo4j_cypher` | ギャップ分析、重複チェック、ベースライン取得 |
| `mcp__neo4j-cypher__write_neo4j_cypher` | MERGE ベース冪等投入 |
| `mcp__alphaxiv__embedding_similarity_search` | 論文検索（主力、**4 並列 max**） |
| `mcp__alphaxiv__full_text_papers_search` | 補助検索（**2 並列 max**、必要時のみ） |
| `mcp__time__get_current_time` | 時刻チェック（毎サイクル開始時） |

## 初期化

コマンドから `END_TIME`（ISO 8601, Asia/Tokyo）が渡される。

### Step 1: 時刻記録

```
mcp__time__get_current_time(timezone="Asia/Tokyo") → START_TIME として記録
END_TIME を記録（コマンドから注入）
total_budget_minutes = (END_TIME - START_TIME) を分単位で計算
```

### Step 2: Neo4j 接続テスト

```cypher
RETURN 'ok' AS status
```

失敗時 → 「Neo4j に接続できません。quants-neo4j コンテナが起動していることを確認してください。」と表示して終了。

### Step 3: ベースライン指標取得

`./gap-analysis.md` のベースライン指標クエリを実行し、以下を記録:

```
baseline = {
  papers: N,
  topics: N,
  methods: N,
  claims: N,
  tagged: N,
  uses_method: N,
  makes_claim: N
}
```

### Step 4: 状態初期化

```
cycle_count = 0
total_papers_added = 0
total_topics_added = 0
total_claims_added = 0
searched_queries = []
current_phase = "broad"  // "broad" | "targeted" | "long_tail"
discovery_rate_history = []
```

### Step 5: 既存 Method 一覧取得

新 Method 作成時の重複防止のため、既存 Method をキャッシュ:

```cypher
MATCH (m:Method) RETURN m.method_id, m.name ORDER BY m.name
```

## メインループ

**以下の Phase 1-6 を END_TIME まで繰り返す。決して途中で停止しないこと。**

最終レポート用に **残り 5 分** を確保する。effective_end = END_TIME - 5 分。

---

### 時刻チェック

```
mcp__time__get_current_time(timezone="Asia/Tokyo") → current_time
if current_time >= effective_end:
  → Final Report へ
```

フェーズ判定:
```
elapsed_pct = (current_time - START_TIME) / total_budget_minutes * 100

if elapsed_pct < 40:
  current_phase = "broad"
elif elapsed_pct < 75:
  current_phase = "targeted"
else:
  current_phase = "long_tail"
```

---

### Phase 1: ギャップ分析

`./gap-analysis.md` を参照し、current_phase に応じたギャップ検出を実行。

1. Cypher クエリを **3-5 本並列**で実行（`read_neo4j_cypher`）
2. 結果を優先度スコアリング
3. searched_queries と照合し、既検索を除外
4. **上位 4 件**（long_tail フェーズは 2-3 件）を選択

**ギャップが 0 件の場合**:
- searched_queries をクリアして再検索
- それでも 0 件なら Final Report へ

---

### Phase 2: クエリ生成

`./query-templates.md` を参照し、上位ギャップからクエリを生成。

1. 各ギャップに対応するテンプレートを選択
2. 2-3 文の英語クエリを生成
3. searched_queries との重複チェック（類似度高ければ修飾パターン適用）
4. searched_queries に追加

---

### Phase 3: 検索実行

```
embedding_similarity_search × 4 並列で実行
```

各結果から以下を抽出:
- arXiv ID
- タイトル
- 著者リスト
- Abstract（冒頭部分）
- 公開日

**重複排除**: 既存 Source の URL と arXiv ID を照合

```cypher
MATCH (s:Source {source_type: 'paper'})
WHERE s.url CONTAINS $arxiv_id
RETURN s.source_id
```

重複を除いた新規論文のみを Phase 4 に渡す。

---

### Phase 4: Neo4j 投入

`./ingestion-cypher.md` を参照。

**各新規論文に対して以下を実行:**

#### 4.1 ID 生成

Bash でバッチ ID 生成:

```bash
uv run python -c "
from database.id_generator import generate_source_id, generate_author_id, generate_topic_id
import sys, json
papers = json.loads(sys.stdin.read())
for p in papers:
    url = f'https://arxiv.org/abs/{p[\"arxiv_id\"]}'
    print(json.dumps({
        'arxiv_id': p['arxiv_id'],
        'source_id': generate_source_id(url),
        'url': url
    }))
" <<'JSON'
[{"arxiv_id": "2303.09406"}, {"arxiv_id": "2401.01234"}]
JSON
```

#### 4.2 Source MERGE

```cypher
MERGE (s:Source {source_id: $source_id})
SET s.title = $title, s.url = $url, s.source_type = 'paper',
    s.publisher = 'arXiv', s.published_at = $published_at,
    s.abstract = $abstract, s.command_source = 'kg-enrich-auto',
    s.fetched_at = datetime()
```

#### 4.3 Author MERGE + AUTHORED_BY

著者ごとに ID 生成 → MERGE → リレーション作成。
**著者が 10 名以上の場合は筆頭著者 + ラスト著者のみ。**

#### 4.4 Topic MERGE + TAGGED

ギャップ分析で特定した Topic をそのまま使用。既存 Topic の topic_id を使う。
新規 Topic が必要な場合のみ ID 生成して MERGE。

#### 4.5 Claim 抽出 + MERGE + MAKES_CLAIM

Abstract から **1-2 件の主要知見** を抽出:
- 「〜を提案/提示する」型の主張
- 「〜を上回る/改善する」型の実証結果
- ID は `generate_claim_id(content)` で生成

#### 4.6 Method 抽出 + MERGE + USES_METHOD

Abstract から使用手法を特定し、既存 Method リストと照合:
- 既存 Method に該当 → その method_id で USES_METHOD
- 新規 Method → `method-{slug}` 形式の ID で MERGE

---

### Phase 5: クロスコネクション

新しく投入した Source を既存 Topic/Method にも接続。

1. 新 Source の Abstract と既存 Topic 名を比較
2. 関連性の高い Topic に TAGGED（**1 Source あたり最大 3 追加 Topic**）
3. 既存 Method との接続も同様に実施

---

### Phase 6: サイクルサマリー

```
cycle_count += 1
papers_this_cycle = (新規投入数)
total_papers_added += papers_this_cycle
discovery_rate = papers_this_cycle / (全検索結果数) if 全検索結果数 > 0 else 0
discovery_rate_history.append(discovery_rate)  // 直近 5 件のみ保持
```

**フェーズ遷移判定**:
```
if discovery_rate < 0.10 が 2 サイクル連続 AND current_phase != "long_tail":
  current_phase を次のフェーズに進める
```

**早期終了判定**:
```
if discovery_rate < 0.02 が 3 サイクル連続 AND current_phase == "long_tail":
  → Final Report へ（飽和到達）
```

**コンテキスト管理（最重要）**:

サイクル完了後、以下を **必ず実行**:
1. 検索結果の全文を記憶から破棄する
2. Cypher クエリ出力を記憶から破棄する
3. 保持するのは上記の指標のみ
4. searched_queries が 50 件を超えたら件数のみに圧縮

**サイクルログ出力**:
```
Cycle {cycle_count} | Phase: {current_phase} | +{papers_this_cycle} papers | Rate: {discovery_rate:.0%} | Total: {total_papers_added}
```

---

**→ 時刻チェックに戻り、次のサイクルを開始する**

---

## Final Report

### Step 1: 最終指標取得

ベースライン指標クエリを再実行 → final として記録。

### Step 2: レポート出力

```markdown
## KG Enrichment Session Complete

| 指標 | Before | After | Delta |
|------|--------|-------|-------|
| Source (paper) | {baseline.papers} | {final.papers} | +{delta} |
| Topic | {baseline.topics} | {final.topics} | +{delta} |
| Method | {baseline.methods} | {final.methods} | +{delta} |
| Claim | {baseline.claims} | {final.claims} | +{delta} |
| TAGGED | {baseline.tagged} | {final.tagged} | +{delta} |
| USES_METHOD | {baseline.uses_method} | {final.uses_method} | +{delta} |
| MAKES_CLAIM | {baseline.makes_claim} | {final.makes_claim} | +{delta} |

### Session Stats
- Duration: {actual_duration}
- Cycles completed: {cycle_count}
- Phase distribution: Broad {n1}, Targeted {n2}, Long-Tail {n3}
- Total searches: {len(searched_queries)}
- Average discovery rate: {avg_rate:.0%}

### Top 5 New Topics Added
1. {topic_name} ({paper_count} papers)
...

### Remaining Gaps (for next session)
1. {gap_description}
...
```

## エラーハンドリング

| エラー | 対応 |
|-------|------|
| Neo4j 接続断 | 3 回リトライ（10 秒間隔）→ 持続すればレポート出力して停止 |
| alphaxiv エラー | 30 秒待機、並列数を 2 に削減してリトライ |
| 検索結果 0 件 | ギャップを「exhausted」マーク、次のギャップへ |
| Cypher 構文エラー | 該当論文をスキップ、ログ記録して継続 |
| コンテキスト圧迫 | searched_queries を圧縮、中間データ破棄を強化 |

## 禁止事項

1. **CREATE は使用禁止** — 全書き込みは MERGE
2. **ID の推測禁止** — 必ず id_generator.py で生成
3. **get_paper_content の使用禁止** — Abstract で十分
4. **agentic_paper_retrieval の使用禁止** — コンテキスト爆発リスク
5. **サイクル途中での停止禁止** — END_TIME まで継続
6. **検索結果の保持禁止** — 各サイクル後に破棄

## リソースファイル

| ファイル | 内容 |
|---------|------|
| `./gap-analysis.md` | 5 次元ギャップ検出 Cypher クエリと優先度スコアリング |
| `./query-templates.md` | ギャップ種別ごとの検索クエリ生成テンプレート |
| `./ingestion-cypher.md` | MERGE Cypher パターン集と ID 生成コマンド |
