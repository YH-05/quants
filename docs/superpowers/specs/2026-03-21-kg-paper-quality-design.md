# KG品質チェック研究論文対応 + スキーマ更新 設計書

**作成日**: 2026-03-21
**ステータス**: 承認済み
**スコープ**: A（スキル改善）→ B（データバックフィル）

## 背景

`/kg-quality-check` スキルは KG v2.2 の全体構造品質を網羅的にチェックするが、研究論文データ固有の品質問題に対して6つの盲点がある。KG全ノードの93%が論文系Sourceであり、この領域の品質チェック強化は優先度が高い。

### 特定された盲点

1. `source_type` 別のブレークダウンがない
2. スキーマドリフト（データにあるがYAML未定義のプロパティ）を検出していない
3. Author文字列プロパティと AUTHORED_BY リレーションの不整合を検出していない
4. パイプライン別（`arxiv-*` vs `src-*`）の品質格差を検出していない
5. 重複Sourceを検出していない
6. 引用ネットワーク密度を計測していない

### 現状のデータ

- 論文系Source: 221件（paper 158 + report 63）
- `arxiv-*`: 98件（AUTHORED_BY, MAKES_CLAIM, USES_METHOD あり）
- `src-*`: 89件（Topic 以外の接続なし — Claims, Methods, Authors 全て欠落）
- `jsai2026-*` / UUID: 34件（JSAI 2026 カンファレンス論文。Claim/Method接続あり、arxiv-*と同等品質）
- CITES リレーション: 4件のみ（密度1.8%）

**パイプライン分類**: チェック D では `arxiv-*` と `jsai2026-*`/UUID を合算して「connected」パイプライン、`src-*` を「unconnected」パイプラインとして比較する。

## フェーズA: スキル改善

### A1. スキーマYAML更新

**ファイル**: `data/config/knowledge-graph-schema.yaml`

#### Source ノードへのプロパティ追加

| プロパティ | 型 | 重要度 | indexed | 説明 |
|-----------|-----|--------|---------|------|
| `abstract` | string | 推奨 | false | 論文要旨（paper/report専用） |
| `venue` | string | 推奨 | true | 発表会場（paper/report専用） |

#### 命名統一

- `published_date`（69件存在、スキーマ未定義）→ `published_at`（既存定義）に統一
- スキーマ側の変更は不要（`published_at` は既に定義済み）
- データマイグレーションはBフェーズで実施

#### 追加しないプロパティ

- `authors`（文字列）— AUTHORED_BY リレーションに展開すべきレガシーデータ
- `arxiv_id`, `doi`, `s2_paper_id` — Source.url / Source.source_id から導出可能

### A2. SKILL.md への Phase 1.7 追加

**ファイル**: `.claude/skills/kg-quality-check/SKILL.md`

#### 重み再配分

| カテゴリ | 現行 | 変更後 |
|---------|------|--------|
| Completeness | 25% | 20% |
| Consistency | 20% | 18% |
| Orphan | 15% | 13% |
| Staleness | 10% | 8% |
| Structural | 10% | 9% |
| Schema Compliance | 5% | 5% |
| LLM-as-Judge | 15% | 12% |
| **Research Paper Quality** | — | **15%** |
| **合計** | **100%** | **100%** |

**LLM-as-Judge 内部重み変更**: 15% → 12% に伴い、Claim/Fact精度 8% → 6.5%、創発的発見 7% → 5.5% に調整。

#### Phase 1.7 の6チェックと内部重み

| チェック | 内部重み | スコア算出 |
|---------|---------|----------|
| A. source_type別ブレークダウン | 20% | 下記算出式参照 |
| B. スキーマドリフト検出 | 15% | 下記算出式参照 |
| C. Author整合性 | 20% | 下記算出式参照 |
| D. パイプライン別品質差分 | 20% | 下記算出式参照 |
| E. 重複Source検出 | 10% | 下記算出式参照 |
| F. 引用ネットワーク密度 | 15% | 下記算出式参照 |
| **合計** | **100%** | |

#### スコア算出式

全チェックで統一式 `max(0, 1.0 - 問題件数 / 総対象件数)` を基本とする。

