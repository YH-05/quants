# 議論メモ: arXiv論文 著者・引用 自動取得パイプライン

**日付**: 2026-03-19
**議論ID**: disc-2026-03-19-arxiv-pipeline
**参加**: ユーザー + AI

## 背景・コンテキスト

Neo4j KG v2.1 は Author, AUTHORED_BY, CITES, COAUTHORED_WITH を定義済みだが、論文メタデータの自動取得パイプラインが存在しない。手動補完した 236 Author ノード（`auth-*` 形式ID）は再利用不可。

## 議論のサマリー

1. 既存コードベースの詳細調査（emit_graph_queue.py, id_generator.py, rate_limiter.py, retry.py, SQLiteCache, error hierarchy）
2. 実装計画の策定（`docs/plan/misty-dazzling-hopper.md`）
3. GitHub Project #92 作成 + 7 Issue 登録
4. Worktree feature/prj92 作成

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-19-010 | S2 API を主、arXiv をフォールバック | S2は引用情報を提供、arXivは提供しない |
| dec-2026-03-19-011 | edgar.RateLimiter 直接import、market.SQLiteCache 再利用、academic 固有エラー階層新規作成 | 汎用コード再利用 + tenacity 型制約 |
| dec-2026-03-19-012 | SCHEMA_VERSION 1.1→2.1、cites/coauthored_with 追加、auth-* Author 移行 | graph-queue パイプラインの KG v2.1 対応 |
| dec-2026-03-19-013 | 5 Wave / 7 Issue 構成（Project #92） | Wave 2A/2B 並列開発で効率化 |

## アクションアイテム

| ID | 内容 | 優先度 | Issue |
|----|------|--------|-------|
| act-2026-03-19-001 | Wave 0: emit_graph_queue 更新 + Author移行 | 高 | #3802 |
| act-2026-03-19-002 | Wave 1: パッケージ基盤（types, errors, retry） | 高 | #3803 |
| act-2026-03-19-003 | Wave 2A/2B: S2 Client + arXiv Client + Cache | 中 | #3804, #3805 |
| act-2026-03-19-004 | Wave 3A/3B: PaperFetcher + Mapper + CLI | 中 | #3806, #3807 |
| act-2026-03-19-005 | Wave 4: バックフィル + ドキュメント | 低 | #3808 |

## 成果物

| 成果物 | パス / URL |
|--------|-----------|
| 実装計画 | `docs/plan/misty-dazzling-hopper.md` |
| 元プランファイル | `docs/plan/2026-03-19_arxiv-author-citation-pipeline.md` |
| GitHub Project | https://github.com/users/YH-05/projects/92 |
| Worktree | `/Users/yukihata/Desktop/.worktrees/quants/feature-prj92` |

## 次回の議論トピック

- Wave 0 実装後の Author ノード移行結果確認
- S2 API の実際のレスポンス確認（フィールド名、ネスト構造）
- feedparser の arXiv namespace 対応の検証結果
