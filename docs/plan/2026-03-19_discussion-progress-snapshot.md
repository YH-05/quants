# 議論メモ: 全プロジェクト進捗スナップショット

**日付**: 2026-03-19（最終更新: 2026-03-19 深夜）
**議論ID**: disc-2026-03-19-progress-snapshot
**最終セッションID**: disc-2026-03-19-session-final-snapshot
**参加**: ユーザー + AI

## 背景・コンテキスト

quants プロジェクト全体の進捗を包括的に記録するスナップショット。
8プロジェクト・20+アクションアイテム・30+決定事項の現在地を構造化。

## 本日 (2026-03-19) の主要成果

| # | 成果 | 詳細 |
|---|------|------|
| 1 | KG v2.0→v2.2 スキーマ拡張・実装 | +4ノード+12リレーション、emit_graph_queue + save-to-graph対応 |
| 2 | JSAI 2026 全34論文 KG投入 | 6バッチ並列→408ノード・629リレーション新規、UNWINDバッチ(1078→21回) |
| 3 | KG品質改善 C+→B | 孤立0、confidence100%、Topic48→21、Entity20→69 |
| 4 | リサーチ統合 | academic+web-researcher並列。提案1(GNN×MAS)=高、提案2(KG×LLM Alpha)=非常に高 |
| 5 | **Project #92 academic 全完了** | **全7 Issue Done、PR #3809マージ、worktreeクリーンアップ済み** |
| 6 | Neo4j品質評価+MemoryMCP廃止 | Memoryノード61件削除、UNIQUE制約全14ノード |
| 7 | NAS Tailscale+UGOS対策完了 | cron @reboot、/volume1バックアップ+restore.sh |
| 8 | **ASEAN 6取引所基盤 PR #3783** | **26 Issue (#3776-#3801) 全完了。asean_common+6取引所サブパッケージ+EODHDスケルトン+レビュー改善** |

**KG最終状態**: 1,075ノード / 2,846リレーション / 16ノードタイプ / 品質B

## プロジェクト別進捗

