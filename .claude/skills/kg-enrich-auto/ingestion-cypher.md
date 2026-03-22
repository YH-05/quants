# Neo4j 投入 Cypher パターン集

alphaxiv 検索結果を Neo4j に MERGE ベースで冪等投入するための Cypher テンプレート。

## ID 生成

全 ID は `src/database/id_generator.py` を Bash 経由で呼び出して生成する。
**LLM が ID を推測・生成してはならない。** 必ず以下のコマンドで取得すること。

### バッチ ID 生成スクリプト

1 論文ずつ Bash を呼ぶのは非効率なため、複数論文の ID をまとめて生成する。

```bash
# 複数 Source ID を一括生成（改行区切りの arXiv ID リストを渡す）
uv run python -c "
from database.id_generator import generate_source_id
import sys
for arxiv_id in sys.stdin.read().strip().split('\n'):
    url = f'https://arxiv.org/abs/{arxiv_id}'
    print(f'{arxiv_id}\t{generate_source_id(url)}')
" <<'IDS'
2303.09406
2401.01234
2405.56789
IDS
```

### 個別 ID 生成

```bash
# Source ID（arXiv URL → UUID5）
uv run python -c "from database.id_generator import generate_source_id; print(generate_source_id('https://arxiv.org/abs/2303.09406'))"

# Topic ID（name + category → UUID5）
uv run python -c "from database.id_generator import generate_topic_id; print(generate_topic_id('Transformer for Finance', 'quant_method'))"

# Author ID（name + type → UUID5）
uv run python -c "from database.id_generator import generate_author_id; print(generate_author_id('John Smith', 'academic'))"

# Claim ID（content → SHA-256[:32]）
uv run python -c "from database.id_generator import generate_claim_id; print(generate_claim_id('Transformers outperform LSTMs for stock prediction'))"
```

## Node MERGE パターン

### Source（論文）

```cypher
MERGE (s:Source {source_id: $source_id})
SET s.title = $title,
    s.url = $url,
    s.source_type = 'paper',
    s.publisher = 'arXiv',
    s.published_at = $published_at,
    s.abstract = $abstract,
    s.command_source = 'kg-enrich-auto',
    s.fetched_at = datetime()
```

パラメータ:
- `$source_id`: `generate_source_id(f"https://arxiv.org/abs/{arxiv_id}")` の出力
- `$url`: `https://arxiv.org/abs/{arxiv_id}`
- `$title`: 論文タイトル
- `$published_at`: 公開日（ISO 8601 文字列、例: `"2023-10-01"`）
- `$abstract`: Abstract テキスト（alphaxiv 結果から取得）

### Author（著者）

```cypher
MERGE (a:Author {author_id: $author_id})
SET a.name = $name,
    a.author_type = 'academic'
```

パラメータ:
- `$author_id`: `generate_author_id(name, "academic")` の出力
- `$name`: 著者名

### Topic（トピック）

```cypher
MERGE (t:Topic {topic_id: $topic_id})
SET t.name = $name,
    t.category = $category
```

パラメータ:
- `$topic_id`: `generate_topic_id(name, category)` の出力
- `$name`: トピック名（PascalCase 不要、自然言語でよい）
- `$category`: `quant_method` | `ai` | `market_anomaly` | `macro` | `stock` | `sector` 等

### Claim（主張・知見）

```cypher
MERGE (c:Claim {claim_id: $claim_id})
SET c.content = $content,
    c.claim_type = 'research_finding',
    c.confidence = 'medium',
    c.created_at = datetime()
```

パラメータ:
- `$claim_id`: `generate_claim_id(content)` の出力
- `$content`: 主張テキスト（Abstract から抽出した 1-2 文の知見）

### Method（手法）

```cypher
MERGE (m:Method {method_id: $method_id})
SET m.name = $name,
    m.method_type = $method_type
```

パラメータ:
- `$method_id`: `method-{slug}` 形式（例: `method-transformer`, `method-deep-rl`）。slug は小文字ハイフン区切り。
- `$name`: 手法名（例: "Transformer", "Deep Reinforcement Learning"）
- `$method_type`: 手法分類（例: "deep_learning", "reinforcement_learning", "statistical", "optimization"）

## Relationship MERGE パターン

### AUTHORED_BY（Source → Author）

```cypher
MATCH (s:Source {source_id: $source_id})
MATCH (a:Author {author_id: $author_id})
MERGE (s)-[:AUTHORED_BY]->(a)
```

### TAGGED（Source → Topic）

```cypher
MATCH (s:Source {source_id: $source_id})
MATCH (t:Topic {topic_id: $topic_id})
MERGE (s)-[:TAGGED]->(t)
```

### MAKES_CLAIM（Source → Claim）

```cypher
MATCH (s:Source {source_id: $source_id})
MATCH (c:Claim {claim_id: $claim_id})
MERGE (s)-[:MAKES_CLAIM]->(c)
```

### USES_METHOD（Source → Method）

```cypher
MATCH (s:Source {source_id: $source_id})
MATCH (m:Method {method_id: $method_id})
MERGE (s)-[:USES_METHOD]->(m)
```

## バッチ投入パターン

複数論文を効率的に投入するため、UNWIND を使用する。

### Source バッチ MERGE

```cypher
UNWIND $papers AS p
MERGE (s:Source {source_id: p.source_id})
SET s.title = p.title,
    s.url = p.url,
    s.source_type = 'paper',
    s.publisher = 'arXiv',
    s.published_at = p.published_at,
    s.abstract = p.abstract,
    s.command_source = 'kg-enrich-auto',
    s.fetched_at = datetime()
```

### TAGGED バッチ MERGE

```cypher
UNWIND $links AS l
MATCH (s:Source {source_id: l.source_id})
MATCH (t:Topic {topic_id: l.topic_id})
MERGE (s)-[:TAGGED]->(t)
```

## 既存 Topic への自動接続（クロスコネクション）

新しく投入した Source を、既存 Topic にキーワードマッチで接続する。

```cypher
// 既存 Topic 一覧を取得（接続候補）
MATCH (t:Topic)
RETURN t.topic_id, t.name, t.category
ORDER BY t.name
```

マッチングロジック（LLM が実行）:
1. 新 Source の Abstract と既存 Topic 名を比較
2. 関連性が高い場合、TAGGED リレーションを MERGE
3. **1 Source あたり最大 3 Topic** に制限（過剰接続防止）

## 重複チェック

投入前に既存 Source の arXiv ID を確認する:

```cypher
// arXiv ID で既存チェック（部分一致）
MATCH (s:Source)
WHERE s.url CONTAINS $arxiv_id
RETURN s.source_id, s.title, s.url
```

```cypher
// 全既存論文の arXiv ID リストを取得
MATCH (s:Source {source_type: 'paper'})
RETURN s.url
ORDER BY s.url
```

## 注意事項

1. **全書き込みは MERGE**: CREATE は使用禁止。冪等性を保証する。
2. **ID は必ず id_generator.py で生成**: LLM による推測 ID は禁止。
3. **Abstract から Claim 抽出は 1-2 件に制限**: 過剰抽出はノイズになる。
4. **Method ID の slug は既存との一貫性を維持**: 新 Method 作成前に既存 Method を確認すること。