- **A**: `0.4 × プロパティ充填率 + 0.6 × 接続率`。充填率 = paper/report の `abstract`, `venue`, `published_at` の加重充填率（重み: 推奨=0.7）。接続率 = AUTHORED_BY/MAKES_CLAIM/USES_METHOD のいずれかを持つ割合。paper と report は件数比例で加重。
- **B**: `max(0, 1.0 - 未定義プロパティ種類数 / 全プロパティ種類数)`。1種類でも未定義があれば減点。
- **C**: `max(0, 1.0 - authors文字列のみの件数 / authors文字列を持つ総件数)`。
- **D**: `max(0, 1.0 - |connected接続率 - unconnected接続率|)`。接続率 = 3リレーション（AUTHORED_BY, MAKES_CLAIM, USES_METHOD）のいずれかを持つ割合。connected = `arxiv-*` + `jsai2026-*`/UUID、unconnected = `src-*`。**注**: このチェックはパイプライン間の**均一性**を計測する。絶対的な接続品質はチェック A がカバーするため、A と D は相補的に機能する。
- **E**: `max(0, 1.0 - 重複URLペア数 / 総Source件数)`。
- **F**: `min(1.0, CITES件数 / 論文件数)`。密度1.0以上は1.0にクランプ。

#### Cypherクエリ

**A. source_type別ブレークダウン:**

```cypher
// 充填率
MATCH (s:Source)
WHERE s.source_type IN ['paper', 'report']
RETURN s.source_type AS type, count(s) AS total,
       count(s.abstract) AS has_abstract,
       count(s.venue) AS has_venue,
       count(s.published_at) AS has_published_at,
       count(s.fetched_at) AS has_fetched_at

// 接続率
MATCH (s:Source)
WHERE s.source_type IN ['paper', 'report']
OPTIONAL MATCH (s)-[:AUTHORED_BY]->(a:Author)
OPTIONAL MATCH (s)-[:MAKES_CLAIM]->(c:Claim)
OPTIONAL MATCH (s)-[:USES_METHOD]->(m:Method)
WITH s, count(DISTINCT a) AS authors, count(DISTINCT c) AS claims, count(DISTINCT m) AS methods
RETURN s.source_type AS type,
       count(s) AS total,
       sum(CASE WHEN authors > 0 THEN 1 ELSE 0 END) AS with_authors,
       sum(CASE WHEN claims > 0 THEN 1 ELSE 0 END) AS with_claims,
       sum(CASE WHEN methods > 0 THEN 1 ELSE 0 END) AS with_methods
```

**B. スキーマドリフト検出:**

```cypher
MATCH (s:Source)
WITH s, keys(s) AS props
UNWIND props AS prop
WHERE NOT prop IN [
    'source_id','title','url','source_type','publisher',
    'published_at','fetched_at','language','category',
    'command_source','abstract','venue'
]
RETURN prop AS undeclared_property, count(*) AS cnt
ORDER BY cnt DESC
```

**C. Author文字列↔リレーション整合性:**

```cypher
MATCH (s:Source)
WHERE s.source_type IN ['paper', 'report']
AND s.authors IS NOT NULL
AND NOT (s)-[:AUTHORED_BY]->()
RETURN count(s) AS papers_with_string_only,
       collect(s.source_id)[..10] AS sample_ids
```

**D. パイプライン別品質差分:**

```cypher
MATCH (s:Source)
WHERE s.source_type IN ['paper', 'report']
WITH s,
     CASE WHEN s.source_id STARTS WITH 'src-' THEN 'unconnected'
          ELSE 'connected' END AS pipeline
OPTIONAL MATCH (s)-[:AUTHORED_BY]->(a:Author)
OPTIONAL MATCH (s)-[:MAKES_CLAIM]->(c:Claim)
OPTIONAL MATCH (s)-[:USES_METHOD]->(m:Method)
WITH pipeline, s,
     count(DISTINCT a) AS authors,
     count(DISTINCT c) AS claims,
     count(DISTINCT m) AS methods
RETURN pipeline, count(s) AS total,
       sum(CASE WHEN authors > 0 THEN 1 ELSE 0 END) AS with_authors,
       sum(CASE WHEN claims > 0 THEN 1 ELSE 0 END) AS with_claims,
       sum(CASE WHEN methods > 0 THEN 1 ELSE 0 END) AS with_methods
```

**E. 重複Source検出:**

```cypher
MATCH (s:Source)
WHERE s.url IS NOT NULL
WITH s.url AS url, collect(s.source_id) AS ids, count(s) AS cnt
WHERE cnt > 1
RETURN url, ids
```

**F. 引用ネットワーク密度:**

```cypher
MATCH (s:Source)
WHERE s.source_type IN ['paper', 'report']
WITH count(s) AS paper_count
CALL {
    MATCH ()-[r:CITES]->()
    RETURN count(r) AS cites_count
}
RETURN paper_count, cites_count,
       toFloat(cites_count) / paper_count AS density
```

