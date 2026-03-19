"""types.py の単体テスト.

frozen dataclass 4種の生成・不変性・デフォルト値を検証する。
"""

from __future__ import annotations

import pytest

from academic.types import AcademicConfig, AuthorInfo, CitationInfo, PaperMetadata


class TestAuthorInfo:
    """AuthorInfo のテスト."""

    def test_正常系_全フィールドで生成できる(self) -> None:
        """全フィールド指定で AuthorInfo を生成できることを確認。"""
        author = AuthorInfo(
            name="John Doe",
            s2_author_id="12345",
            organization="MIT",
        )

        assert author.name == "John Doe"
        assert author.s2_author_id == "12345"
        assert author.organization == "MIT"

    def test_正常系_名前のみで生成できる(self) -> None:
        """名前のみで AuthorInfo を生成できることを確認。"""
        author = AuthorInfo(name="Jane Smith")

        assert author.name == "Jane Smith"
        assert author.s2_author_id is None
        assert author.organization is None

    def test_正常系_frozenで不変である(self) -> None:
        """AuthorInfo が frozen で属性を変更できないことを確認。"""
        author = AuthorInfo(name="Alice")

        with pytest.raises(AttributeError):
            author.name = "Bob"

    def test_正常系_同値のインスタンスは等しい(self) -> None:
        """同じ値の AuthorInfo が等しいことを確認。"""
        a1 = AuthorInfo(name="Alice", s2_author_id="1")
        a2 = AuthorInfo(name="Alice", s2_author_id="1")

        assert a1 == a2

    def test_正常系_異なる値のインスタンスは等しくない(self) -> None:
        """異なる値の AuthorInfo が等しくないことを確認。"""
        a1 = AuthorInfo(name="Alice")
        a2 = AuthorInfo(name="Bob")

        assert a1 != a2

    def test_正常系_ハッシュ可能である(self) -> None:
        """frozen dataclass がハッシュ可能であることを確認。"""
        author = AuthorInfo(name="Alice")
        author_set = {author}

        assert author in author_set


class TestCitationInfo:
    """CitationInfo のテスト."""

    def test_正常系_全フィールドで生成できる(self) -> None:
        """全フィールド指定で CitationInfo を生成できることを確認。"""
        citation = CitationInfo(
            title="Attention Is All You Need",
            arxiv_id="1706.03762",
            s2_paper_id="s2-abc123",
        )

        assert citation.title == "Attention Is All You Need"
        assert citation.arxiv_id == "1706.03762"
        assert citation.s2_paper_id == "s2-abc123"

    def test_正常系_タイトルのみで生成できる(self) -> None:
        """タイトルのみで CitationInfo を生成できることを確認。"""
        citation = CitationInfo(title="Sample Paper")

        assert citation.title == "Sample Paper"
        assert citation.arxiv_id is None
        assert citation.s2_paper_id is None

    def test_正常系_frozenで不変である(self) -> None:
        """CitationInfo が frozen で属性を変更できないことを確認。"""
        citation = CitationInfo(title="Test")

        with pytest.raises(AttributeError):
            citation.title = "Changed"

    def test_正常系_同値のインスタンスは等しい(self) -> None:
        """同じ値の CitationInfo が等しいことを確認。"""
        c1 = CitationInfo(title="Paper", arxiv_id="1234.56789")
        c2 = CitationInfo(title="Paper", arxiv_id="1234.56789")

        assert c1 == c2

    def test_正常系_ハッシュ可能である(self) -> None:
        """frozen dataclass がハッシュ可能であることを確認。"""
        citation = CitationInfo(title="Test")
        citation_set = {citation}

        assert citation in citation_set


