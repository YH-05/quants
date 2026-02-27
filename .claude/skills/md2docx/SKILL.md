---
name: md2docx
description: MarkdownをWord(.docx)に変換する。pandoc + カスタムテンプレート + 表フォント後処理を自動実行。/md2docx コマンドで使用。
allowed-tools: Read, Bash, Glob
---

# md2docx

pandoc を使用して Markdown ファイルを Word(.docx) に変換するスキルです。カスタムデザインテンプレート適用と表フォント後処理を自動実行します。

## 目的

このスキルは以下を提供します：

- **Markdown to Word 変換**: pandoc + reference.docx テンプレートによる高品質な変換
- **表フォント後処理**: 変換後の docx 内の表フォントを自動的に 10pt に調整
- **一貫したデザイン**: 游明朝/Times New Roman、余白 1.5cm、本文 10.5pt の統一フォーマット

## いつ使用するか

### プロアクティブ使用（自動的に検討）

以下の状況では、ユーザーが明示的に要求しなくても使用を検討：

1. **Markdown を Word に変換したい場合**
   - 「docx に変換して」「Word にして」
   - 「レポートを Word で出力して」

2. **分析レポートの納品物作成**
   - `/dr-stock` や `/ca-eval` で生成したレポートを Word 化
   - リサーチ結果の共有用ファイル作成

### 明示的な使用（ユーザー要求）

- `/md2docx <filepath>` コマンド
- 「Markdown を docx に変換して」という直接的な要求

## テンプレートのデザイン仕様

| 項目 | 設定値 |
|------|--------|
| 日本語フォント | 游明朝 |
| 英語フォント | Times New Roman |
| 本文フォントサイズ | 10.5pt |
| 表のフォントサイズ | 9pt（後処理で適用） |
| 表の罫線 | 実線（ヘッダー下は二重線） |
| 余白（上下左右） | 1.5cm |
| コードブロック | Consolas 9pt |
| 見出し1 | 16pt Bold |
| 見出し2 | 14pt Bold |
| 見出し3 | 12pt Bold |

## プロセス

### 1. 入力の検証

引数からMarkdownファイルパスを取得し、ファイルの存在を確認する。

```bash
# ファイル存在確認
ls -la <markdown_file>
```

- 出力先が `--output` で指定されていない場合、入力ファイルと同じディレクトリに `.docx` 拡張子で生成

### 2. ASCIIアートの文章化（前処理）

**重要: 元の Markdown ファイルは絶対に変更しないこと。**

Markdown ファイルを Read で読み込み、コードブロック（` ``` ` で囲まれた部分）内に ASCIIアート（矢印 `→←↑↓`、罫線 `─│┘┐`、ボックス `【】` 等を含む図表）がないか確認する。

#### ASCIIアートが検出された場合

1. ASCIIアートの内容を読み取り、**構造関係を正確に保った自然な日本語の文章**に変換する
2. 元のコードブロックを文章に置き換えた**一時 Markdown ファイル**を作成する（`.tmp/` ディレクトリに配置）
3. pandoc の入力はこの一時ファイルを使用する

#### 変換のガイドライン

- 階層関係（核心→補完→限定的 等）を段落や箇条書きで表現する
- 矢印が示す因果関係・相互関係を「〜は〜と相互補完する」等の文で表現する
- 注記（[T8修正] 等）は括弧書きで付記する
- 数値・固有名詞はそのまま維持する

#### 変換例

ASCIIアート:
```
【核心的優位性（70%）】
  #2 低分子経口GLP-1技術的差別化 ←→ #4 GLP-1供給能力参入障壁
          ↑ 技術力                     ↑ 設備投資
【補完的要素（50%）】
  #1 ポートフォリオ管理力 ─────────────────┘
```

変換後の文章:
```markdown
**核心的優位性（70%）**: 主張#2「低分子経口GLP-1技術的差別化」と主張#4「GLP-1供給能力参入障壁」は
相互に補完する関係にある。#2は技術力、#4は設備投資をそれぞれ基盤とする。

**補完的要素（50%）**: 主張#1「ポートフォリオ管理力」は核心的優位性を下支えする。
```

#### ASCIIアートが検出されなかった場合

一時ファイルは作成せず、元の Markdown ファイルをそのまま pandoc に渡す。

### 3. pandoc で Markdown を docx に変換

```bash
# ASCIIアートがあった場合は一時ファイルを使用
pandoc <input_or_temp.md> \
  --reference-doc=template/docx/reference.docx \
  -o <output.docx>
