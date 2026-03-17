# タスク 06: .env.example を更新

- **Issue**: [#2845](https://github.com/YH-05/quants/issues/2845)
- **ステータス**: todo

## 概要

`.env.example` ファイルを更新し、新しいパス設定オプションのドキュメントを追加する。

## 対象ファイル

- `.env.example`

## 実装内容

以下の内容を `.env.example` に追加:

```bash
# Finance Library Configuration
# Copy this file to .env and fill in your values

# =============================================================================
# Path Configuration (Optional)
# =============================================================================
# These are optional. If not set, paths are resolved relative to the current
# working directory.

# Custom .env file path (default: ./.env)
# DOTENV_PATH=/path/to/custom/.env

# Data directory (default: ./data)
# DATA_DIR=/path/to/data

# FRED historical cache directory (default: ./data/raw/fred/indicators)
# FRED_HISTORICAL_CACHE_DIR=/path/to/cache

# FRED series configuration file (default: ./data/config/fred_series.json)
# FRED_SERIES_ID_JSON=/path/to/fred_series.json

# =============================================================================
# API Keys (Required for full functionality)
# =============================================================================

# FRED API Key (https://fred.stlouisfed.org/docs/api/api_key.html)
FRED_API_KEY=

# Tavily API Key (for web search)
TAVILY_API_KEY=
```

## 受け入れ条件

- [ ] DOTENV_PATH の説明が追加されている
- [ ] DATA_DIR の説明が追加されている
- [ ] FRED_HISTORICAL_CACHE_DIR の説明が追加されている
- [ ] FRED_SERIES_ID_JSON の説明が追加されている
- [ ] 各オプションのデフォルト値が明記されている
- [ ] コメントが英語で記載されている

## 依存関係

- depends_on: [#2842](https://github.com/YH-05/quants/issues/2842), [#2843](https://github.com/YH-05/quants/issues/2843), [#2844](https://github.com/YH-05/quants/issues/2844)
- blocks: なし

## 見積もり

15分
