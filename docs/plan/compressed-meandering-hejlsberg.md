# 実装計画: kg-enrich-auto — 自律KGエンリッチメントスキル

## Context

Neo4j KG（bolt://localhost:7690）の論文カバレッジを自律的に拡充するスキル/コマンドを新規作成する。2026-03-21 の手動セッション（3時間で 120→701 論文、+100 Topic）の成功パターンを再現可能なスキルとして体系化する。指定終了時刻まで「ギャップ分析→検索→投入→接続→最適化」サイクルを自動継続する。

## 設計判断

### 1. ループ機構: 単一スキル内での明示的繰り返し指示

Claude Code スキルにはループプリミティブがないため、SKILL.md のプロンプト内で「Phase 2-6 を END_TIME まで繰り返せ」と明示指示する。`mcp__time__get_current_time` で毎サイクル開始時に時刻チェック。2026-03-21 セッションでもこの方式で 3 時間自律実行に成功済み。

### 2. データフロー: 直接 Cypher MERGE（graph-queue 不使用）

graph-queue パイプライン（emit-graph-queue → save-to-graph）はバッチ変換向け。自律サイクルではオーバーヘッドが大きいため、`mcp__neo4j-cypher__write_neo4j_cypher` で直接 MERGE する。ID 生成は `src/database/id_generator.py` を Bash 経由で呼び出し、決定論的 ID を保証。

### 3. 3フェーズ戦略（飽和対応）

2026-03-21 セッションで約 50 分で主要ギャップが埋まった知見に基づく:

| フェーズ | 時間配分 | 戦略 | 並列数 |
|---------|---------|------|-------|
| Broad Coverage | 0-40% | 孤立 Topic・薄い Topic を網羅的に埋める | 4 |
| Targeted Depth | 40-75% | Method カバレッジ・時系列ギャップを深掘り | 4 |
| Long-Tail Discovery | 75-100% | 未接続 Topic ペアのクロスドメイン検索 | 2-3 |

フェーズ遷移条件: 時間割合 AND 発見率 < 10% が 2 サイクル連続。

## 作成ファイル

```
.claude/
  commands/
    kg-enrich-auto.md                    # コマンドエントリポイント
  skills/
    kg-enrich-auto/
      SKILL.md                            # メインスキル（サイクル制御）
      gap-analysis.md                     # ギャップ検出 Cypher クエリ集
      query-templates.md                  # 検索クエリ生成テンプレート
      ingestion-cypher.md                 # MERGE Cypher パターン集
```

## 各ファイルの詳細仕様

### 1. `.claude/commands/kg-enrich-auto.md`

```yaml
---
description: Neo4j KGを学術論文で自動拡充（指定時間まで継続）
argument-hint: <duration> (例: "2h", "90m", "until 15:00")
---
```

処理:
1. `mcp__time__get_current_time(timezone="Asia/Tokyo")` で現在時刻取得
2. 引数から END_TIME（ISO 8601）を計算
   - "2h" / "2 hours" → 現在 + 2 時間
   - "90m" / "90 minutes" → 現在 + 90 分
   - "until 15:00" → 本日 15:00 JST
3. `kg-enrich-auto` スキルを END_TIME パラメータ付きで呼び出し

### 2. `.claude/skills/kg-enrich-auto/SKILL.md`

**allowed-tools**: `Read, Bash, Glob, Grep`（MCP ツールは環境から利用可能）

**使用 MCP ツール**:
- `mcp__neo4j-cypher__read_neo4j_cypher` — ギャップ分析
- `mcp__neo4j-cypher__write_neo4j_cypher` — MERGE 投入
- `mcp__alphaxiv__embedding_similarity_search` — 論文検索（主力、4 並列 max）
- `mcp__alphaxiv__full_text_papers_search` — 補助検索（2 並列 max）
- `mcp__time__get_current_time` — 時刻チェック

**サイクル構造**:

