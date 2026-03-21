# KG品質チェック研究論文対応 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** kg-quality-check スキルに Research Paper Quality チェック（Phase 1.7）を追加し、スキーマYAMLを更新する

**Architecture:** 3ファイルの編集のみ。スキーマYAML に `abstract`/`venue` を追加 → SKILL.md に Phase 1.7（6チェック）と重み再配分を追記 → コマンド定義を更新。Pythonコードの変更なし。

**Tech Stack:** YAML, Markdown（SKILL.md / コマンド定義）

**Spec:** `docs/superpowers/specs/2026-03-21-kg-paper-quality-design.md`

---

### Task 1: スキーマYAML に `abstract` と `venue` を追加

**Files:**
- Modify: `data/config/knowledge-graph-schema.yaml:81-97` (Source properties セクション)

- [ ] **Step 1: `command_source` の後に `abstract` と `venue` を追加**

`data/config/knowledge-graph-schema.yaml` の Source ノード properties セクション末尾（`command_source` の後、`Entity:` の前）に以下を追加:

```yaml
      abstract:
        type: string
        description: "Paper/report abstract (paper/report source_type only)"
      venue:
        type: string
        indexed: true
        description: "Publication venue (e.g., NeurIPS, JSAI, ICML; paper/report source_type only)"
```

- [ ] **Step 2: YAML 構文を確認**

Run: `python -c "import yaml; yaml.safe_load(open('data/config/knowledge-graph-schema.yaml'))"`
Expected: エラーなし

- [ ] **Step 3: コミット**

```bash
git add data/config/knowledge-graph-schema.yaml
git commit -m "feat(kg): Source スキーマに abstract, venue プロパティを追加"
```

---

### Task 2: SKILL.md の冒頭 description と処理フローを更新

**Files:**
- Modify: `.claude/skills/kg-quality-check/SKILL.md:1-58`

- [ ] **Step 1: frontmatter の description を更新**

行 6 `6カテゴリの定量指標` → `7カテゴリの定量指標`

- [ ] **Step 2: 目的セクションを更新**

行 21 `**定量計測**: 6カテゴリの品質指標` → `**定量計測**: 7カテゴリの品質指標`

- [ ] **Step 3: 処理フローを更新**

行 48-56（コードフェンス内全体）の処理フロー図を以下に変更:

```
Phase 1: 定量計測（Cypher プローブ）
    |  mcp__neo4j-cypher__read_neo4j_cypher で7カテゴリの指標を計測
    |
Phase 1.7: Research Paper Quality（Cypher プローブ）
    |  論文系 Source の充填率・接続率・パイプライン品質を計測
    |
Phase 2: LLM-as-Judge
    |  Claim/Fact のサンプリング精度評価
    |  4構造プローブ → 仮説構築 → 自己評価
    |
Phase 3: レポート出力
    定量スコア + 問題一覧 + 改善提案をユーザーに提示
```

- [ ] **Step 4: Phase 1 ヘッダーを更新**

行 59 `## Phase 1: 定量計測（6カテゴリ）` → `## Phase 1: 定量計測（7カテゴリ）`

- [ ] **Step 5: コミット**

```bash
git add .claude/skills/kg-quality-check/SKILL.md
git commit -m "docs(kg): SKILL.md 冒頭を7カテゴリに更新"
```

---

### Task 3: SKILL.md の既存重みを更新

**Files:**
- Modify: `.claude/skills/kg-quality-check/SKILL.md:63,357,538,604,646,735,778,782,822`

- [ ] **Step 1: 6カテゴリの重みを変更**

以下の行の重み表記を変更:

| 行 | 変更前 | 変更後 |
|----|--------|--------|
| 63 | `Completeness（完全性）— 重み 25%` | `Completeness（完全性）— 重み 20%` |
| 357 | `Consistency（一貫性）— 重み 20%` | `Consistency（一貫性）— 重み 18%` |
| 538 | `Orphan 検出（孤立ノード）— 重み 15%` | `Orphan 検出（孤立ノード）— 重み 13%` |
| 604 | `Staleness（鮮度）— 重み 10%` | `Staleness（鮮度）— 重み 8%` |
| 646 | `Structural（構造）— 重み 10%` | `Structural（構造）— 重み 9%` |
| 735 | `Schema Compliance（スキーマ準拠）— 重み 5%` | 変更なし |
| 778 | `Phase 2: LLM-as-Judge（重み 15%）` | `Phase 2: LLM-as-Judge（重み 12%）` |
| 782 | `Claim/Fact 精度（8%）` | `Claim/Fact 精度（6.5%）` |
| 822 | `創発的発見ポテンシャル（7%）` | `創発的発見ポテンシャル（5.5%）` |

- [ ] **Step 2: 重み合計を検証**