#### レポート出力

既存Markdownフォーマットに「8. Research Paper Quality」セクションとして追加:

```markdown
### 8. Research Paper Quality スコア: XX%

#### source_type別充填率
| type | total | abstract | venue | published_at |
|------|-------|----------|-------|-------------|
| paper | XX | XX% | XX% | XX% |
| report | XX | XX% | XX% | XX% |

#### パイプライン別接続率
| pipeline | total | AUTHORED_BY | MAKES_CLAIM | USES_METHOD |
|----------|-------|-------------|-------------|-------------|
| arxiv | XX | XX% | XX% | XX% |
| src | XX | XX% | XX% | XX% |

#### スキーマドリフト
| プロパティ | 件数 | 対応 |
|-----------|------|------|
| published_date | XX | → published_at に統一 |
| authors | XX | → AUTHORED_BY に展開 |
...

#### Author整合性
- authors文字列のみ（リレーションなし）: N件

#### 重複Source
- 重複URL: N件

#### 引用ネットワーク密度
- CITES: N件 / 論文 N件 = X.X%
```

#### 総合スコア表の更新

```markdown
| カテゴリ | スコア | 重み | 加重スコア |
|---------|--------|------|-----------|
| ... | | | |
| Research Paper Quality | XX% | 15% | XX |
| **合計** | | **100%** | **XX** |
```

## フェーズB: データバックフィル

スキル改善後に実行するデータ修正。

| # | 作業 | 対象 | 方法 | 工数 |
|---|------|------|------|------|
| B1 | `published_date` → `published_at` マイグレーション | 69件 Source | Cypher SET + REMOVE | 小 |
| B2 | Claim.sentiment enum正規化 | 93件 | `positive`→`bullish`, `negative`→`bearish` | 小 |
| B3 | Claim.claim_type enum正規化 | 56件 | マッピングルール策定 → Cypher UPDATE | 中 |
| B4 | `src-*` 論文の Claim/Method 抽出 | 89件 | alphaxiv-search → emit-graph-queue → save-to-graph | 大 |
| B5 | `src-*` 論文の Author リレーション展開 | 89件 | `authors`文字列 → AUTHORED_BY リレーション生成 | 中 |
| B6 | PerformanceEvidence ID正規化 | 47件 | 8桁hex suffix追加 | 小 |
| B7 | CITES リレーション再構築 | 221件 | academic パッケージで既存論文間の引用を再スキャン | 中 |

### B3 マッピングルール案

| 現在の値 | マッピング先 | 根拠 |
|---------|-------------|------|
| `empirical_result` | `analysis` | 実験結果の解釈 |
| `finding` | `analysis` | 発見の分析 |
| `result` | `analysis` | 結果の報告 |
| `methodology` | `analysis` | 手法の適用・分析（実データで content を確認し、`recommendation` が適切な場合は個別判断） |
| `hypothesis` | `prediction` | 仮説の提示 |
| `benchmark_result` | `analysis` | ベンチマーク結果 |
| `novelty` | `analysis` | 新規性の主張 |

### B4 実行方針

89件の `src-*` 論文は `abstract` を持つため、LLMによる Claim/Method 抽出が可能。ただし工数が大きいため、以下の段階的アプローチを取る:

1. 高関連度の論文から優先的に抽出（Topic count >= 3 または is_meta Topic に接続しているもの）
2. バッチサイズ10件ずつ、品質確認しながら段階実行
3. 抽出後に `/kg-quality-check` を再実行し、スコア改善を確認

## 成功基準

- Phase 1.7 の全6チェックが `/kg-quality-check` 実行時に計測される
- `knowledge-graph-schema.yaml` に `abstract`, `venue` が正式定義される
- Bフェーズ完了後、Research Paper Quality スコアが70%以上に改善
- 総合スコアが現行78点から85点以上に改善

## 影響範囲

| ファイル | 変更内容 |
|---------|---------|
| `data/config/knowledge-graph-schema.yaml` | Source に `abstract`, `venue` 追加 |
| `.claude/skills/kg-quality-check/SKILL.md` | Phase 1.7 追加、重み再配分、レポートフォーマット更新、冒頭 description を「7カテゴリ」に更新、LLM-as-Judge 内部重み更新 |
| `.claude/commands/kg-quality-check.md` | Phase 1 箇条書きに Research Paper Quality を追加 |