```
初期化
  ├─ END_TIME 記録
  ├─ Neo4j 接続テスト
  ├─ ベースライン指標取得（Source/Topic/Method/Claim 件数）
  └─ searched_queries = [], cycle_count = 0

メインループ（END_TIME まで繰り返し）
  ├─ 時刻チェック → 超過なら Final Report へ
  ├─ Phase 1: ギャップ分析（gap-analysis.md 参照）
  │   ├─ 5 次元のギャップ検出 Cypher を 3-5 本並列実行
  │   ├─ 優先度スコアリング（孤立 Topic=10, 薄い Topic=8-count, ...）
  │   └─ searched_queries と照合して既検索を除外
  ├─ Phase 2: クエリ生成（query-templates.md 参照）
  │   ├─ 上位 4 ギャップから embedding_similarity_search クエリ作成
  │   ├─ 各クエリ: 2-3 文の詳細記述（alphaxiv-search スキル準拠）
  │   └─ searched_queries に追加
  ├─ Phase 3: 検索実行
  │   ├─ embedding_similarity_search × 4 並列
  │   ├─ 結果から arXiv ID・タイトル・著者・Abstract・公開日を抽出
  │   └─ 既存 Source と arXiv ID で重複排除
  ├─ Phase 4: Neo4j 投入（ingestion-cypher.md 参照）
  │   ├─ ID 生成: Bash で id_generator.py 呼び出し
  │   ├─ MERGE Source ノード
  │   ├─ MERGE Author ノード + AUTHORED_BY
  │   ├─ MERGE Topic ノード + TAGGED（ギャップコンテキストから）
  │   ├─ Abstract から Method 抽出 → MERGE Method + USES_METHOD
  │   └─ Abstract から Claim 抽出 → MERGE Claim + MAKES_CLAIM
  ├─ Phase 5: クロスコネクション
  │   ├─ 新 Source を既存 Topic にキーワードマッチで TAGGED
  │   └─ 新 Source を既存 Method にコンテンツマッチで USES_METHOD
  └─ Phase 6: サイクルサマリー
      ├─ cycle_count++, 累計指標更新
      ├─ discovery_rate = 新規 / 全結果
      ├─ フェーズ遷移判定
      └─ 中間データ破棄（指標と searched_queries のみ保持）

Final Report
  ├─ Neo4j から最終件数取得
  ├─ Before/After 比較テーブル出力
  ├─ セッション統計（サイクル数、検索数、飽和ポイント）
  ├─ 新規追加 Top 5 Topic
  └─ 残ギャップリスト（次回セッション用）
```

### 3. `.claude/skills/kg-enrich-auto/gap-analysis.md`

5 次元のギャップ検出:

| 優先度 | ギャップ種別 | Cypher クエリ | アクション |
|-------|------------|-------------|----------|
| 1 | 孤立 Topic | `MATCH (t:Topic) WHERE NOT (t)<-[:TAGGED]-(:Source) RETURN t.name` | Topic 名で論文検索 |
| 2 | 薄い Topic (<5 論文) | `MATCH (t:Topic)<-[:TAGGED]-(s:Source) WITH t, count(s) AS c WHERE c < 5 RETURN t.name, c ORDER BY c` | 既存 Topic を強化 |
| 3 | 未接続 Method | `MATCH (m:Method) WHERE NOT (m)<-[:USES_METHOD]-(:Source {source_type:'paper'}) RETURN m.name` | Method を使う論文検索 |
| 4 | 時系列ギャップ | `MATCH (s:Source {source_type:'paper'}) RETURN substring(s.published_at,0,4) AS year, count(s) ORDER BY year` | 過少年の論文補充 |
| 5 | クロスドメイン | 共有論文がない Topic ペアを検出 | 創造的クエリで long-tail 発掘 |

スコアリング: 孤立=10, 薄い=8-count, 未接続=6, 時系列=5, クロスドメイン=3

### 4. `.claude/skills/kg-enrich-auto/query-templates.md`

ギャップ種別ごとのクエリテンプレート（alphaxiv-search スキル準拠: 2-3 文記述）:

| ギャップ種別 | テンプレート |
|------------|------------|
| 孤立 Topic | "Research on {topic} in quantitative finance. Papers covering {topic} methods, applications to portfolio management, risk assessment, and trading strategies." |
| 薄い Topic | "Recent advances in {topic} for financial applications. Novel approaches including deep learning, RL, and LLM applications in {related_methods}." |
| 未接続 Method | "Academic papers using {method} for financial prediction and portfolio optimization. Studies applying {method} to stock selection, asset allocation, and market analysis." |
| 時系列ギャップ | "{topic} research published in {year}. Papers covering new datasets, improved architectures, and empirical evaluations." |
| クロスドメイン | "Intersection of {topic1} and {topic2} in quantitative finance. Research combining {topic1} techniques with {topic2} approaches for investment strategies." |

重複排除: searched_queries との Jaccard 類似度 > 0.7 なら修飾語追加（サブトピック指定、応用ドメイン変更、時期限定）。

### 5. `.claude/skills/kg-enrich-auto/ingestion-cypher.md`

全 MERGE パターン。ID 生成は Bash 経由:

```bash
# Source ID
uv run python -c "from database.id_generator import generate_source_id; print(generate_source_id('https://arxiv.org/abs/{arxiv_id}'))"

# Topic ID
uv run python -c "from database.id_generator import generate_topic_id; print(generate_topic_id('{name}', '{category}'))"

# Author ID
uv run python -c "from database.id_generator import generate_author_id; print(generate_author_id('{name}', 'academic'))"

# Claim ID
uv run python -c "from database.id_generator import generate_claim_id; print(generate_claim_id('{content}'))"
```

