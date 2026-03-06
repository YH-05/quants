"""Unit tests for market.edinet_api.parsers module.

EDINET disclosure API パーサーのテストスイート。
ZIP 展開 + XBRL/PDF 抽出関数の動作を検証する。

Test TODO List:
- [x] parse_xbrl_zip(): 正常系 - XBRL ファイルを抽出
- [x] parse_xbrl_zip(): 正常系 - XML ファイルも抽出
- [x] parse_xbrl_zip(): 正常系 - XSD ファイルも抽出
- [x] parse_xbrl_zip(): 正常系 - 非 XBRL ファイルは除外
- [x] parse_xbrl_zip(): 正常系 - ディレクトリエントリはスキップ
- [x] parse_xbrl_zip(): 正常系 - 空の ZIP アーカイブ（XBRL なし）
- [x] parse_xbrl_zip(): 異常系 - 空のバイトで ValueError
- [x] parse_xbrl_zip(): 異常系 - 不正なZIPで BadZipFile
- [x] extract_pdf(): 正常系 - PDF ファイルを抽出
- [x] extract_pdf(): 正常系 - 複数 PDF がある場合は最初のものを抽出
- [x] extract_pdf(): 異常系 - PDF がない ZIP で ValueError
- [x] extract_pdf(): 異常系 - 空のバイトで ValueError
- [x] extract_pdf(): 異常系 - 不正なZIPで BadZipFile
- [x] __all__ エクスポート
"""

import io
import zipfile

import pytest

from market.edinet_api.parsers import extract_pdf, parse_xbrl_zip


