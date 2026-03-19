# 議論メモ: Neo4j KG品質改善 + パイプライン整合性修正

**日付**: 2026-03-19
**議論ID**: disc-2026-03-19-kg-quality-improvement
**参加**: ユーザー + AI

## 背景・コンテキスト

Neo4j KGの品質レポートを作成し、Project #92（arXivパイプライン）に依存しない改善可能箇所を特定・実施した。さらにユーザーの指摘により、改善内容とデータ投入パイプライン（emit_graph_queue.py, save-to-graph skill, schema.yaml）の整合性を確保するコード修正も実施。

## 議論のサマリー

### 1. KG品質レポート（改善前）

| カテゴリ | スコア | 主要問題 |
|---------|--------|---------|
| スキーマ設計 | A | 18ノード型、14 UNIQUE制約 |
| データ充実度 | C | published 0%, confidence 0%, CITES 4件 |
| 接続密度 | B- | AUTHORED_BY 42%欠損、CITES ほぼ空 |
| 分析可能性 | C+ | Topic横断は有用だが時系列・定量データ空 |
| **総合** | **C+** | |

### 2. 改善8項目の実施

| # | 内容 | Before | After |
|---|------|--------|-------|
| A1 | 孤立ノード接続 | 4件 | 0件 |
| A2 | report/web published = fetched_at | 0% | 53% |
| A3 | Topic統合（1件接続を親に吸収） | 48 | 21 |
| B1 | Claim.confidence付与 | 0% | 100% |
| B2 | CONTRADICTS拡充 | 5 | 10 |
| B3 | paper URL補完 | 77% | 100% |
| C1 | Entity自動生成（Author.org→Entity） | 20 | 69 |
| C2 | Topic階層化（7メタTopic + SUBTOPIC_OF） | 0 | 21 |

**改善後**: 1,069ノード / 2,840リレーション / 孤立0 / **スコア B**

### 3. パイプライン整合性修正（ユーザー指摘）

ユーザーから「データ投入パイプラインに影響しないか」との指摘。調査の結果5箇所の不整合を発見し修正。

| ファイル | 変更内容 |
|---------|---------|
| `data/config/knowledge-graph-schema.yaml` | v2.1→v2.2: Claim.confidence, Topic.is_meta, SUBTOPIC_OF, AFFILIATED_WITH追加 |
| `scripts/emit_graph_queue.py` | SCHEMA_VERSION 1.1→2.2, relations に4種追加 |
| `.claude/skills/save-to-graph/SKILL.md` | Source MERGE に published_at COALESCE, Claim に confidence, Phase 3aに4リレーション追加 |
| `.claude/skills/save-to-graph/guide.md` | schema_version更新、relations追加 |

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-19-020 | EDINET Proプラン検討アクションアイテムを削除 | Freeプランで十分進捗 |
| dec-2026-03-19-021 | NAS Tailscale自動起動はcron @reboot方式で確定 | reboot後60秒以内に復帰確認済み |
| dec-2026-03-19-022 | UGOS FW更新対策は/volume1バックアップ+restore.sh方式 | overlay FS構成、/volume1は永続 |
| dec-2026-03-19-023 | KGスキーマをv2.2に拡張 | パイプライン整合性確保 |
| dec-2026-03-19-024 | Topic統合方針: source_count=1は親Topicにマージ | 48→21に圧縮、接続密度向上 |

## アクションアイテム更新

| ID | 内容 | 優先度 | ステータス |
|----|------|--------|-----------|
| act-2026-03-18-001 | EDINET Proプラン検討 | - | **削除** |
| act-2026-03-18-002 | EDINET --resume 継続実行 | 高 | in_progress（106/3838社、翌日以降継続） |
| act-2026-03-19-002 | NAS再起動後Tailscale自動起動確認 | 中 | **completed** |
| act-2026-03-19-003 | UGOS FW更新後Tailscale永続化確認 | 中 | **completed** |

## 変更したファイル

| ファイル | 変更内容 |
|---------|---------|
| `data/config/knowledge-graph-schema.yaml` | v2.2: +Claim.confidence, +Topic.is_meta, +SUBTOPIC_OF, +AFFILIATED_WITH |
| `scripts/emit_graph_queue.py` | SCHEMA_VERSION 2.2, +4 relation types |
| `.claude/skills/save-to-graph/SKILL.md` | v2.2対応、COALESCE フォールバック追加 |
| `.claude/skills/save-to-graph/guide.md` | schema_version、relations更新 |
| `.claude/skills/project-discuss/SKILL.md` | neo4j-memory依存削除（前セッション）|
| `.claude/skills/project-discuss/guide.md` | 同上 |
| `docs/plan/2026-03-19_discussion-progress-snapshot.md` | Tailscale完了、Proプラン削除 |
| `docs/plan/2026-03-18_nas-tailscale-setup.md` | 検証結果追記 |

## 次回の議論トピック

- EDINET --resume の日次継続（API上限到達まで自動化検討）
- Project #92（arXivパイプライン）Wave 0着手判断
- Neo4j KG: paper の published（S2/arXiv API依存）とCITESネットワーク構築
- 創発的戦略提案クエリの実行（MAS×KG, GNN×MASギャップから新戦略生成）