MERGE Cypher パターン:

```cypher
-- Source
MERGE (s:Source {source_id: $source_id})
SET s.title = $title, s.url = $url, s.source_type = 'paper',
    s.publisher = 'arXiv', s.published_at = $published_at,
    s.abstract = $abstract, s.command_source = 'kg-enrich-auto',
    s.fetched_at = datetime()

-- Author + AUTHORED_BY
MERGE (a:Author {author_id: $author_id})
SET a.name = $name, a.author_type = 'academic'
WITH a
MATCH (s:Source {source_id: $source_id})
MERGE (s)-[:AUTHORED_BY]->(a)

-- Topic + TAGGED
MERGE (t:Topic {topic_id: $topic_id})
SET t.name = $name, t.category = $category
WITH t
MATCH (s:Source {source_id: $source_id})
MERGE (s)-[:TAGGED]->(t)

-- Claim + MAKES_CLAIM
MERGE (c:Claim {claim_id: $claim_id})
SET c.content = $content, c.claim_type = 'research_finding',
    c.confidence = 'medium', c.created_at = datetime()
WITH c
MATCH (s:Source {source_id: $source_id})
MERGE (s)-[:MAKES_CLAIM]->(c)

-- Method + USES_METHOD
MERGE (m:Method {method_id: $method_id})
SET m.name = $name, m.method_type = $method_type
WITH m
MATCH (s:Source {source_id: $source_id})
MERGE (s)-[:USES_METHOD]->(m)
```

## コンテキストウィンドウ管理

**最重要**: 各サイクル後に検索結果と Cypher 出力を破棄し、指標のみ保持。

保持する状態:
- `searched_queries`: list[str]（50 件超で件数のみに圧縮）
- `cycle_count`, `total_papers_added`, `total_topics_added`
- `current_phase`, `discovery_rate_history`（直近 5 サイクルのみ）

破棄する状態:
- 検索結果全文（~40,000 tokens/サイクル）
- Cypher クエリ出力
- 中間解析データ

## エラーハンドリング

| エラー | 対応 |
|-------|------|
| Neo4j 接続断 | 3 回リトライ（10 秒間隔）→ 持続すればレポート出力して停止 |
| alphaxiv レートリミット | 30 秒待機、並列数を 2 に削減してリトライ |
| 検索結果 0 件 | ギャップを「exhausted」マーク、次のギャップへ |
| 発見率 < 2% が 3 サイクル連続（Long-Tail 中）| 品質サイクル 1 回実行後、Final Report 出力して早期終了 |
| Cypher 構文エラー | 該当論文をスキップ、ログ記録して継続 |

## 推定パフォーマンス

- サイクル所要時間: 3-5 分
- サイクルあたり新規論文: 15-60 本
- 1 時間あたりサイクル数: 12-20
- 2 時間セッション期待値: +200-600 論文

## 検証方法

1. **15 分テストセッション**: `/kg-enrich-auto 15m`
   - 3-5 サイクル完了を確認
   - Final Report が正しく生成されることを確認
   - Neo4j でノード増加を確認: `MATCH (s:Source {command_source: 'kg-enrich-auto'}) RETURN count(s)`

2. **フェーズ遷移テスト**: `/kg-enrich-auto 30m`
   - Broad → Targeted 遷移が発生することを確認

3. **冪等性テスト**: 同じセッションを 2 回実行
   - 2 回目のサイクルでほぼ全て重複判定されることを確認

## 既存ファイル参照

| ファイル | 用途 |
|---------|------|
| `.claude/skills/alphaxiv-search/SKILL.md` | 検索戦略・ツール選択ガイド |
| `.claude/skills/save-to-graph/SKILL.md` | MERGE パターンのリファレンス |
| `src/database/id_generator.py` | 決定論的 ID 生成関数 |
| `src/academic/mapper.py` | 論文→graph-queue 変換のフィールドマッピング参照 |
| `docs/plan/2026-03-21_discussion-kg-paper-enrichment.md` | 実績データ（飽和タイミング、検索量） |
| `data/config/knowledge-graph-schema.yaml` | KG v2.2 スキーマ定義（SSoT） |

## 実装順序

1. `ingestion-cypher.md` — MERGE パターン（全コンポーネントの基盤）
2. `gap-analysis.md` — ギャップ検出クエリと優先度スコアリング
3. `query-templates.md` — 検索クエリ生成テンプレート
4. `SKILL.md` — メインスキル（上記 3 ファイルを参照するオーケストレーション）
5. `kg-enrich-auto.md` — コマンドエントリポイント
6. テスト: 15 分セッションで動作検証
