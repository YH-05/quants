# 議論メモ: クオンツ知識のNeo4j保存における障壁分析

**日付**: 2026-03-19
**議論ID**: disc-2026-03-19-quant-kg-barriers
**参加**: ユーザー + AI

## 背景・コンテキスト

ユーザーは「Web検索や論文検索で収集したクオンツ分析・コード構築情報をNeo4jに保存したい」という要望を持っている。現在のNeo4jには project-discuss が作成する Discussion/Decision/ActionItem のみが保存されており、KG v1 ノード（Source/Entity/Claim等）は0件。

## 議論のサマリー

### 論点1: 現行スキーマのクオンツ知識対応状況

KG v1 スキーマ（9ノード）は金融市場情報に特化。以下が保存できない:

| 保存したい情報 | 問題 |
|---|---|
| ファクター定義（モメンタム、バリュー等） | Claimに無理矢理入れると型が混在 |
| バックテスト結果・戦略パフォーマンス | FinancialDataPointは企業財務用 |
| コードスニペット・アルゴリズム | コード保存用ノード型が未定義 |
| 論文の手法・数式 | Factは過去事実用で手法記述に不適 |
| ライブラリ・ツール情報 | Entity.entity_typeにlibrary/toolがない |

**結論**: スキーマ拡張が必要（Method/Algorithm/Library等のノード型追加）

### 論点2: KG v1 パイプラインの稼働状況

- KG v1 ノード: 0件（Source, Entity, Claim, Fact, Insight等すべて空）
- .tmp/graph-queue/ に未処理JSON 2件が残存（dr-stock, ca-eval）
- emit-graph-queue → save-to-graph パイプラインが一度も実行されていない

**結論**: スキーマ拡張前にまず既存パイプラインの動作確認が先決

### 論点3: 収集→構造化パイプラインの欠如

```
Web検索/論文検索
    ↓ ???（構造化エージェントがない）
graph-queue JSON
    ↓ /emit-graph-queue
.tmp/graph-queue/*.json
    ↓ /save-to-graph
Neo4j
```

既存の emit-graph-queue は金融ワークフロー出力をJSON変換する設計。「Web検索結果やPDF論文をクオンツ知識として構造化する」用途には未対応。

**結論**: クオンツ知識収集→構造化エージェントの新規設計が必要

### 論点4: enum値の不足

- Topic.category: `quant_method`, `backtest`, `algorithm`, `risk_model` がない
- Source.source_type: `paper`/`academic`, `code`, `documentation` がない

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-19-001 | KG v1スキーマにクオンツ知識用ノード型（Method/Algorithm/Library）の追加が必要 | 現行9ノードは金融市場情報に特化 |
| dec-2026-03-19-002 | KG v1パイプライン動作確認を先に実施（未処理JSON 2件） | KG v1ノード0件、パイプライン未実行 |
| dec-2026-03-19-003 | クオンツ知識収集エージェントの新規構築が必要 | 既存パイプラインは金融ワークフロー出力用 |

## アクションアイテム

| ID | 内容 | 優先度 | 依存 |
|----|------|--------|------|
| act-2026-03-19-001 | 既存graph-queue 2件を /save-to-graph で投入しパイプライン動作確認 | 高 | - |
| act-2026-03-19-002 | KG v1スキーマ拡張設計（ノード型・enum追加） | 高 | act-001完了後 |
| act-2026-03-19-003 | クオンツ知識収集→構造化エージェント設計 | 中 | act-002完了後 |
| act-2026-03-19-004 | note-financeプロジェクトのKG構築手法を調査 | 高 | - |

## 次回の議論トピック

- note-finance調査結果を踏まえたスキーマ拡張の具体設計
- クオンツ知識収集エージェントのワークフロー設計
- KG v1パイプライン動作確認結果のレビュー
