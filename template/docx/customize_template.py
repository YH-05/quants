"""pandoc reference.docx のスタイルをカスタマイズするスクリプト."""

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from lxml import etree


def set_font(style, ascii_font: str, east_asia_font: str, size_pt: float) -> None:
    """フォントとサイズを設定."""
    font = style.font
    font.name = ascii_font
    font.size = Pt(size_pt)
    # 日本語フォント設定
    rpr = style.element.get_or_add_rPr()
    r_fonts = rpr.find(qn("w:rFonts"))
    if r_fonts is None:
        r_fonts = etree.SubElement(rpr, qn("w:rFonts"))
    r_fonts.set(qn("w:eastAsia"), east_asia_font)
    r_fonts.set(qn("w:ascii"), ascii_font)
    r_fonts.set(qn("w:hAnsi"), ascii_font)


def set_narrow_margins(doc: Document) -> None:
    """余白を狭く設定（上下1.5cm、左右1.5cm）."""
    for section in doc.sections:
        section.top_margin = Cm(1.5)
        section.bottom_margin = Cm(1.5)
        section.left_margin = Cm(1.5)
        section.right_margin = Cm(1.5)


def customize_template(input_path: str, output_path: str) -> None:
    """テンプレートをカスタマイズ."""
    doc = Document(input_path)

    ascii_font = "Times New Roman"
    ja_font = "游明朝"
    body_size = 10.5
    table_size = 10.0

    # -- 本文スタイル --
    body_styles = [
        "Normal",
        "Body Text",
        "First Paragraph",
        "Compact",
        "Block Text",
    ]
    for name in body_styles:
        try:
            style = doc.styles[name]
            set_font(style, ascii_font, ja_font, body_size)
        except KeyError:
            pass

    # -- 見出しスタイル --
    heading_sizes = {
        "Heading 1": 16,
        "Heading 2": 14,
        "Heading 3": 12,
        "Heading 4": 11,
        "Heading 5": 10.5,
    }
    for name, size in heading_sizes.items():
        try:
            style = doc.styles[name]
            set_font(style, ascii_font, ja_font, size)
            style.font.bold = True
        except KeyError:
            pass

    # -- 表スタイル（文字スタイル） --
    # pandocが使う表関連スタイルを設定
    table_styles_char = [
        "Table Normal",
    ]
    for name in table_styles_char:
        try:
            style = doc.styles[name]
            set_font(style, ascii_font, ja_font, table_size)
        except KeyError:
            pass

    # -- コードブロック --
    code_styles = ["Verbatim Char", "Source Code"]
    for name in code_styles:
        try:
            style = doc.styles[name]
            font = style.font
            font.name = "Consolas"
            font.size = Pt(9)
            rpr = style.element.get_or_add_rPr()
            r_fonts = rpr.find(qn("w:rFonts"))
            if r_fonts is None:
                r_fonts = etree.SubElement(rpr, qn("w:rFonts"))
            r_fonts.set(qn("w:eastAsia"), ja_font)
        except KeyError:
            pass

    # -- デフォルトフォント設定（文書全体） --
    doc_defaults = doc.styles.element.find(qn("w:docDefaults"))
    if doc_defaults is not None:
        rpr_default = doc_defaults.find(qn("w:rPrDefault"))
        if rpr_default is not None:
            rpr = rpr_default.find(qn("w:rPr"))
            if rpr is not None:
                r_fonts = rpr.find(qn("w:rFonts"))
                if r_fonts is None:
                    r_fonts = etree.SubElement(rpr, qn("w:rFonts"))
                r_fonts.set(qn("w:ascii"), ascii_font)
                r_fonts.set(qn("w:hAnsi"), ascii_font)
                r_fonts.set(qn("w:eastAsia"), ja_font)

                sz = rpr.find(qn("w:sz"))
                if sz is None:
                    sz = etree.SubElement(rpr, qn("w:sz"))
                sz.set(qn("w:val"), str(int(body_size * 2)))  # half-points

                sz_cs = rpr.find(qn("w:szCs"))
                if sz_cs is None:
                    sz_cs = etree.SubElement(rpr, qn("w:szCs"))
                sz_cs.set(qn("w:val"), str(int(body_size * 2)))

    # -- 余白を狭く --
    set_narrow_margins(doc)

    doc.save(output_path)
    print(f"Template saved: {output_path}")


if __name__ == "__main__":
    customize_template(
        "template/docx/reference.docx",
        "template/docx/reference.docx",
    )
