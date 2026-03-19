# 議論メモ: 全プロジェクト進捗スナップショット

**日付**: 2026-03-19
**議論ID**: disc-2026-03-19-progress-snapshot
**参加**: ユーザー + AI

## 背景・コンテキスト

quants プロジェクト全体の進捗を包括的に記録するスナップショット。
6プロジェクト・14アクションアイテム・20+決定事項の現在地を構造化。

## プロジェクト別進捗

### 1. quants-library（コアライブラリ）
- **ステータス**: Production 安定稼働
- **規模**: 14パッケージ・439ファイル・150,644行・11,103テスト
- **最大パッケージ**: market（108ファイル・45,621行・2,690テスト）
- **Claude Code設定**: 120エージェント・63スキル・31コマンド
- **最近の変更**: EDINET DB API修正、NASインフラ構築

### 2. quants-analyst-tacit-knowledge（暗黙知形式化）
- **ステータス**: Stage 2 部分完了
- **完了**: dogma v1.0（Y検証済み）、KB1(8ルール)/KB2(12パターン)/KB3(5 Few-shot)
- **完了**: ca-eval ワークフロー v1.0、12銘柄バッチ実行済み（AME, ATCOA, CPRT, LLY, LRCX, MCO, MNST, MSFT, NFLX, ORLY, POOL, VRSK）
- **課題**: 鏡問題（KBに準拠されると批判が難しい）、FM批判目線 vs AN推奨目線の分離が必要
- **次ステップ**: Out-of-sample検証（最優先）。リスト外+ボーダーライン混合銘柄で実施
- **ブロッカー**: 銘柄選定、Yレビュー回答待ち（9銘柄依頼済み）

### 3. quants-backtest-engine（汎用バックテストエンジン）
- **ステータス**: 詳細設計完了、実装未着手
- **設計**: Vectorized + Event-driven両モード、SOLID/DIP（market非依存）
- **コア**: BacktestData 3層コンテナ + PitGuard（PoiT構造的強制）
- **規模**: 6フェーズ・30+ファイル
- **設計文書**: `docs/plan/2026-02-25_backtest-engine-design.md`
- **重要**: MAS Phase 1 MVP のブロッカー

### 4. quants-mas-investment-team（MAS投資チーム）
- **ステータス**: 詳細設計完了、実装未着手
- **アーキテクチャ**: ハイブリッド（Python バックテスト + Claude Code Agent Teams）
- **構成**: 12エージェント・5フェーズ、マネージャー決定型+構造化ディベート
- **先読みバイアス排除**: 3層防御（PitGuard + 時間的制約 + ティッカー匿名化）
- **Phase 1 MVP**: 4四半期（2024Q1-Q4）、コスト ~$10-30/回
- **ブロッカー**: バックテストエンジン実装
- **設計文書**: `docs/plan/mas-multi-agent-investment-team-poc-plan.md`

### 5. quants-neo4j-kg（ナレッジグラフ）
- **ステータス**: Wave 1 一部実装済み
- **完了**: id_generator.py, neo4j-constraints.cypher, knowledge-graph-schema.yaml, 名前空間規約
- **未実装**: Wave 2-5（軽量mapper → リッチmapper → save-to-graph → 統合）
- **MCP構成**: neo4j-memory + neo4j-cypher + neo4j-data-modeling（運用中）

### 6. quants-edinet-db（EDINET DB）
- **ステータス**: 両モジュール実装完了・テスト全パス、データ投入進行中
- **market.edinet**: 10ファイル・4,826行・367テスト（EdinetClient, EdinetStorage, EdinetSyncer, CLI）
- **market.edinet_api**: 7ファイル・1,843行・134テスト（開示書類検索・DL、XBRL/PDFパーサー）
- **DuckDB**: 8テーブル作成済み、11/3,838社処理済み（Free: 100件/日）
- **Project 70**: Step 0 API実検証完了、Step 1-8未着手
- **最近の修正**: APIレスポンス/dataclassアライメント、429エラーハンドリング、Freeプラン定数修正