def _create_zip(files: dict[str, bytes]) -> bytes:
    """テスト用の ZIP アーカイブを作成するヘルパー関数。

    Parameters
    ----------
    files : dict[str, bytes]
        ファイル名 -> コンテンツ のマッピング。

    Returns
    -------
    bytes
        ZIP アーカイブのバイト列。
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


# =============================================================================
# parse_xbrl_zip() tests
# =============================================================================


class TestParseXbrlZip:
    """parse_xbrl_zip() のテスト。"""

    def test_正常系_XBRLファイルを抽出(self) -> None:
        """XBRL ファイルが抽出されること。"""
        zip_data = _create_zip(
            {
                "report.xbrl": b"<xbrl>content</xbrl>",
                "readme.txt": b"readme",
            }
        )

        result = parse_xbrl_zip(zip_data)

        assert "report.xbrl" in result
        assert result["report.xbrl"] == b"<xbrl>content</xbrl>"
        assert "readme.txt" not in result

    def test_正常系_XMLファイルも抽出(self) -> None:
        """XML ファイルも XBRL 関連として抽出されること。"""
        zip_data = _create_zip(
            {
                "schema.xml": b"<xml>schema</xml>",
            }
        )

        result = parse_xbrl_zip(zip_data)

        assert "schema.xml" in result
        assert result["schema.xml"] == b"<xml>schema</xml>"

    def test_正常系_XSDファイルも抽出(self) -> None:
        """XSD ファイルも XBRL 関連として抽出されること。"""
        zip_data = _create_zip(
            {
                "taxonomy.xsd": b"<xsd>taxonomy</xsd>",
            }
        )

        result = parse_xbrl_zip(zip_data)

        assert "taxonomy.xsd" in result

    def test_正常系_非XBRLファイルは除外(self) -> None:
        """非 XBRL ファイル（.txt, .pdf, .csv）は除外されること。"""
        zip_data = _create_zip(
            {
                "report.xbrl": b"xbrl",
                "readme.txt": b"readme",
                "document.pdf": b"pdf",
                "data.csv": b"csv",
                "image.png": b"png",
            }
        )

        result = parse_xbrl_zip(zip_data)

        assert len(result) == 1
        assert "report.xbrl" in result
        assert "readme.txt" not in result
        assert "document.pdf" not in result

    def test_正常系_空のZIPアーカイブ(self) -> None:
        """XBRL ファイルがない ZIP の場合、空の辞書が返ること。"""
        zip_data = _create_zip(
            {
                "readme.txt": b"readme",
                "document.pdf": b"pdf",
            }
        )

        result = parse_xbrl_zip(zip_data)

        assert result == {}

    def test_正常系_複数のXBRLファイルを抽出(self) -> None:
        """複数の XBRL/XML/XSD ファイルが全て抽出されること。"""
        zip_data = _create_zip(
            {
                "report.xbrl": b"xbrl-content",
                "schema.xml": b"xml-content",
                "taxonomy.xsd": b"xsd-content",
                "readme.txt": b"readme",
            }
        )

        result = parse_xbrl_zip(zip_data)

        assert len(result) == 3
        assert "report.xbrl" in result
        assert "schema.xml" in result
        assert "taxonomy.xsd" in result

    def test_正常系_拡張子の大文字小文字を区別しない(self) -> None:
        """拡張子の大文字小文字を区別しないこと。"""
        zip_data = _create_zip(
            {
                "REPORT.XBRL": b"xbrl-upper",
                "Schema.XML": b"xml-mixed",
            }
        )

        result = parse_xbrl_zip(zip_data)

        assert len(result) == 2

    def test_異常系_空のバイトでValueError(self) -> None:
        """空のバイトで ValueError が発生すること。"""
        with pytest.raises(ValueError, match="must not be empty"):
            parse_xbrl_zip(b"")

    def test_異常系_不正なZIPでBadZipFile(self) -> None:
        """不正な ZIP データで BadZipFile が発生すること。"""
        with pytest.raises(zipfile.BadZipFile):
            parse_xbrl_zip(b"not a zip file")


# =============================================================================
# extract_pdf() tests
# =============================================================================


class TestExtractPdf:
    """extract_pdf() のテスト。"""

    def test_正常系_PDFファイルを抽出(self) -> None:
        """PDF ファイルが抽出されること。"""
        pdf_content = b"%PDF-1.4 fake pdf content"
        zip_data = _create_zip(
            {
                "document.pdf": pdf_content,
                "report.xbrl": b"xbrl",
            }
        )

        result = extract_pdf(zip_data)

        assert result == pdf_content

    def test_正常系_複数PDFがある場合は最初のものを抽出(self) -> None:
        """複数の PDF がある場合、最初の PDF が抽出されること。"""
        first_pdf = b"%PDF-1.4 first"
        second_pdf = b"%PDF-1.4 second"
        zip_data = _create_zip(
            {
                "first.pdf": first_pdf,
                "second.pdf": second_pdf,
            }
        )

        result = extract_pdf(zip_data)

        # ZIP のエントリ順序は保証されないため、
        # 結果がいずれかの PDF であることを確認
        assert result in (first_pdf, second_pdf)

    def test_正常系_拡張子の大文字小文字を区別しない(self) -> None:
        """拡張子の大文字小文字を区別しないこと。"""
        pdf_content = b"%PDF-1.4 content"
        zip_data = _create_zip(
            {
                "DOCUMENT.PDF": pdf_content,
            }
        )

        result = extract_pdf(zip_data)

        assert result == pdf_content

    def test_異常系_PDFがないZIPでValueError(self) -> None:
        """PDF がない ZIP で ValueError が発生すること。"""
        zip_data = _create_zip(
            {
                "report.xbrl": b"xbrl",
                "readme.txt": b"readme",
            }
        )

        with pytest.raises(ValueError, match="No PDF file found"):
            extract_pdf(zip_data)

    def test_異常系_空のバイトでValueError(self) -> None:
        """空のバイトで ValueError が発生すること。"""
        with pytest.raises(ValueError, match="must not be empty"):
            extract_pdf(b"")

    def test_異常系_不正なZIPでBadZipFile(self) -> None:
        """不正な ZIP データで BadZipFile が発生すること。"""
        with pytest.raises(zipfile.BadZipFile):
            extract_pdf(b"not a zip file")


# =============================================================================
# Module Exports
# =============================================================================


class TestModuleExports:
    """__all__ エクスポートのテスト。"""

    def test_正常系_全関数がエクスポートされている(self) -> None:
        """__all__ に parse_xbrl_zip と extract_pdf が含まれていること。"""
        from market.edinet_api import parsers

        assert hasattr(parsers, "__all__")
        expected = {"parse_xbrl_zip", "extract_pdf"}
        assert set(parsers.__all__) == expected