class TestPaperMetadata:
    """PaperMetadata のテスト."""

    def test_正常系_全フィールドで生成できる(self) -> None:
        """全フィールド指定で PaperMetadata を生成できることを確認。"""
        authors = (AuthorInfo(name="Alice"),)
        refs = (CitationInfo(title="Ref 1"),)
        cites = (CitationInfo(title="Cite 1"),)

        paper = PaperMetadata(
            arxiv_id="2301.00001",
            title="Test Paper",
            authors=authors,
            references=refs,
            citations=cites,
            abstract="Abstract text",
            s2_paper_id="s2-001",
            published="2023-01-01T00:00:00Z",
            updated="2023-06-15T00:00:00Z",
        )

        assert paper.arxiv_id == "2301.00001"
        assert paper.title == "Test Paper"
        assert len(paper.authors) == 1
        assert paper.authors[0].name == "Alice"
        assert len(paper.references) == 1
        assert len(paper.citations) == 1
        assert paper.abstract == "Abstract text"
        assert paper.s2_paper_id == "s2-001"
        assert paper.published == "2023-01-01T00:00:00Z"
        assert paper.updated == "2023-06-15T00:00:00Z"

    def test_正常系_必須フィールドのみで生成できる(self) -> None:
        """必須フィールド（arxiv_id, title）のみで生成できることを確認。"""
        paper = PaperMetadata(
            arxiv_id="2301.00001",
            title="Minimal Paper",
        )

        assert paper.arxiv_id == "2301.00001"
        assert paper.title == "Minimal Paper"
        assert paper.authors == ()
        assert paper.references == ()
        assert paper.citations == ()
        assert paper.abstract is None
        assert paper.s2_paper_id is None
        assert paper.published is None
        assert paper.updated is None

    def test_正常系_frozenで不変である(self) -> None:
        """PaperMetadata が frozen で属性を変更できないことを確認。"""
        paper = PaperMetadata(arxiv_id="2301.00001", title="Test")

        with pytest.raises(AttributeError):
            paper.title = "Changed"

    def test_正常系_著者リストはタプルで順序保持される(self) -> None:
        """著者リストがタプルで順序が保持されることを確認。"""
        authors = (
            AuthorInfo(name="First"),
            AuthorInfo(name="Second"),
            AuthorInfo(name="Third"),
        )
        paper = PaperMetadata(
            arxiv_id="2301.00001",
            title="Test",
            authors=authors,
        )

        assert paper.authors[0].name == "First"
        assert paper.authors[1].name == "Second"
        assert paper.authors[2].name == "Third"

    def test_正常系_複数の参考文献と被引用を保持できる(self) -> None:
        """複数の参考文献と被引用を保持できることを確認。"""
        refs = (
            CitationInfo(title="Ref 1"),
            CitationInfo(title="Ref 2"),
        )
        cites = (
            CitationInfo(title="Cite 1"),
            CitationInfo(title="Cite 2"),
            CitationInfo(title="Cite 3"),
        )
        paper = PaperMetadata(
            arxiv_id="2301.00001",
            title="Test",
            references=refs,
            citations=cites,
        )

        assert len(paper.references) == 2
        assert len(paper.citations) == 3

    def test_正常系_同値のインスタンスは等しい(self) -> None:
        """同じ値の PaperMetadata が等しいことを確認。"""
        p1 = PaperMetadata(arxiv_id="2301.00001", title="Test")
        p2 = PaperMetadata(arxiv_id="2301.00001", title="Test")

        assert p1 == p2


class TestAcademicConfig:
    """AcademicConfig のテスト."""

    def test_正常系_デフォルト値で生成できる(self) -> None:
        """デフォルト値で AcademicConfig を生成できることを確認。"""
        config = AcademicConfig()

        assert config.s2_api_key is None
        assert config.s2_rate_limit == 1
        assert config.arxiv_rate_limit == 3
        assert config.cache_ttl == 604800
        assert config.max_retries == 3
        assert config.timeout == 30.0

    def test_正常系_全フィールドをカスタマイズできる(self) -> None:
        """全フィールドをカスタマイズして生成できることを確認。"""
        config = AcademicConfig(
            s2_api_key="my-key",
            s2_rate_limit=0.5,
            arxiv_rate_limit=1.0,
            cache_ttl=3600,
            max_retries=5,
            timeout=60.0,
        )

        assert config.s2_api_key == "my-key"
        assert config.s2_rate_limit == 0.5
        assert config.arxiv_rate_limit == 1.0
        assert config.cache_ttl == 3600
        assert config.max_retries == 5
        assert config.timeout == 60.0

    def test_正常系_frozenで不変である(self) -> None:
        """AcademicConfig が frozen で属性を変更できないことを確認。"""
        config = AcademicConfig()

        with pytest.raises(AttributeError):
            config.s2_rate_limit = 999

    def test_正常系_cache_ttlのデフォルトは7日(self) -> None:
        """cache_ttl のデフォルトが 604800 秒（7日）であることを確認。"""
        config = AcademicConfig()

        assert config.cache_ttl == 7 * 24 * 60 * 60

    def test_正常系_同値のインスタンスは等しい(self) -> None:
        """同じ値の AcademicConfig が等しいことを確認。"""
        c1 = AcademicConfig(s2_api_key="key")
        c2 = AcademicConfig(s2_api_key="key")

        assert c1 == c2

    def test_正常系_ハッシュ可能である(self) -> None:
        """frozen dataclass がハッシュ可能であることを確認。"""
        config = AcademicConfig()
        config_set = {config}

        assert config in config_set