変更後の重み合計が100%であることを確認: Completeness(20) + Consistency(18) + Orphan(13) + Staleness(8) + Structural(9) + Schema(5) + LLM(12) + ResearchPaper(15) = 100

- [ ] **Step 3: コミット**

```bash
git add .claude/skills/kg-quality-check/SKILL.md
git commit -m "docs(kg): 既存カテゴリの重みを再配分（Research Paper Quality 15%分の捻出）"
```

---

### Task 4: SKILL.md に Phase 1.7 セクションを追加

**Files:**
- Modify: `.claude/skills/kg-quality-check/SKILL.md` (行 735 の `### 1.6 Schema Compliance` セクションの後、`## Phase 2` の前に挿入)

- [ ] **Step 1: Phase 1.7 セクション全体を挿入**

`### 1.6 Schema Compliance` セクションの末尾（`## Phase 2: LLM-as-Judge` の直前）に以下を挿入:

```markdown
---

### 1.7 Research Paper Quality（研究論文品質）— 重み 15%

論文系 Source（`source_type` が `paper` または `report`）に特化した品質チェック。6つのサブチェックで構成される。

#### 内部重み

| チェック | 内部重み |
|---------|---------|
| A. source_type別ブレークダウン | 20% |
| B. スキーマドリフト検出 | 15% |
| C. Author整合性 | 20% |
| D. パイプライン別品質差分 | 20% |
| E. 重複Source検出 | 10% |
| F. 引用ネットワーク密度 | 15% |
| **合計** | **100%** |

#### スコア算出式

全チェックで統一式 `max(0, 1.0 - 問題件数 / 総対象件数)` を基本とする。

- **A**: `0.4 × プロパティ充填率 + 0.6 × 接続率`。充填率 = paper/report の `abstract`, `venue`, `published_at` の加重充填率（重み: 推奨=0.7）。接続率 = AUTHORED_BY/MAKES_CLAIM/USES_METHOD のいずれかを持つ割合。paper と report は件数比例で加重。
- **B**: `max(0, 1.0 - 未定義プロパティ種類数 / 全プロパティ種類数)`。1種類でも未定義があれば減点。
- **C**: `max(0, 1.0 - authors文字列のみの件数 / authors文字列を持つ総件数)`。
- **D**: `max(0, 1.0 - |connected接続率 - unconnected接続率|)`。接続率 = 3リレーション（AUTHORED_BY, MAKES_CLAIM, USES_METHOD）のいずれかを持つ割合。connected = `arxiv-*` + `jsai2026-*`/UUID、unconnected = `src-*`。**注**: このチェックはパイプライン間の**均一性**を計測する。絶対的な接続品質はチェック A がカバーするため、A と D は相補的に機能する。
- **E**: `max(0, 1.0 - 重複URLペア数 / 総Source件数)`。
- **F**: `min(1.0, CITES件数 / 論文件数)`。密度1.0以上は1.0にクランプ。

#### A. source_type別ブレークダウン

**充填率**:

```cypher
MATCH (s:Source)
WHERE s.source_type IN ['paper', 'report']
RETURN s.source_type AS type, count(s) AS total,
       count(s.abstract) AS has_abstract,
       count(s.venue) AS has_venue,
       count(s.published_at) AS has_published_at,
       count(s.fetched_at) AS has_fetched_at
```

**接続率**:

```cypher
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

#### B. スキーマドリフト検出

Source 上の全プロパティキーを収集し、スキーマ定義プロパティリストと比較する。

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

#### C. Author文字列↔リレーション整合性

`authors` 文字列プロパティを持つが AUTHORED_BY リレーションがない Source を検出する。

```cypher
MATCH (s:Source)
WHERE s.source_type IN ['paper', 'report']
AND s.authors IS NOT NULL
AND NOT (s)-[:AUTHORED_BY]->()
RETURN count(s) AS papers_with_string_only,
       collect(s.source_id)[..10] AS sample_ids
```

#### D. パイプライン別品質差分

`src-*` prefix（unconnected）とそれ以外（connected）の接続率を比較する。

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

#### E. 重複Source検出

同一URLで異なる source_id を持つノードを検出する。

```cypher
MATCH (s:Source)
WHERE s.url IS NOT NULL
WITH s.url AS url, collect(s.source_id) AS ids, count(s) AS cnt
WHERE cnt > 1
RETURN url, ids
```

#### F. 引用ネットワーク密度

論文間の CITES リレーションの密度を計測する。

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

**スコア算出**:
- 各サブチェックのスコアを算出し、内部重みで加重平均してカテゴリスコアとする
```

- [ ] **Step 2: 正しい位置に挿入されていることを確認**

`### 1.6 Schema Compliance` の後、`## Phase 2: LLM-as-Judge` の前にあること。

- [ ] **Step 3: コミット**