### 1. quants-library（コアライブラリ）
- **ステータス**: Production 安定稼働
- **規模**: 15パッケージ・450+ファイル・155,000+行・11,100+テスト（academic追加）
- **最大パッケージ**: market（108ファイル・45,621行・2,690テスト）
- **Claude Code設定**: 120エージェント・63スキル・31コマンド
- **最近の変更**: ASEAN 6取引所基盤(PR #3783)、academic パッケージ(PR #3809)、KGスキーマv2.2拡張、EDINET DB API修正、NASインフラ構築

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
- **ステータス**: v2.2スキーマ運用中、品質B
- **規模**: 1,075ノード / 2,846リレーション / 16ノードタイプ
- **完了**: id_generator.py, neo4j-constraints.cypher(14ノード全制約), knowledge-graph-schema.yaml(v2.2), 名前空間規約
- **完了**: JSAI 2026全34論文投入、品質改善8項目、MemoryMCP廃止
- **MCP構成**: neo4j-cypher + neo4j-data-modeling（運用中）※neo4j-memory廃止済み

### 5b. quants-academic（学術論文メタデータ取得）★NEW
- **ステータス**: **全完了** (Project #92, PR #3809マージ済み)
- **構成**: S2 API(主) + arXiv API(フォールバック) + SQLiteCache + PaperFetcher + graph-queue Mapper + CLI
- **依存**: database, edgar(RateLimiter), market(SQLiteCache), utils_core
- **全7 Issue Done**: #3802〜#3808

### 6. quants-asean（ASEAN 6取引所基盤）★NEW
- **ステータス**: **Phase 1 完了** (PR #3783マージ済み、26 Issue: #3776-#3801)
- **asean_common**: AseanMarket enum、TickerRecord、ExchangeConfig基底クラス、AseanTickerStorage(DuckDB)、screener.py(tradingview-screener)
- **6取引所サブパッケージ**: SGX/Bursa/SET/IDX/HOSE/PSE（各 constants/types/errors）
- **EODHD**: APIスケルトン（全メソッドNotImplementedError、型定義・テスト完備）
- **品質**: panderaスキーマ検証、SQLインジェクション防止、ILIKEエスケープ、Hypothesisプロパティテスト、CVE対応(requests>=2.32.0)
- **テスト**: 500+件（79 asean_common + 166 6取引所基盤 + 46 EODHD + 72 init + PRレビュー追加分）
- **DRY改善**: ExchangeConfig基底クラスで~420行→~210行、Exchange共通エラー階層統合、FREDError/BloombergError→MarketError継承統一
- **次ステップ**: Phase 2 = 国別ライブラリ統合(vnstock/idx-bei/thaifin)、Phase 3 = フィリピン対応

### 7. quants-edinet-db（EDINET DB）
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

### 完了済み (2026-03-19)

| ID | 内容 | ステータス |
|----|------|-----------|
| act-2026-03-19-001 | graph-queueリレーションキー名をfrom_id/to_idに統一 | **completed** |
| act-2026-03-19-002 | venue統一（JSAI 2026 SIG-FIN） | **completed** |
| act-2026-03-19-003 | JSAI論文間CITESリレーション追加 | **completed** |
| act-2026-03-19-004 | Wave 3A/3B: PaperFetcher + Mapper + CLI | **completed** |
| act-2026-03-19-005 | Wave 4: バックフィル + ドキュメント | **completed** |
| act-2026-03-19-NAS-002 | NAS再起動後Tailscale自動起動確認 | **completed** |
| act-2026-03-19-NAS-003 | UGOS FW更新後Tailscale永続化確認 | **completed** |

### 未完了

| ID | 内容 | 優先度 | ステータス |
|----|------|--------|-----------|
| act-2026-03-17-001 | バックテストエンジン実装開始（Phase 1基盤） | 高 | pending |
| act-2026-03-17-002 | MASエージェント群作成 | 中 | pending（バックテスト依存） |
| act-2026-03-17-003 | ca-eval In-sample検証 | 高 | on_hold（OOS優先） |
| act-2026-03-17-004 | Yレビュー（12銘柄）フィードバック取得 | 高 | in_progress（AMEレビュー済、9銘柄依頼中） |
| act-2026-03-17-005 | Phase 1仮説生成の改善 | 中 | pending（検証結果依存） |
| act-2026-03-17-007 | Out-of-sample銘柄のAI Initial report作成 | 高 | pending（銘柄選定待ち） |
| act-2026-03-17-008 | Yフォロー（9銘柄レビュー、推奨ポイント記述） | 中 | pending |
| act-2026-03-18-002 | EDINET --resume 継続実行 | 高 | in_progress（106/3838社） |
| act-2026-03-18-003 | フィリピンPSEデータ取得手段確立 | 低 | pending |
| act-2026-03-19-006 | ins-0004(HMM×Attention仮説)バックテスト実装 | 高 | pending |
| act-2026-03-19-007 | bearish論文の意図的収集（CONTRADICTS構築） | 中 | pending |
| act-2026-03-19-008 | ins-0003(MAS×LLM Alpha Mining統合)設計書作成 | 中 | pending |
| act-2026-03-19-009 | v2スキーマ自動投入パイプライン検証 | 高 | pending |
| act-2026-03-19-MAC | Mac mini SSH鍵登録 | 低 | pending（オフライン） |

## 優先度マトリクス

### 最優先（今すぐ着手可能）
1. **EDINET --resume 日次実行**（act-2026-03-18-002）: 106/3,838社処理済み、日次継続
2. **Yフォロー**（act-2026-03-17-008）: 9銘柄レビュー回答の催促
3. **v2パイプライン検証**（act-2026-03-19-009）: 新論文1件でend-to-end投入テスト

### 高優先（依存解決後）
4. **Out-of-sample AI report**（act-2026-03-17-007）: 銘柄選定が必要
5. **バックテストエンジン実装**（act-2026-03-17-001）: MASのブロッカー
6. **HMM×Attention仮説バックテスト**（act-2026-03-19-006）: factor パッケージ

### 中優先
7. **bearish論文収集**（act-2026-03-19-007）: KG CONTRADICTS拡充
8. **MAS×LLM Alpha Mining設計書**（act-2026-03-19-008）

### 低優先
9. **フィリピンPSE**（act-2026-03-18-003）

## 決定事項（本日分）

| ID | 内容 |
|----|------|
| dec-2026-03-19-001 | 34論文を6バッチ並列エージェントで処理、graph-queue JSON経由Neo4j投入 |
| dec-2026-03-19-002 | UNWINDバッチCypherで投入効率化（1078→21回） |
| dec-2026-03-19-003 | from/to→from_id/to_idキー正規化ステップ追加 |
| dec-2026-03-19-004 | UNIQUE制約を全14ノードに追加完了 |
| dec-2026-03-19-005 | 推論パス3種検証済み（アノマリー別比較、無料データ実装、共通攻略未組合Method） |
| dec-2026-03-19-006〜009 | emit_graph_queue v2対応、save-to-graph v2対応、PE拡充、REQUIRES_DATA拡充 |
| dec-2026-03-19-010〜013 | academic: S2主/arXivフォールバック、既存コード再利用、schema v2.1、Project #92構成 |
| dec-2026-03-19-020 | EDINET Proプラン検討削除（Freeで十分） |
| dec-2026-03-19-021〜022 | NAS Tailscale cron @reboot確定、UGOS /volume1バックアップ方式 |
| dec-2026-03-19-023〜024 | KGスキーマv2.2拡張、Topic統合方針（source_count=1→親マージ） |
| dec-2026-03-19-025 | **Project #92 全7 Issue完了・PR #3809マージ** |
| dec-2026-03-19-026 | KG最終: 1,075ノード/2,846リレーション/16ノードタイプ/品質B |
| dec-2026-03-19-030 | **ASEAN 6取引所基盤 PR #3783完了（26 Issue: #3776-#3801）** |
| dec-2026-03-19-031 | PRレビュー改善11項目（DRY/セキュリティ/パフォーマンス/テスト/CVE対応） |

## 次回の議論トピック

- Out-of-sample検証の銘柄選定（ボーダーライン+リスト外の具体的銘柄）
- バックテストエンジン実装の着手時期判断
- Yレビュー結果に基づくKB改善方針
- v2パイプラインend-to-end検証結果
- 創発的戦略提案クエリの実行（MAS×KG, GNN×MASギャップから新戦略生成）
- academic パッケージのバックフィル実行（既存34+論文の著者・引用取得）

## 参考情報

- 全Discussion一覧（2026-03-19）: disc-2026-03-19-kg-v2-schema, disc-2026-03-19-kg-v2-implementation, disc-2026-03-19-research-integration, disc-2026-03-19-jsai2026-kg-import, disc-2026-03-19-neo4j-quality-cleanup, disc-2026-03-19-kg-quality-improvement, disc-2026-03-19-arxiv-pipeline, disc-2026-03-19-asean-implementation, disc-2026-03-19-session-final-snapshot
- 全Discussion一覧（過去）: disc-2026-03-17-project-status, disc-2026-03-17-oos-planning, disc-2026-03-18-project-overview, disc-2026-03-18-edinet-db-status, disc-2026-03-18-asean-data-sources, disc-2026-03-18-edinet-sync-fix, disc-2026-03-18-edinet-api-alignment, disc-2026-03-19-nas-tailscale-setup
- Neo4j保存先: Discussion / Decision / ActionItem ノード
