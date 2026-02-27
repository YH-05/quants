"""変換後のdocx内の表フォントサイズを10ptに調整するスクリプト."""

import sys

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt
from lxml import etree


def fix_table_fonts(
    docx_path: str, ascii_font: str, ja_font: str, size_pt: float
) -> None:
    """表内の全セルのフォントを設定."""
    doc = Document(docx_path)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(size_pt)
                        run.font.name = ascii_font
                        rpr = run._element.get_or_add_rPr()
                        r_fonts = rpr.find(qn("w:rFonts"))
                        if r_fonts is None:
                            r_fonts = etree.SubElement(rpr, qn("w:rFonts"))
                        r_fonts.set(qn("w:eastAsia"), ja_font)
                        r_fonts.set(qn("w:ascii"), ascii_font)
                        r_fonts.set(qn("w:hAnsi"), ascii_font)

    doc.save(docx_path)
    print(f"Table fonts fixed: {docx_path}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    if not target:
        print("Usage: python fix_table_font.py <docx_path>")
        sys.exit(1)
    fix_table_fonts(target, "Times New Roman", "游明朝", 10.0)
