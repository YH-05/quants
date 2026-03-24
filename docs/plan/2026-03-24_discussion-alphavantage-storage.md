# 議論メモ: Alpha Vantage Storage Layer 設計

**日付**: 2026-03-24
**議論ID**: disc-2026-03-24-alphavantage-storage
**参加**: ユーザー + AI

## 背景・コンテキスト

Alpha Vantage APIクライアント（`src/market/alphavantage/`）は PR #3840 でマージ済み。
API取得→パース→TTLキャッシュまで実装済みだが、長期的なデータ蓄積のための永続化層（Storage + Collector）が未実装。

## 議論のサマリー

1. **DB バックエンド選択**: DuckDB vs SQLite vs ハイブリッドの3案を提示
   - ユーザーが SQLite を選択（外付けSSD/NAS上での保存・操作要件）
2. **財務諸表テーブル設計**: 統合 vs 分離
   - ユーザーが分離を選択（IS/BS/CF の3テーブル）
3. **設計書作成・レビュー**: rev.1 作成 → doc-reviewer サブエージェントで9件の指摘 → rev.2 で全件対応
4. **実装計画策定**: 5 Wave 構成、~2825行の計画を作成

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-24-001 | SQLiteを採用（DuckDBではなく） | 外付けSSD・NAS対応要件 |
| dec-2026-03-24-002 | 財務諸表は IS/BS/CF 3テーブル分離 | カラム明確化、テーブル設計シンプル化 |
| dec-2026-03-24-003 | 8テーブル構成（av_プレフィックス） | 暗号通貨・Quote・ExchangeRateはスコープ外 |
| dec-2026-03-24-004 | frozen dataclass + DDL-first + Collector層でcamelCase変換 | EDINET/Polymarket パターン踏襲 |

## アクションアイテム

| ID | 内容 | 優先度 | 状態 |
|----|------|--------|------|
| act-2026-03-24-001 | Wave 1-2: storage_constants.py + models.py | 高 | pending |
| act-2026-03-24-002 | Wave 3: storage.py (DDL + upsert + get) | 高 | pending |
| act-2026-03-24-003 | Wave 4: collector.py (camelCase変換 + パイプライン) | 高 | pending |
| act-2026-03-24-004 | Wave 5: __init__.py + Property/統合テスト | 中 | pending |

## 成果物

| ドキュメント | パス |
|---|---|
| 設計書 (rev.2) | `docs/superpowers/specs/2026-03-24-alphavantage-storage-design.md` |
| 実装計画 | `docs/plan/2026-03-24_alphavantage-storage-implementation-plan.md` |
| ストレージアーキテクチャ参照 | `docs/plan/persistent-storage-architecture.md` |

## レビュー指摘と対応（主要9件）

| 指摘 | 対応 |
|---|---|
| company_overview DDL に13+フィールド欠落 | parser.py の _OVERVIEW_NUMERIC_FIELDS 32個を完全反映 |
| economic_indicators に maturity カラムなし | maturity カラム追加、PK に含めた |
| daily_prices に adjusted_close なし | adjusted_close REAL（NULL許容）追加 |
| camelCase→snake_case 変換戦略未定義 | Collector層に _camel_to_snake() + _SPECIAL_KEY_MAP |
| __init__ シグネチャ不一致 | `db_path: Path | None = None` に統一 |
| @lru_cache 問題 | 削除（PolymarketStorage に合わせる） |
| 暗号通貨テーブル欠落 | スコープ外として明記 |
| models.py 省略 | 全8 dataclass の全フィールドを明示 |
| CollectionSummary 未定義 | 追加定義 |

## 再開方法

「実装して」と言えば Wave 1 から順に TDD で進行。
Wave 1・2 は並列実行可能。
