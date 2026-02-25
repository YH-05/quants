---
name: drawio
description: Generate draw.io diagrams as .drawio files, optionally export to PNG/SVG/PDF with embedded XML
allowed-tools: Bash, Write
---

# Draw.io Diagram Skill

Generate draw.io diagrams as native `.drawio` files. Optionally export to PNG, SVG, or PDF with the diagram XML embedded (so the exported file remains editable in draw.io).

## How to create a diagram

1. **Generate draw.io XML** in mxGraphModel format for the requested diagram
2. **Write the XML** to a `.drawio` file in the current working directory using the Write tool
3. **If the user requested an export format** (png, svg, pdf), export using the draw.io CLI with `--embed-diagram`, then delete the source `.drawio` file
4. **If PNG export**: generate a **clean copy** without embedded XML metadata (see "Clean PNG generation" below)
5. **Open the result** — the exported file if exported, or the `.drawio` file otherwise

## Choosing the output format

Check the user's request for a format preference. Examples:

- `/drawio create a flowchart` → `flowchart.drawio`
- `/drawio png flowchart for login` → `login-flow.drawio.png`
- `/drawio svg: ER diagram` → `er-diagram.drawio.svg`
- `/drawio pdf architecture overview` → `architecture-overview.drawio.pdf`

If no format is mentioned, just write the `.drawio` file and open it in draw.io. The user can always ask to export later.

### Supported export formats

| Format | Embed XML | Notes |
|--------|-----------|-------|
| `png` | Yes (`-e`) | Viewable everywhere, editable in draw.io |
| `svg` | Yes (`-e`) | Scalable, editable in draw.io |
| `pdf` | Yes (`-e`) | Printable, editable in draw.io |
| `jpg` | No | Lossy, no embedded XML support |

PNG, SVG, and PDF all support `--embed-diagram` — the exported file contains the full diagram XML, so opening it in draw.io recovers the editable diagram.

## draw.io CLI

The draw.io desktop app includes a command-line interface for exporting.

### Locating the CLI

Try `drawio` first (works if on PATH), then fall back to the platform-specific path:

- **macOS**: `/Applications/draw.io.app/Contents/MacOS/draw.io`
- **Linux**: `drawio` (typically on PATH via snap/apt/flatpak)
- **Windows**: `"C:\Program Files\draw.io\draw.io.exe"`

Use `which drawio` (or `where drawio` on Windows) to check if it's on PATH before falling back.

### Export command

```bash
drawio -x -f <format> -e -b 10 -o <output> <input.drawio>
```

Key flags:
- `-x` / `--export`: export mode
- `-f` / `--format`: output format (png, svg, pdf, jpg)
- `-e` / `--embed-diagram`: embed diagram XML in the output (PNG, SVG, PDF only)
- `-o` / `--output`: output file path
- `-b` / `--border`: border width around diagram (default: 0)
- `-t` / `--transparent`: transparent background (PNG only)
- `-s` / `--scale`: scale the diagram size
- `--width` / `--height`: fit into specified dimensions (preserves aspect ratio)
- `-a` / `--all-pages`: export all pages (PDF only)
- `-p` / `--page-index`: select a specific page (1-based)

### Opening the result

- **macOS**: `open <file>`
- **Linux**: `xdg-open <file>`
- **Windows**: `start <file>`

## File naming

- Use a descriptive filename based on the diagram content (e.g., `login-flow`, `database-schema`)
- Use lowercase with hyphens for multi-word names
- For export, use double extensions: `name.drawio.png`, `name.drawio.svg`, `name.drawio.pdf` — this signals the file contains embedded diagram XML
- After a successful export, delete the intermediate `.drawio` file — the exported file contains the full diagram

### PNG export produces two files

| File | Purpose |
|------|---------|
| `name.drawio.png` | draw.io 再編集用（XML メタデータ埋め込み） |
| `name.png` | Claude API / 一般閲覧用（メタデータ除去済み） |

## Clean PNG generation

draw.io の `--embed-diagram` オプションは PNG の `zTXt` チャンクに mxGraphModel XML を埋め込む。このメタデータが含まれると **Claude API が画像を処理できず 400 エラーになる**。

PNG エクスポート後、必ず以下のコマンドでクリーン版を生成すること：

```bash
# macOS (sips を使用)
sips -s format png name.drawio.png --out name.png

# Linux (Python PIL を使用)
python3 -c "from PIL import Image; img = Image.open('name.drawio.png'); img.save('name.png', 'PNG', optimize=True)"
```

### 実行フロー（PNG の場合）

```
1. drawio -x -f png -e -b 10 -o name.drawio.png input.drawio
2. sips -s format png name.drawio.png --out name.png   ← クリーン版生成
3. rm input.drawio                                      ← 中間ファイル削除
4. open name.png                                        ← クリーン版を開く
```

**結果**: `name.drawio.png`（再編集用）と `name.png`（閲覧用）の2ファイルが残る。

## XML format

A `.drawio` file is native mxGraphModel XML. Always generate XML directly — Mermaid and CSV formats require server-side conversion and cannot be saved as native files.

### Basic structure

Every diagram must have this structure:

```xml
<mxGraphModel>
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <!-- Diagram cells go here with parent="1" -->
  </root>
</mxGraphModel>
```

- Cell `id="0"` is the root layer
- Cell `id="1"` is the default parent layer
- All diagram elements use `parent="1"` unless using multiple layers

### CRITICAL: No HTML in cell values (plain text only)

draw.io の `value` 属性には **プレーンテキストのみ** を使用すること。HTML タグ (`<b>`, `<br>`, `<font>` 等) を含めてはならない。

**理由**: エクスポートした PNG を Claude のビジョンモデルで読む際、HTML タグがそのままテキストとして認識され、図の内容が正確に読み取れなくなる。

