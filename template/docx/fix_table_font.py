"""変換後のdocx内の表スタイルを調整するスクリプト.

- 表内フォント: Times New Roman / 游明朝 9pt
- 罫線: 実線（single）
- ヘッダー行下: 二重線（double）
"""

import sys

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt
from lxml import etree

# 罫線の太さ（1/8pt 単位。4 = 0.5pt）
BORDER_SIZE = "4"
BORDER_COLOR = "000000"


def _make_border_el(tag: str, val: str = "single") -> etree._Element:
    """w:top / w:bottom 等の罫線要素を生成."""
    el = etree.SubElement(etree.Element("dummy"), qn(f"w:{tag}"))
    el.set(qn("w:val"), val)
    el.set(qn("w:sz"), BORDER_SIZE)
    el.set(qn("w:space"), "0")
    el.set(qn("w:color"), BORDER_COLOR)
    return el


def set_table_borders(table) -> None:
    """表全体に実線罫線を設定."""
    tbl = table._tbl
    tbl_pr = tbl.find(qn("w:tblPr"))
    if tbl_pr is None:
        tbl_pr = etree.SubElement(tbl, qn("w:tblPr"))

    # 既存の tblBorders を削除
    existing = tbl_pr.find(qn("w:tblBorders"))
    if existing is not None:
        tbl_pr.remove(existing)

    borders = etree.SubElement(tbl_pr, qn("w:tblBorders"))
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        borders.append(_make_border_el(side, "single"))


def set_header_double_bottom(table) -> None:
    """ヘッダー行（1行目）の下罫線を二重線に設定."""
    if len(table.rows) == 0:
        return

    header_row = table.rows[0]
    for cell in header_row.cells:
        tc = cell._element
        tc_pr = tc.find(qn("w:tcPr"))
        if tc_pr is None:
            tc_pr = etree.SubElement(tc, qn("w:tcPr"))

        # 既存の tcBorders を削除
        existing = tc_pr.find(qn("w:tcBorders"))
        if existing is not None:
            tc_pr.remove(existing)

        tc_borders = etree.SubElement(tc_pr, qn("w:tcBorders"))
        # 上・左・右は実線
        tc_borders.append(_make_border_el("top", "single"))
        tc_borders.append(_make_border_el("left", "single"))
        tc_borders.append(_make_border_el("right", "single"))
        # 下を二重線
        tc_borders.append(_make_border_el("bottom", "double"))


def set_cell_font(run, ascii_font: str, ja_font: str, size_pt: float) -> None:
    """run のフォントを設定."""
    run.font.size = Pt(size_pt)
    run.font.name = ascii_font
    rpr = run._element.get_or_add_rPr()
    r_fonts = rpr.find(qn("w:rFonts"))
    if r_fonts is None:
        r_fonts = etree.SubElement(rpr, qn("w:rFonts"))
    r_fonts.set(qn("w:eastAsia"), ja_font)
    r_fonts.set(qn("w:ascii"), ascii_font)
    r_fonts.set(qn("w:hAnsi"), ascii_font)


def fix_tables(
    docx_path: str,
    ascii_font: str = "Times New Roman",
    ja_font: str = "游明朝",
    size_pt: float = 9.0,
) -> None:
    """表のフォント・罫線を一括調整."""
    doc = Document(docx_path)

    for table in doc.tables:
        # 罫線: 全体を実線に
        set_table_borders(table)
        # ヘッダー行の下を二重線に
        set_header_double_bottom(table)

        # フォント設定
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        set_cell_font(run, ascii_font, ja_font, size_pt)

    doc.save(docx_path)
    print(f"Tables fixed: {docx_path}")
    print(f"  Font: {ascii_font} / {ja_font} {size_pt}pt")
    print("  Borders: single (header bottom: double)")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    if not target:
        print("Usage: python fix_table_font.py <docx_path>")
        sys.exit(1)
    fix_tables(target)