```

- `--reference-doc` でカスタムテンプレートを適用
- 游明朝/Times New Roman、余白 1.5cm、本文 10.5pt が適用される

### 4. 表フォントの後処理

```bash
uv run python template/docx/fix_table_font.py <output.docx>
```

- 表内の全セルのフォントを Times New Roman / 游明朝 9pt に調整
- 表の罫線を実線に、ヘッダー行の下罫線を二重線に設定
- pandoc の変換では表スタイルが正しく設定されないため、後処理が必要

### 5. クリーンアップと完了報告

```bash
# 一時ファイルがあれば削除
rm -f .tmp/<temp_file>.md

ls -lh <output.docx>
```

- 一時ファイルを削除
- 生成されたファイルのパスとサイズを表示

## 前提条件

| ツール | インストール方法 |
|--------|-----------------|
| pandoc | `brew install pandoc` |
| python-docx | `uv pip install python-docx` |

## テンプレートファイル

| ファイル | パス | 説明 |
|---------|------|------|
| reference.docx | `template/docx/reference.docx` | pandoc 用 Word テンプレート |
| customize_template.py | `template/docx/customize_template.py` | テンプレートスタイル設定スクリプト |
| fix_table_font.py | `template/docx/fix_table_font.py` | 表フォント後処理スクリプト |

## 使用例

### 例1: 基本的な変換

**状況**: CA評価レポートを Word に変換したい

**処理**:
```bash
/md2docx analyst/research/CA_eval_20260226-2021_LLY/04_output/revised-report-LLY.md
```

**結果**:
```
pandoc で変換完了: revised-report-LLY.docx
表フォント後処理完了: Times New Roman / 游明朝 10pt
出力: analyst/research/CA_eval_20260226-2021_LLY/04_output/revised-report-LLY.docx (245 KB)
```

---

### 例2: 出力先を指定して変換

**状況**: レポートを別のディレクトリに出力したい

**処理**:
```bash
/md2docx research/DR_stock_20260220_AAPL/04_output/report.md --output /tmp/AAPL_report.docx
```

**結果**:
```
pandoc で変換完了: AAPL_report.docx
表フォント後処理完了: Times New Roman / 游明朝 10pt
出力: /tmp/AAPL_report.docx (312 KB)
```

---

### 例3: ファイルが存在しない場合

**状況**: 指定したMarkdownファイルが存在しない

**処理**:
```bash
/md2docx nonexistent/report.md
```

**結果**:
```
エラー: ファイルが見つかりません: nonexistent/report.md
指定されたパスを確認してください。
```

---

### 例4: pandoc がインストールされていない場合

**状況**: pandoc が未インストール

**結果**:
```
エラー: pandoc がインストールされていません。
インストール方法: brew install pandoc
```

## 品質基準

### 必須（MUST）

- [ ] pandoc の `--reference-doc` オプションで `template/docx/reference.docx` を指定
- [ ] 変換後に `fix_table_font.py` で表フォントを後処理
- [ ] 出力ファイルのパスとサイズを報告
- [ ] 入力ファイルの存在を事前に確認
- [ ] ASCIIアートが含まれる場合は文章に変換してから pandoc に渡す
- [ ] 元の Markdown ファイルは絶対に変更しない（一時ファイルを使用）

### 推奨（SHOULD）

- pandoc のインストール状況を事前に確認
- エラー時に具体的な対処法を表示
- 変換元の Markdown ファイル名を出力ファイル名に使用
- 一時ファイルは変換完了後に削除する

## エラーハンドリング

### 入力ファイルが存在しない

**原因**: 指定されたパスに Markdown ファイルがない

**対処法**:
- パスを確認してエラーメッセージを表示
- Glob で類似ファイルを検索して候補を提示

### pandoc が未インストール

**原因**: pandoc がシステムにインストールされていない

**対処法**:
- `which pandoc` で確認
- `brew install pandoc` のインストール手順を表示

### python-docx が未インストール

**原因**: fix_table_font.py の実行に必要な python-docx がない

**対処法**:
- `uv pip install python-docx` のインストール手順を表示

### pandoc 変換エラー

**原因**: Markdown の構文エラー、テンプレートファイルの破損等

**対処法**:
- pandoc のエラーメッセージを表示
- テンプレートファイルの存在を確認（`template/docx/reference.docx`）

## 完了条件

- [ ] 入力 Markdown ファイルの存在が確認されている
- [ ] pandoc で docx への変換が成功している
- [ ] fix_table_font.py で表フォント後処理が完了している
- [ ] 出力ファイルのパスとサイズが報告されている

## 関連スキル

- **dr-stock**: 個別銘柄分析レポート生成（変換元レポートの生成元）
- **ca-eval**: 競争優位性評価レポート生成（変換元レポートの生成元）
- **deep-research**: ディープリサーチレポート生成（変換元レポートの生成元）

## 参考資料

- `template/docx/reference.docx`: pandoc 用 Word テンプレート
- `template/docx/customize_template.py`: テンプレートカスタマイズスクリプト
- `template/docx/fix_table_font.py`: 表フォント後処理スクリプト