#### 禁止パターン

```xml
<!-- WRONG: HTML tags in value -->
<mxCell value="<b>Title</b><br>subtitle<br><font color='#FF0000'>warning</font>" style="html=1;" .../>
```

#### 正しいパターン

```xml
<!-- CORRECT: plain text + style attributes for formatting -->
<mxCell value="Title&#xa;subtitle" style="fontStyle=1;fontColor=#333333;whiteSpace=wrap;" .../>
```

#### style 属性での装飾（HTML の代替）

| やりたいこと | HTML（禁止） | style 属性（推奨） |
|-------------|-------------|-------------------|
| 太字 | `<b>text</b>` | `fontStyle=1` |
| イタリック | `<i>text</i>` | `fontStyle=2` |
| 太字+イタリック | `<b><i>text</i></b>` | `fontStyle=3` |
| 下線 | `<u>text</u>` | `fontStyle=4` |
| 太字+下線 | `<b><u>text</u></b>` | `fontStyle=5` |
| 文字色 | `<font color="#F00">` | `fontColor=#FF0000` |
| 文字サイズ | `<font size="4">` | `fontSize=16` |
| 改行 | `<br>` | `&#xa;` (XML entity) |
| テキスト折り返し | HTML の wrap | `whiteSpace=wrap` |

`fontStyle` はビットフラグ: 1=bold, 2=italic, 4=underline（加算で組み合わせ）。

#### 複数行テキスト

改行には `&#xa;` を使用する。`<br>` は使わない。

```xml
<!-- CORRECT: multi-line with &#xa; -->
<mxCell value="Phase 1: ANALYSIS&#xa;データ収集 + 評価&#xa;2人/KB1活用" style="whiteSpace=wrap;" .../>

<!-- WRONG: <br> tags -->
<mxCell value="Phase 1: ANALYSIS<br>データ収集 + 評価<br>2人/KB1活用" style="html=1;" .../>
```

#### セル内の一部だけ装飾を変えたい場合

1つのセル内で一部だけ色やサイズを変える「混合フォーマット」が必要な場合は、**セルを分割する** ことで対応する。

```xml
<!-- CORRECT: separate cells for different formatting -->
<mxCell id="10" value="Main Title" style="fontStyle=1;fontSize=14;fontColor=#333333;" .../>
<mxCell id="11" value="subtitle text" style="fontSize=11;fontColor=#999999;" .../>

<!-- WRONG: mixed HTML in one cell -->
<mxCell value="<b style='font-size:14px'>Main Title</b><br><font color='#999'>subtitle text</font>" style="html=1;" .../>
```

### Common styles

**Rounded rectangle:**
```xml
<mxCell id="2" value="Label" style="rounded=1;whiteSpace=wrap;" vertex="1" parent="1">
  <mxGeometry x="100" y="100" width="120" height="60" as="geometry"/>
</mxCell>
```

**Multi-line rounded rectangle:**
```xml
<mxCell id="2" value="Title&#xa;description line" style="rounded=1;whiteSpace=wrap;fontStyle=1;" vertex="1" parent="1">
  <mxGeometry x="100" y="100" width="160" height="60" as="geometry"/>
</mxCell>
```

**Diamond (decision):**
```xml
<mxCell id="3" value="Condition?" style="rhombus;whiteSpace=wrap;" vertex="1" parent="1">
  <mxGeometry x="100" y="200" width="120" height="80" as="geometry"/>
</mxCell>
```

**Arrow (edge):**
```xml
<mxCell id="4" value="" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="2" target="3" parent="1">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

**Labeled arrow:**
```xml
<mxCell id="5" value="Yes" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="3" target="6" parent="1">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

### Useful style properties

| Property | Values | Use for |
|----------|--------|---------|
| `rounded=1` | 0 or 1 | Rounded corners |
| `whiteSpace=wrap` | wrap | Text wrapping |
| `fontStyle=1` | 1/2/3/4/5 | Bold/italic/both/underline/bold+underline |
| `fontSize=14` | number | Font size in pt |
| `fontFamily=Helvetica` | font name | Font family |
| `fillColor=#dae8fc` | Hex color | Background color |
| `strokeColor=#6c8ebf` | Hex color | Border color |
| `fontColor=#333333` | Hex color | Text color |
| `shape=cylinder3` | shape name | Database cylinders |
| `shape=mxgraph.flowchart.document` | shape name | Document shapes |
| `ellipse` | style keyword | Circles/ovals |
| `rhombus` | style keyword | Diamonds |
| `edgeStyle=orthogonalEdgeStyle` | style keyword | Right-angle connectors |
| `edgeStyle=elbowEdgeStyle` | style keyword | Elbow connectors |
| `dashed=1` | 0 or 1 | Dashed lines |
| `swimlane` | style keyword | Swimlane containers |

## CRITICAL rules

### XML well-formedness

- **NEVER use double hyphens (`--`) inside XML comments.** `--` is illegal inside `<!-- -->` per the XML spec and causes parse errors. Use single hyphens or rephrase.
- Escape special characters in attribute values: `&amp;`, `&lt;`, `&gt;`, `&quot;`
- Always use unique `id` values for each `mxCell`

### No HTML in cell values

- **NEVER use `html=1` in style attributes.** HTML mode causes `<b>`, `<br>`, `<font>` tags to appear as literal text when Claude reads the exported PNG.
- **NEVER use HTML tags** (`<b>`, `<br>`, `<font>`, `<i>`, `<u>`) in `value` attributes.
- Use `&#xa;` for line breaks, `fontStyle` / `fontColor` / `fontSize` in style for formatting.
- See "No HTML in cell values" section above for the complete reference.
