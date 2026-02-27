---
description: MarkdownファイルをWord(.docx)に変換します。pandocでカスタムテンプレートを適用し、表フォントの後処理も自動実行します。
argument-hint: <markdown_file> [--output <output_path>]
---

# /md2docx - Markdown to Word 変換

Markdown ファイルを pandoc + カスタムテンプレートで Word(.docx) に変換するコマンドです。

## 使用例

```bash
# 基本的な変換（同じディレクトリに .docx を生成）
/md2docx analyst/research/CA_eval_20260226-2021_LLY/04_output/revised-report-LLY.md

# 出力先を指定
/md2docx research/DR_stock_20260220_AAPL/04_output/report.md --output /tmp/AAPL_report.docx

# 週次レポートを変換
/md2docx research/weekly/2026-02-24_weekly-report.md
```

## 入力パラメータ

| パラメータ | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| `markdown_file` | Yes | - | 変換対象の Markdown ファイルパス |
| `--output` | No | 入力と同じディレクトリに `.docx` | 出力先ファイルパス |

## 処理フロー

```
Step 1: 入力検証
├── 引数パース（markdown_file, --output）
├── ファイル存在確認
├── pandoc インストール確認
└── テンプレートファイル存在確認

Step 2: pandoc 変換
└── pandoc <input.md> --reference-doc=template/docx/reference.docx -o <output.docx>

Step 3: 表フォント後処理
└── uv run python template/docx/fix_table_font.py <output.docx>

Step 4: 完了報告
└── ファイルパス・サイズ表示
```

## 実行手順

### Step 1: 引数のパース

1. **第1引数**を `markdown_file` として取得（必須）
2. `--output` オプションを取得（任意）
3. 出力先が未指定の場合、入力ファイルと同じディレクトリに `.md` を `.docx` に置換して出力先を決定

### Step 2: 事前検証

```bash
# ファイル存在確認
ls -la <markdown_file>

# pandoc インストール確認
which pandoc

# テンプレート存在確認
ls -la template/docx/reference.docx
```

### Step 3: pandoc で変換

```bash
pandoc <markdown_file> \
  --reference-doc=template/docx/reference.docx \
  -o <output.docx>
```

### Step 4: 表フォント後処理

```bash
uv run python template/docx/fix_table_font.py <output.docx>
```

### Step 5: 完了報告

```bash
ls -lh <output.docx>
```

以下の形式で報告：

```
## 変換完了

- 入力: <markdown_file>
- 出力: <output.docx>
- サイズ: <file_size>

テンプレート: template/docx/reference.docx
表フォント後処理: 完了（Times New Roman / 游明朝 10pt）
```

## デザイン仕様

| 項目 | 設定値 |
|------|--------|
| 日本語フォント | 游明朝 |
| 英語フォント | Times New Roman |
| 本文サイズ | 10.5pt |
| 表フォントサイズ | 9pt |
| 表の罫線 | 実線（ヘッダー下は二重線） |
| 余白（上下左右） | 1.5cm |
| コードブロック | Consolas 9pt |
| 見出し1 | 16pt Bold |
| 見出し2 | 14pt Bold |
| 見出し3 | 12pt Bold |

## エラーハンドリング

### Markdown ファイルが指定されていない

```
エラー: Markdown ファイルパスが必要です。

使用法: /md2docx <markdown_file> [--output <output_path>]

例:
  /md2docx report.md
  /md2docx report.md --output /tmp/report.docx
```

### ファイルが存在しない

```
エラー: ファイルが見つかりません: <path>
指定されたパスを確認してください。
```

### pandoc が未インストール

```
エラー: pandoc がインストールされていません。
インストール: brew install pandoc
```

## テンプレートファイル

| ファイル | パス | 説明 |
|---------|------|------|
| reference.docx | `template/docx/reference.docx` | pandoc 用 Word テンプレート |
| fix_table_font.py | `template/docx/fix_table_font.py` | 表フォント後処理スクリプト |
| customize_template.py | `template/docx/customize_template.py` | テンプレートスタイル設定 |

## 関連コマンド

| コマンド | 説明 |
|----------|------|
| `/dr-stock` | 個別銘柄分析レポート生成 |
| `/ca-eval` | 競争優位性評価レポート生成 |
| `/finance-research` | 金融リサーチワークフロー |