## インフラ

### NAS（2026-03-19完了）
- UGREEN DH2300-48C1, Tailscale v1.80.3
- SMB自動マウント: ~/bin/mount-nas.sh + launchd + macOS Keychain
- Quants データパス: /Volumes/personal_folder/Quants

### ASEAN データソース（2026-03-18調査完了）
- yfinance: SGX/Bursa/SET/IDX=完全対応、HOSE=概ね対応、PSE=非対応
- 3フェーズ戦略: Phase1=yfinance拡張 → Phase2=国別ライブラリ → Phase3=フィリピン対応

## アクションアイテム一覧

| ID | 内容 | 優先度 | ステータス |
|----|------|--------|-----------|
| act-2026-03-17-001 | バックテストエンジン実装開始（Phase 1基盤） | 高 | pending |
| act-2026-03-17-002 | MASエージェント群作成 | 中 | pending（バックテスト依存） |
| act-2026-03-17-003 | ca-eval In-sample検証 | 高 | on_hold（OOS優先） |
| act-2026-03-17-004 | Yレビュー（12銘柄）フィードバック取得 | 高 | in_progress（AMEレビュー済、9銘柄依頼中） |
| act-2026-03-17-005 | Phase 1仮説生成の改善 | 中 | pending（検証結果依存） |
| act-2026-03-17-006 | Neo4j KG Wave 2-5実装 | 低 | pending |
| act-2026-03-17-007 | Out-of-sample銘柄のAI Initial report作成 | 高 | pending（銘柄選定待ち） |
| act-2026-03-17-008 | Yフォロー（9銘柄レビュー、推奨ポイント記述） | 中 | pending |
| act-2026-03-18-002 | EDINET --resume 継続実行 | 高 | pending（コード修正完了、日次実行待ち） |
| act-2026-03-18-003 | フィリピンPSEデータ取得手段確立 | 低 | pending |
| act-2026-03-19-001 | Mac mini SSH鍵登録 | 低 | pending（Mac miniオフライン） |
| act-2026-03-19-002 | NAS再起動後Tailscale自動起動確認 | 中 | **completed**（2026-03-19 reboot→60秒以内に自動復帰確認済み） |
| act-2026-03-19-003 | UGOS FW更新後Tailscale永続化確認 | 中 | **completed**（/volume1/tailscale-backup/ にバイナリ+restore.sh配置済み） |

## 優先度マトリクス

### 最優先（今すぐ着手可能）
1. **EDINET --resume 日次実行**（act-2026-03-18-002）: コード修正済み、毎日0時リセット後に実行
2. **Yフォロー**（act-2026-03-17-008）: 9銘柄レビュー回答の催促

### 高優先（依存解決後）
3. **Out-of-sample AI report**（act-2026-03-17-007）: 銘柄選定が必要
4. **バックテストエンジン実装**（act-2026-03-17-001）: MASのブロッカー

### 低優先
7. **Neo4j KG Wave 2-5**（act-2026-03-17-006）
8. **フィリピンPSE**（act-2026-03-18-003）

## 決定事項

| ID | 内容 |
|----|------|
| dec-2026-03-19-003 | 全プロジェクト進捗スナップショットとして本文書を作成 |

## 次回の議論トピック

- Out-of-sample検証の銘柄選定（ボーダーライン+リスト外の具体的銘柄）
- バックテストエンジン実装の着手時期判断
- EDINET Proプラン移行の費用対効果
- Yレビュー結果に基づくKB改善方針

## 参考情報

- 全Discussion一覧: disc-2026-03-17-project-status, disc-2026-03-17-oos-planning, disc-2026-03-18-project-overview, disc-2026-03-18-edinet-db-status, disc-2026-03-18-asean-data-sources, disc-2026-03-18-edinet-sync-fix, disc-2026-03-18-edinet-api-alignment, disc-2026-03-19-nas-tailscale-setup
- Neo4j保存先: Discussion / Decision / ActionItem ノード
