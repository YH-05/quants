# ギャップ分析クエリ集

Neo4j KG の情報ギャップを 5 次元で検出し、優先度スコアリングで次の検索対象を決定する。

## 使用ツール

全クエリは `mcp__neo4j-cypher__read_neo4j_cypher` で実行する（読み取り専用）。

## ギャップ次元と Cypher クエリ

### 次元 1: 孤立 Topic（優先度スコア = 10）

Topic ノードが存在するが、論文（Source）が 1 本も TAGGED されていない。

```cypher
MATCH (t:Topic)
WHERE NOT EXISTS {
  MATCH (t)<-[:TAGGED]-(:Source {source_type: 'paper'})
}
RETURN t.name, t.category, t.topic_id
ORDER BY t.name
```

### 次元 2: 薄い Topic（優先度スコア = 8 - count）

論文が 5 本未満の Topic。count が少ないほどスコアが高い。

```cypher
MATCH (t:Topic)<-[:TAGGED]-(s:Source {source_type: 'paper'})
WITH t, count(s) AS paper_count
WHERE paper_count < 5
RETURN t.name, t.category, t.topic_id, paper_count
ORDER BY paper_count ASC, t.name
```

### 次元 3: 未接続 Method（優先度スコア = 6）

Method ノードが存在するが、論文が USES_METHOD で接続されていない。

```cypher
MATCH (m:Method)
WHERE NOT EXISTS {
  MATCH (m)<-[:USES_METHOD]-(:Source {source_type: 'paper'})
}
RETURN m.name, m.method_type, m.method_id
ORDER BY m.name
```

### 次元 4: 時系列ギャップ（優先度スコア = 5）

特定年の論文数が平均より大幅に少ない。特に最新年（2025-2026）が過少な場合に重要。

```cypher
MATCH (s:Source {source_type: 'paper'})
WHERE s.published_at IS NOT NULL
WITH substring(s.published_at, 0, 4) AS year, count(s) AS paper_count
RETURN year, paper_count
ORDER BY year
```

判定ロジック（LLM が実行）:
- 全年の平均 paper_count を算出
- 平均の 50% 未満の年をギャップとして抽出
- 2025-2026 年が平均未満なら優先度を +2 加算

### 次元 5: クロスドメイン（優先度スコア = 3）

共有論文がない Topic ペア。Long-Tail Discovery フェーズで使用。

```cypher
MATCH (t1:Topic)<-[:TAGGED]-(:Source {source_type: 'paper'})
WITH t1, count(*) AS c1
WHERE c1 >= 3
MATCH (t2:Topic)<-[:TAGGED]-(:Source {source_type: 'paper'})
WITH t1, t2, count(*) AS c2
WHERE c2 >= 3 AND id(t1) < id(t2)
  AND NOT EXISTS {
    MATCH (s:Source {source_type: 'paper'})-[:TAGGED]->(t1)
    MATCH (s)-[:TAGGED]->(t2)
  }
RETURN t1.name AS topic1, t2.name AS topic2
LIMIT 20
```

## ベースライン指標クエリ

サイクル開始前と Final Report で使用する指標取得クエリ。

```cypher
// 全体統計（1 クエリで取得）
MATCH (s:Source {source_type: 'paper'}) WITH count(s) AS papers
MATCH (t:Topic) WITH papers, count(t) AS topics
MATCH (m:Method) WITH papers, topics, count(m) AS methods
MATCH (c:Claim) WITH papers, topics, methods, count(c) AS claims
OPTIONAL MATCH ()-[r:TAGGED]->() WITH papers, topics, methods, claims, count(r) AS tagged
OPTIONAL MATCH ()-[r2:USES_METHOD]->() WITH papers, topics, methods, claims, tagged, count(r2) AS uses_method
OPTIONAL MATCH ()-[r3:MAKES_CLAIM]->() WITH papers, topics, methods, claims, tagged, uses_method, count(r3) AS makes_claim
RETURN papers, topics, methods, claims, tagged, uses_method, makes_claim
```

## 優先度スコアリングアルゴリズム

各サイクルの Phase 1 で以下のアルゴリズムを実行する。

### 入力

5 次元のクエリ結果（各次元に 0 個以上のギャップ候補）

### スコア計算

```
各ギャップ候補に対して:
  base_score = 次元別基本スコア（上記参照）

  // 薄い Topic の場合、count が少ないほど高スコア
  if 次元 == "薄い Topic":
    score = 8 - paper_count  // count=1 → 7, count=4 → 4

  // 時系列ギャップで最新年の場合、ボーナス
  if 次元 == "時系列ギャップ" AND year >= "2025":
    score = base_score + 2  // 7

  // 既に検索済みのギャップはスコアを 0 にする
  if ギャップ名 in searched_queries（類似度 > 0.7）:
    score = 0

  final_score = score
```

### 出力

スコア降順でソートされたギャップ候補リスト。上位 4 件を次の Phase 2 に渡す。

## フェーズ別ギャップ選択ルール

| フェーズ | 使用する次元 | 選択数 |
|---------|------------|--------|
| Broad Coverage (0-40%) | 次元 1, 2 を優先。次元 3, 4 も使用 | 上位 4 件 |
| Targeted Depth (40-75%) | 次元 3, 4 を優先。次元 2 の残りも使用 | 上位 4 件 |
| Long-Tail Discovery (75-100%) | 次元 5 を優先。次元 3, 4 の残りも使用 | 上位 2-3 件 |

## ギャップ枯渇時の対応

全次元でスコア > 0 のギャップが見つからない場合:

1. **searched_queries をリセット**して同じ Topic を異なるクエリ表現で再検索
2. **既存 Topic の粒度を細分化**: "Deep RL for Finance" → "Model-Based RL for Portfolio", "Offline RL for Trading" 等
3. **それでも見つからない場合**: 早期終了を判断し Final Report へ
