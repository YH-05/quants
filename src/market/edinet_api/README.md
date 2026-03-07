# market.edinet_api - EDINET 開示 API クライアント

金融庁の EDINET 開示 API (`api.edinet-fsa.go.jp`) クライアントモジュール。有価証券報告書・四半期報告書等の開示書類を検索・ダウンロードできる。

## 既存 edinet/ との違い

| 項目 | market.edinet (既存) | market.edinet_api (本モジュール) |
|------|---------------------|-------------------------------|
| API | EDINET DB API | EDINET 開示 API |
| ホスト | `edinetdb.jp` | `api.edinet-fsa.go.jp` |
| 用途 | 企業財務データ検索 | 開示書類の検索・ダウンロード |
| 環境変数 | `EDINET_DB_API_KEY` | `EDINET_FSA_API_KEY` |

## API キー設定

```bash
export EDINET_FSA_API_KEY="your-api-key-here"
```

API キーは [EDINET API](https://disclosure.edinet-fsa.go.jp/) から取得できる。

## 使用例

### 開示書類の検索

```python
from market.edinet_api import EdinetApiClient, EdinetApiConfig, DocumentType

config = EdinetApiConfig(api_key="your-api-key")
with EdinetApiClient(config=config) as client:
    # 指定日の開示書類を検索
    docs = client.search_documents("2025-01-15")

    # 有価証券報告書のみフィルタリング
    annual_reports = client.search_documents(
        "2025-01-15",
        doc_type=DocumentType.ANNUAL_REPORT,
    )
```

### 書類のダウンロード

```python
with EdinetApiClient(config=config) as client:
    # XBRL形式でダウンロード
    xbrl_data = client.download_document("S100ABCD", format="xbrl")

    # PDF形式でダウンロード
    pdf_data = client.download_document("S100ABCD", format="pdf")
```

### ZIP ファイルの解析

```python
from market.edinet_api import parse_xbrl_zip, extract_pdf

# XBRLファイルの抽出
xbrl_files = parse_xbrl_zip(xbrl_data)
for filename, content in xbrl_files.items():
    print(f"{filename}: {len(content)} bytes")

# PDFファイルの抽出
pdf_content = extract_pdf(pdf_data)
```

## モジュール構成

| ファイル | 責務 |
|---------|------|
| `constants.py` | BASE_URL, ALLOWED_HOSTS, 環境変数名 |
| `errors.py` | EdinetApiError 階層 (4クラス) |
| `types.py` | Config, DocumentType enum, DisclosureDocument |
| `session.py` | X-API-Key 認証 + httpx セッション |
| `client.py` | API クライアント (search + download) |
| `parsers.py` | XBRL/PDF パーサー |

## エラーハンドリング

```python
from market.edinet_api import (
    EdinetApiClient,
    EdinetApiError,
    EdinetApiAPIError,
    EdinetApiRateLimitError,
    EdinetApiValidationError,
)

try:
    docs = client.search_documents("2025-01-15")
except EdinetApiRateLimitError as e:
    print(f"Rate limited. Retry after: {e.retry_after}s")
except EdinetApiAPIError as e:
    print(f"API error {e.status_code}: {e.response_body}")
except EdinetApiValidationError as e:
    print(f"Validation error on field '{e.field}': {e.value}")
except EdinetApiError as e:
    print(f"General error: {e.message}")
```
