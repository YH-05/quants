# 議論メモ: ASEAN銘柄の無料データソース徹底調査

**日付**: 2026-03-18
**議論ID**: disc-2026-03-18-asean-data-sources
**参加**: ユーザー + AI

## 背景・コンテキスト

2026年3月からASEAN銘柄のカバレッジを仕事で開始。財務データ・マーケットデータを無料で取得する手段を徹底調査する必要があった。対象はASEAN主要6市場: シンガポール(SGX)、マレーシア(Bursa Malaysia)、タイ(SET)、インドネシア(IDX)、ベトナム(HOSE/HNX)、フィリピン(PSE)。

## 議論のサマリー

3並列エージェントで以下を調査:
1. **API調査**: 無料API、取引所公式データ、各国の対応状況を網羅的に調査
2. **yfinance実機テスト**: 各ASEAN取引所のティッカーで実際にデータ取得を試行（価格・企業情報・財務諸表・配当）
3. **代替ソース調査**: 国別Pythonパッケージ、Webスクレイピング候補、政府機関データ、無料枠ありアグリゲーター

### yfinance実機テスト結果

| 取引所 | サフィックス | ティッカー例 | 価格 | 財務諸表 | 配当 | 判定 |
|---|---|---|---|---|---|---|
| SGX | `.SI` | D05.SI (DBS), O39.SI (OCBC) | OK | OK (5期) | OK | **完全対応** |
| Bursa | `.KL` | 1155.KL (Maybank), 1295.KL (Public Bank) | OK | OK (4-5期) | OK | **完全対応** |
| SET | `.BK` | PTT.BK, KBANK.BK, ADVANC.BK | OK | OK (4-5期) | OK | **完全対応** |
| IDX | `.JK` | BBCA.JK, BBRI.JK, TLKM.JK | OK | OK (4-5期) | OK | **完全対応** |
| HOSE | `.VN` | VIC.VN, VNM.VN, FPT.VN | OK | OK (5期) | 一部 | **概ね対応** |
| PSE | `.PS` | SM.PS, BDO.PS | **NG** | **NG** | **NG** | **非対応** |

### 国別専用Pythonライブラリ

| 国 | ライブラリ | インストール | 主なデータ |
|---|---|---|---|
| ベトナム | **vnstock** | `pip install vnstock` | リアルタイム価格、財務諸表(BS/PL/CF)、指標。TCBS/SSI API。**ASEAN中最も成熟** |
| インドネシア | **idx-bei** | GitHub | 市場データ、企業プロフィール、財務比率、iXBRL。IDX公式APIスクレイパー |
| タイ | **thaifin** | `pip install thaifin` | 10年+ファンダメンタル、全銘柄リスト、セクターフィルタ |
| タイ | Settrade Open API | SDK | 無料サンドボックスあり。Python SDK提供 |
| マレーシア | Bursa Price API | API | 15年+ヒストリカル日次OHLCV |
| フィリピン | PSEStockAPI | GitHub | PSEリアルタイム株価。phisix APIは2023年11月停止済み |

### グローバルAPI（バックアップ）

| API | ASEAN対応 | 無料枠 | 評価 |
|---|---|---|---|
| **EODHD** | 6カ国全対応 | あり（制限付き） | 最も包括的なバックアップ |
| Twelve Data | SG/MY/TH/ID | 800コール/日 | VN/PH非対応 |
| FMP | 46カ国（要確認） | 250リクエスト/日（US銘柄のみ） | ASEAN銘柄は有料の可能性大 |
| Alpha Vantage | SGX停止済み | 25リクエスト/日 | ASEAN実用性低 |

### 注意事項

- **investpy は使用不可**: Investing.comのCloudflare V2保護により機能不全
- **yfinanceは非公式API**: 過度なリクエストでブロックされる可能性。キャッシュ実装推奨
- **マレーシアは数値コードティッカー**: 銘柄名→コード対応表の整備が必要（例: Maybank = 1155）
- **VNM注意**: `VNM`（サフィックスなし）はVanEck Vietnam ETF（米国上場）。Vinamilk = `VNM.VN`

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-18-006 | yfinance ASEAN対応: 5市場完全〜概ね対応、PSEのみ非対応 | 実機テスト済み。各取引所2-7銘柄で検証 |
| dec-2026-03-18-007 | 国別ライブラリ: VN=vnstock, ID=idx-bei, TH=thaifin, PH=PSEStockAPI | ファンダメンタル補完用 |
| dec-2026-03-18-008 | 3フェーズ実装戦略: yfinance拡張→国別統合→フィリピン対応 | Phase 1は最小工数で5市場カバー |

## アクションアイテム

| ID | 内容 | 優先度 | ステータス |
|----|------|--------|-----------|
| act-2026-03-18-001 | marketパッケージにASEANサフィックス対応実装（.SI, .KL, .BK, .JK, .VN） | medium | pending |
| act-2026-03-18-002 | vnstock / idx-bei / thaifin の実機検証と統合設計 | low | pending |
| act-2026-03-18-003 | フィリピン市場（PSE）のデータ取得手段確立 | low | pending |

## 次回の議論トピック

- Phase 1実装時のASEANティッカーマスタ管理方法（特にマレーシアの数値コード）
- vnstock/idx-bei/thaifinの実機検証結果と統合アーキテクチャ
- ASEAN銘柄の分析ワークフロー設計（既存ca-eval/dr-stockとの連携）

## 参考情報

### 主要リンク

- [yfinance](https://github.com/ranaroussi/yfinance) - 全6市場対応（PSE除く）
- [vnstock](https://github.com/thinh-vu/vnstock) - ベトナム専用（最も成熟）
- [idx-bei](https://github.com/nichsedge/idx-bei) - インドネシア専用
- [thaifin](https://github.com/ninyawee/thaifin) - タイ専用
- [Settrade Open API](https://developer.settrade.com/open-api/) - タイ公式
- [Bursa Price API](https://nikizwan.com/bursa-price-api/) - マレーシア
- [PSEStockAPI](https://github.com/edceliz/PSEStockAPI) - フィリピン
- [EODHD](https://eodhd.com/) - グローバル（ASEAN 6カ国全対応）
- [SGX Delayed Price Feed](https://www.sgx.com/data-connectivity/sgx-delayed-price-feed) - シンガポール公式（無料、10分遅延）
- [tradingview-screener](https://pypi.org/project/tradingview-screener/) - スクリーニング用