```bash
git add .claude/skills/kg-quality-check/SKILL.md
git commit -m "feat(kg): SKILL.md に Phase 1.7 Research Paper Quality を追加"
```

---

### Task 5: SKILL.md のレポートテンプレートと総合スコア表を更新

**Files:**
- Modify: `.claude/skills/kg-quality-check/SKILL.md` (Phase 3 レポート出力セクション)

- [ ] **Step 1: レポートテンプレートにセクション8を追加**

Phase 3 レポート出力テンプレート内、`### 7. LLM-as-Judge` セクションの後、`### 総合スコア` の前に以下を追加:

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
| connected | XX | XX% | XX% | XX% |
| unconnected | XX | XX% | XX% | XX% |

#### スキーマドリフト
| プロパティ | 件数 | 対応 |
|-----------|------|------|
| ... | XX | ... |

#### Author整合性
- authors文字列のみ（リレーションなし）: N件

#### 重複Source
- 重複URL: N件

#### 引用ネットワーク密度
- CITES: N件 / 論文 N件 = X.X%
```

- [ ] **Step 2: 総合スコア表に Research Paper Quality 行を追加**

既存の総合スコア表（`### 総合スコア: XX/100` 内）に行を追加:

変更前:
```markdown
| Schema Compliance | XX% | 5% | XX |
| LLM-as-Judge | XX% | 15% | XX |
```

変更後:
```markdown
| Schema Compliance | XX% | 5% | XX |
| LLM-as-Judge | XX% | 12% | XX |
| Research Paper Quality | XX% | 15% | XX |
```

**注**: パイプライン別接続率テーブルのラベルは `connected`/`unconnected`（Cypherクエリの出力に一致）。スペックでは `arxiv`/`src` と記載されているが、クエリ出力との整合性を優先して変更した。

他の行の重みも更新:
- Completeness: 25% → 20%
- Consistency: 20% → 18%
- Orphan: 15% → 13%
- Staleness: 10% → 8%
- Structural: 10% → 9%

- [ ] **Step 3: コミット**

```bash
git add .claude/skills/kg-quality-check/SKILL.md
git commit -m "docs(kg): レポートテンプレートに Research Paper Quality セクションを追加"
```

---

### Task 6: SKILL.md の MUST/SHOULD/NEVER と完了条件を更新

**Files:**
- Modify: `.claude/skills/kg-quality-check/SKILL.md` (MUST/完了条件セクション)

- [ ] **Step 1: MUST セクションを更新**

行 1020 `Phase 1 の6カテゴリ全ての Cypher プローブを実行すること` → `Phase 1 の7カテゴリ全ての Cypher プローブを実行すること（Phase 1.7 Research Paper Quality を含む）`

- [ ] **Step 2: 完了条件を更新**

行 1041 `6カテゴリの Cypher プローブが全て実行されている` → `7カテゴリの Cypher プローブが全て実行されている（Phase 1.7 Research Paper Quality を含む）`

以下を完了条件に追加:
```markdown
- [ ] Research Paper Quality の6サブチェック（A-F）が全て実行されている
```

- [ ] **Step 3: コミット**

```bash
git add .claude/skills/kg-quality-check/SKILL.md
git commit -m "docs(kg): MUST/完了条件を7カテゴリに更新"
```

---

### Task 7: コマンド定義を更新

**Files:**
- Modify: `.claude/commands/kg-quality-check.md`

- [ ] **Step 1: Phase 1 箇条書きに Research Paper Quality を追加**

行 15 `1. **Phase 1**: 6カテゴリの Cypher プローブ` → `1. **Phase 1**: 7カテゴリの Cypher プローブ`

**注**: 行 7 は既に `7カテゴリで計測・評価します` と記載されているため変更不要。

箇条書き（行 16-21）の最後に以下を追加:
```markdown
   - Research Paper Quality（研究論文品質）— 充填率・接続率・パイプライン差分・重複・引用密度
```

- [ ] **Step 2: コミット**

```bash
git add .claude/commands/kg-quality-check.md
git commit -m "docs(kg): コマンド定義に Research Paper Quality を追加"
```

---

### Task 8: 動作確認 — `/kg-quality-check` を実行して Phase 1.7 が計測されることを確認

**Files:**
- なし（実行確認のみ）

- [ ] **Step 1: `/kg-quality-check` を実行**

スキルを実行し、レポートに「8. Research Paper Quality」セクションが出力されることを確認。

- [ ] **Step 2: 確認項目**

以下を確認:
- [ ] 6サブチェック（A-F）の全てが実行されている
- [ ] Research Paper Quality のスコアが算出されている
- [ ] 総合スコア表に Research Paper Quality 行が含まれている
- [ ] 重みの合計が100%になっている
- [ ] Rating が正しく算出されている
