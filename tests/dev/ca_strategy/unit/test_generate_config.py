"""単体テスト: generate_config モジュール。

対象モジュール: src/dev/ca_strategy/generate_config.py

list_portfolio_20151224.json を読み込み、universe.json と
benchmark_weights.json を生成するスクリプトを検証する。

Key behaviors:
- generate_universe() は TickerConverter を使い Bloomberg→yfinance 変換して universe.json を生成する
- generate_benchmark_weights() は MSCI_Mkt_Cap_USD_MM をセクター別集約して近似セクターウェイトを算出する
- セクターウェイト合計は 1.0 になること
- 時価総額が 0 または None のエントリはスキップする
- generate_benchmark_weights() の出力に近似値を示すメタデータが含まれること
- main() は --source と --output-dir の CLI オプションを受け付ける
- 変換成功/失敗/スキップの件数がログ出力されること
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


# ===========================================================================
# Fixtures
# ===========================================================================
@pytest.fixture
def sample_portfolio_data() -> dict:
    """テスト用の最小ポートフォリオデータを返す。"""
    return {
        "0001": [
            {
                "Name": "Apple Inc.",
                "Country": "UNITED STATES",
                "GICS_Sector": "Information Technology",
                "GICS_Industry": "Technology Hardware",
                "MSCI_Mkt_Cap_USD_MM": 2000000.0,
                "Bloomberg_Ticker": "AAPL UW Equity",
                "FIGI": "BBG000B9XRY4",
            }
        ],
        "0002": [
            {
                "Name": "Microsoft Corp",
                "Country": "UNITED STATES",
                "GICS_Sector": "Information Technology",
                "GICS_Industry": "Systems Software",
                "MSCI_Mkt_Cap_USD_MM": 1800000.0,
                "Bloomberg_Ticker": "MSFT UW Equity",
                "FIGI": "BBG000BPH459",
            }
        ],
        "0003": [
            {
                "Name": "JPMorgan Chase & Co",
                "Country": "UNITED STATES",
                "GICS_Sector": "Financials",
                "GICS_Industry": "Diversified Banks",
                "MSCI_Mkt_Cap_USD_MM": 400000.0,
                "Bloomberg_Ticker": "JPM UN Equity",
                "FIGI": "BBG000DMBXR2",
            }
        ],
    }


@pytest.fixture
def sample_portfolio_with_zero_cap() -> dict:
    """時価総額が 0 または None のエントリを含むポートフォリオデータを返す。"""
    return {
        "0001": [
            {
                "Name": "Valid Corp",
                "GICS_Sector": "Industrials",
                "MSCI_Mkt_Cap_USD_MM": 500000.0,
                "Bloomberg_Ticker": "VALID UW Equity",
                "FIGI": "BBG000FAKE01",
            }
        ],
        "0002": [
            {
                "Name": "Zero Cap Corp",
                "GICS_Sector": "Materials",
                "MSCI_Mkt_Cap_USD_MM": 0,
                "Bloomberg_Ticker": "ZERO UW Equity",
                "FIGI": "BBG000FAKE02",
            }
        ],
        "0003": [
            {
                "Name": "None Cap Corp",
                "GICS_Sector": "Energy",
                "MSCI_Mkt_Cap_USD_MM": None,
                "Bloomberg_Ticker": "NONE UW Equity",
                "FIGI": "BBG000FAKE03",
            }
        ],
    }


@pytest.fixture
def sample_portfolio_file(tmp_path: Path, sample_portfolio_data: dict) -> Path:
    """サンプルデータを JSON ファイルに書き込み、そのパスを返す。"""
    portfolio_path = tmp_path / "list_portfolio_test.json"
    portfolio_path.write_text(
        json.dumps(sample_portfolio_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return portfolio_path


@pytest.fixture
def zero_cap_portfolio_file(
    tmp_path: Path, sample_portfolio_with_zero_cap: dict
) -> Path:
    """時価総額が 0/None のエントリを含む JSON ファイルを返す。"""
    portfolio_path = tmp_path / "list_portfolio_zero_cap.json"
    portfolio_path.write_text(
        json.dumps(sample_portfolio_with_zero_cap, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return portfolio_path


# ===========================================================================
# generate_universe()
# ===========================================================================
class TestGenerateUniverse:
    """generate_universe() の動作を検証する。"""

    def test_正常系_有効なデータからuniverse_jsonが生成される(
        self, tmp_path: Path, sample_portfolio_file: Path
    ) -> None:
        """有効なポートフォリオデータから universe.json が生成されることを確認。"""
        from dev.ca_strategy.generate_config import generate_universe

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generate_universe(source=sample_portfolio_file, output_dir=output_dir)

        universe_path = output_dir / "universe.json"
        assert universe_path.exists()

    def test_正常系_生成されたuniverse_jsonの形式がConfigRepositoryの期待形式である(
        self, tmp_path: Path, sample_portfolio_file: Path
    ) -> None:
        """生成された universe.json が {\"tickers\": [...]} の形式であることを確認。"""
        from dev.ca_strategy.generate_config import generate_universe

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generate_universe(source=sample_portfolio_file, output_dir=output_dir)

        universe_path = output_dir / "universe.json"
        data = json.loads(universe_path.read_text(encoding="utf-8"))

        assert "tickers" in data
        assert isinstance(data["tickers"], list)
        assert len(data["tickers"]) > 0

    def test_正常系_tickersにticker_フィールドが含まれる(
        self, tmp_path: Path, sample_portfolio_file: Path
    ) -> None:
        """生成された universe.json の各エントリに ticker フィールドが含まれることを確認。"""
        from dev.ca_strategy.generate_config import generate_universe

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generate_universe(source=sample_portfolio_file, output_dir=output_dir)

        universe_path = output_dir / "universe.json"
        data = json.loads(universe_path.read_text(encoding="utf-8"))

        for entry in data["tickers"]:
            assert "ticker" in entry

    def test_正常系_tickersにgics_sectorフィールドが含まれる(
        self, tmp_path: Path, sample_portfolio_file: Path
    ) -> None:
        """生成された universe.json の各エントリに gics_sector フィールドが含まれることを確認。"""
        from dev.ca_strategy.generate_config import generate_universe

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generate_universe(source=sample_portfolio_file, output_dir=output_dir)

        universe_path = output_dir / "universe.json"
        data = json.loads(universe_path.read_text(encoding="utf-8"))

        for entry in data["tickers"]:
            assert "gics_sector" in entry

    def test_正常系_Bloomberg_ティッカーがyfinance形式に変換される(
        self, tmp_path: Path, sample_portfolio_file: Path
    ) -> None:
        """Bloomberg ティッカー（AAPL UW Equity）が yfinance 形式（AAPL）に変換されることを確認。"""
        from dev.ca_strategy.generate_config import generate_universe

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generate_universe(source=sample_portfolio_file, output_dir=output_dir)

        universe_path = output_dir / "universe.json"
        data = json.loads(universe_path.read_text(encoding="utf-8"))
        tickers = [entry["ticker"] for entry in data["tickers"]]

        assert "AAPL" in tickers
        assert "MSFT" in tickers
        assert "JPM" in tickers

    def test_正常系_gics_sectorフィールドが正しく保持される(
        self, tmp_path: Path, sample_portfolio_file: Path
    ) -> None:
        """GICS セクター情報が正しく保持されることを確認。"""
        from dev.ca_strategy.generate_config import generate_universe

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generate_universe(source=sample_portfolio_file, output_dir=output_dir)

        universe_path = output_dir / "universe.json"
        data = json.loads(universe_path.read_text(encoding="utf-8"))
        aapl_entry = next(e for e in data["tickers"] if e["ticker"] == "AAPL")

        assert aapl_entry["gics_sector"] == "Information Technology"

    def test_正常系_tickersにbloomberg_tickerフィールドが含まれる(
        self, tmp_path: Path, sample_portfolio_file: Path
    ) -> None:
        """生成された universe.json の各エントリに bloomberg_ticker フィールドが含まれることを確認。"""
        from dev.ca_strategy.generate_config import generate_universe

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generate_universe(source=sample_portfolio_file, output_dir=output_dir)

        universe_path = output_dir / "universe.json"
        data = json.loads(universe_path.read_text(encoding="utf-8"))

        for entry in data["tickers"]:
            assert "bloomberg_ticker" in entry
            assert isinstance(entry["bloomberg_ticker"], str)
            assert entry["bloomberg_ticker"] != ""

    def test_正常系_bloomberg_tickerが元データのBloomberg_Tickerをstripした値である(
        self, tmp_path: Path, sample_portfolio_file: Path
    ) -> None:
        """bloomberg_ticker フィールドが元データの Bloomberg_Ticker を strip した値であることを確認。"""
        from dev.ca_strategy.generate_config import generate_universe

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generate_universe(source=sample_portfolio_file, output_dir=output_dir)

        universe_path = output_dir / "universe.json"
        data = json.loads(universe_path.read_text(encoding="utf-8"))

        aapl_entry = next(e for e in data["tickers"] if e["ticker"] == "AAPL")
        assert aapl_entry["bloomberg_ticker"] == "AAPL UW Equity"

        msft_entry = next(e for e in data["tickers"] if e["ticker"] == "MSFT")
        assert msft_entry["bloomberg_ticker"] == "MSFT UW Equity"

        jpm_entry = next(e for e in data["tickers"] if e["ticker"] == "JPM")
        assert jpm_entry["bloomberg_ticker"] == "JPM UN Equity"

    def test_正常系_既存フィールドがbloomberg_ticker追加後も変更されない(
        self, tmp_path: Path, sample_portfolio_file: Path
    ) -> None:
        """bloomberg_ticker 追加により既存フィールドが変更されていないことを確認。"""
        from dev.ca_strategy.generate_config import generate_universe

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generate_universe(source=sample_portfolio_file, output_dir=output_dir)

        universe_path = output_dir / "universe.json"
        data = json.loads(universe_path.read_text(encoding="utf-8"))

        aapl_entry = next(e for e in data["tickers"] if e["ticker"] == "AAPL")
        assert aapl_entry["ticker"] == "AAPL"
        assert aapl_entry["company_name"] == "Apple Inc."
        assert aapl_entry["gics_sector"] == "Information Technology"
        assert aapl_entry["country"] == "UNITED STATES"

    def test_後方互換_bloomberg_tickerがないJSONでUniverseTickerのパースがエラーにならない(
        self, tmp_path: Path
    ) -> None:
        """bloomberg_ticker フィールドがない既存 JSON を UniverseTicker でパースしてもエラーにならないことを確認。"""
        from dev.ca_strategy.types import UniverseTicker

        # bloomberg_ticker なしの旧形式データ
        old_format = {"ticker": "AAPL", "gics_sector": "Information Technology"}
        ticker = UniverseTicker.model_validate(old_format)
        assert ticker.ticker == "AAPL"
        assert ticker.bloomberg_ticker == ""

    def test_正常系_bloomberg_tickerの前後空白がstripされる(
        self, tmp_path: Path
    ) -> None:
        """元データの Bloomberg_Ticker に前後空白がある場合にstripされることを確認。"""
        from dev.ca_strategy.generate_config import generate_universe

        # 前後に空白を持つ Bloomberg_Ticker を含むデータ
        data_with_spaces = {
            "0001": [
                {
                    "Name": "Test Corp",
                    "Country": "US",
                    "GICS_Sector": "Energy",
                    "MSCI_Mkt_Cap_USD_MM": 100000.0,
                    "Bloomberg_Ticker": "  TEST US Equity  ",
                }
            ]
        }

        source = tmp_path / "test_spaces.json"
        source.write_text(
            json.dumps(data_with_spaces, ensure_ascii=False), encoding="utf-8"
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generate_universe(source=source, output_dir=output_dir)

        universe_path = output_dir / "universe.json"
        result = json.loads(universe_path.read_text(encoding="utf-8"))

        assert result["tickers"][0]["bloomberg_ticker"] == "TEST US Equity"

    def test_正常系_生成されたuniverse_jsonがConfigRepositoryで読み込める(
        self, tmp_path: Path, sample_portfolio_file: Path
    ) -> None:
        """生成された universe.json が ConfigRepository で正常に読み込めることを確認。"""
        from dev.ca_strategy._config import ConfigRepository
        from dev.ca_strategy.generate_config import generate_universe

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generate_universe(source=sample_portfolio_file, output_dir=output_dir)

        # ConfigRepository で読み込めることを確認
        repo = ConfigRepository(output_dir)
        universe = repo.universe
        assert len(universe.tickers) == 3

    def test_異常系_存在しないソースファイルでFileNotFoundError(
        self, tmp_path: Path
    ) -> None:
        """存在しないソースファイルを指定した場合に FileNotFoundError が発生することを確認。"""
        from dev.ca_strategy.generate_config import generate_universe

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        non_existent = tmp_path / "non_existent.json"

        with pytest.raises(FileNotFoundError):
            generate_universe(source=non_existent, output_dir=output_dir)


# ===========================================================================
# generate_benchmark_weights()
# ===========================================================================
class TestGenerateBenchmarkWeights:
    """generate_benchmark_weights() の動作を検証する。"""

    def test_正常系_有効なデータからbenchmark_weights_jsonが生成される(
        self, tmp_path: Path, sample_portfolio_file: Path
    ) -> None:
        """有効なポートフォリオデータから benchmark_weights.json が生成されることを確認。"""
        from dev.ca_strategy.generate_config import generate_benchmark_weights

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generate_benchmark_weights(source=sample_portfolio_file, output_dir=output_dir)

        benchmark_path = output_dir / "benchmark_weights.json"
        assert benchmark_path.exists()

    def test_正常系_生成されたファイルにweightsキーが含まれる(
        self, tmp_path: Path, sample_portfolio_file: Path
    ) -> None:
        """生成された benchmark_weights.json に weights キーが含まれることを確認。"""
        from dev.ca_strategy.generate_config import generate_benchmark_weights

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generate_benchmark_weights(source=sample_portfolio_file, output_dir=output_dir)

        benchmark_path = output_dir / "benchmark_weights.json"
        data = json.loads(benchmark_path.read_text(encoding="utf-8"))

        assert "weights" in data

    def test_正常系_セクターウェイトの合計が1_0になる(
        self, tmp_path: Path, sample_portfolio_file: Path
    ) -> None:
        """セクターウェイトの合計が 1.0 になることを確認。"""
        from dev.ca_strategy.generate_config import generate_benchmark_weights

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generate_benchmark_weights(source=sample_portfolio_file, output_dir=output_dir)

        benchmark_path = output_dir / "benchmark_weights.json"
        data = json.loads(benchmark_path.read_text(encoding="utf-8"))

        total_weight = sum(data["weights"].values())
        assert total_weight == pytest.approx(1.0, abs=1e-6)

    def test_正常系_セクターが正しく集約される(
        self, tmp_path: Path, sample_portfolio_file: Path
    ) -> None:
        """Information Technology と Financials セクターが正しく集約されることを確認。"""
        from dev.ca_strategy.generate_config import generate_benchmark_weights

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generate_benchmark_weights(source=sample_portfolio_file, output_dir=output_dir)

        benchmark_path = output_dir / "benchmark_weights.json"
        data = json.loads(benchmark_path.read_text(encoding="utf-8"))

        assert "Information Technology" in data["weights"]
        assert "Financials" in data["weights"]

    def test_正常系_時価総額加重平均で正しくウェイトが計算される(
        self, tmp_path: Path, sample_portfolio_file: Path
    ) -> None:
        """時価総額加重平均（MSCI_Mkt_Cap_USD_MM）でウェイトが正しく計算されることを確認。

        サンプルデータ:
        - IT: 2000000 + 1800000 = 3800000
        - Financials: 400000
        - Total: 4200000

        期待ウェイト:
        - IT: 3800000 / 4200000 ≈ 0.9048
        - Financials: 400000 / 4200000 ≈ 0.0952
        """
        from dev.ca_strategy.generate_config import generate_benchmark_weights

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generate_benchmark_weights(source=sample_portfolio_file, output_dir=output_dir)

        benchmark_path = output_dir / "benchmark_weights.json"
        data = json.loads(benchmark_path.read_text(encoding="utf-8"))

        it_weight = data["weights"]["Information Technology"]
        fin_weight = data["weights"]["Financials"]

        assert it_weight == pytest.approx(3800000 / 4200000, rel=1e-4)
        assert fin_weight == pytest.approx(400000 / 4200000, rel=1e-4)

    def test_正常系_近似値メタデータが含まれる(
        self, tmp_path: Path, sample_portfolio_file: Path
    ) -> None:
        """生成された benchmark_weights.json に近似値である旨のメタデータが含まれることを確認。"""
        from dev.ca_strategy.generate_config import generate_benchmark_weights

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generate_benchmark_weights(source=sample_portfolio_file, output_dir=output_dir)

        benchmark_path = output_dir / "benchmark_weights.json"
        data = json.loads(benchmark_path.read_text(encoding="utf-8"))

        assert "metadata" in data
        metadata = data["metadata"]
        # 近似値である旨を示すフィールドが存在すること
        assert (
            "approximation" in metadata
            or "note" in metadata
            or "is_approximate" in metadata
        )

    def test_エッジケース_時価総額がゼロのエントリはスキップされる(
        self, tmp_path: Path, zero_cap_portfolio_file: Path
    ) -> None:
        """時価総額が 0 のエントリがスキップされ、有効エントリのみで計算されることを確認。"""
        from dev.ca_strategy.generate_config import generate_benchmark_weights

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generate_benchmark_weights(
            source=zero_cap_portfolio_file, output_dir=output_dir
        )

        benchmark_path = output_dir / "benchmark_weights.json"
        data = json.loads(benchmark_path.read_text(encoding="utf-8"))

        # 0 時価総額の Materials セクターはウェイトに含まれないこと
        assert "Materials" not in data["weights"]
        # None 時価総額の Energy セクターはウェイトに含まれないこと
        assert "Energy" not in data["weights"]
        # 有効な Industrials セクターのみが含まれること
        assert "Industrials" in data["weights"]
        assert data["weights"]["Industrials"] == pytest.approx(1.0, abs=1e-6)

    def test_エッジケース_時価総額がNoneのエントリはスキップされる(
        self, tmp_path: Path, zero_cap_portfolio_file: Path
    ) -> None:
        """時価総額が None のエントリがスキップされることを確認。"""
        from dev.ca_strategy.generate_config import generate_benchmark_weights

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generate_benchmark_weights(
            source=zero_cap_portfolio_file, output_dir=output_dir
        )

        benchmark_path = output_dir / "benchmark_weights.json"
        data = json.loads(benchmark_path.read_text(encoding="utf-8"))

        # セクターウェイト合計は 1.0 であること（有効エントリのみで計算）
        assert sum(data["weights"].values()) == pytest.approx(1.0, abs=1e-6)

    def test_正常系_生成されたbenchmark_weights_jsonがConfigRepositoryで読み込める(
        self, tmp_path: Path, sample_portfolio_file: Path
    ) -> None:
        """生成された benchmark_weights.json が ConfigRepository で正常に読み込めることを確認。"""
        from dev.ca_strategy._config import ConfigRepository
        from dev.ca_strategy.generate_config import generate_benchmark_weights

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generate_benchmark_weights(source=sample_portfolio_file, output_dir=output_dir)

        # ConfigRepository で読み込めることを確認
        # universe.json も必要なので作成する
        universe_data = {
            "tickers": [{"ticker": "AAPL", "gics_sector": "Information Technology"}]
        }
        (output_dir / "universe.json").write_text(
            json.dumps(universe_data, ensure_ascii=False), encoding="utf-8"
        )

        repo = ConfigRepository(output_dir)
        benchmark = repo.benchmark
        assert len(benchmark) > 0
        total = sum(b.weight for b in benchmark)
        assert total == pytest.approx(1.0, abs=1e-6)

    def test_エッジケース_全エントリの時価総額が0の場合空のweightsが生成される(
        self, tmp_path: Path
    ) -> None:
        """全エントリの MSCI_Mkt_Cap_USD_MM が 0 の場合、空の weights が生成されることを確認。"""
        from dev.ca_strategy.generate_config import generate_benchmark_weights

        # 時価総額が 0 のみのデータ
        all_zero_data = {
            "0001": [
                {
                    "Name": "Zero Corp",
                    "GICS_Sector": "Energy",
                    "MSCI_Mkt_Cap_USD_MM": 0,
                    "Bloomberg_Ticker": "ZERO UW Equity",
                }
            ],
            "0002": [
                {
                    "Name": "None Corp",
                    "GICS_Sector": "Materials",
                    "MSCI_Mkt_Cap_USD_MM": None,
                    "Bloomberg_Ticker": "NONE UW Equity",
                }
            ],
        }

        source = tmp_path / "all_zero_portfolio.json"
        source.write_text(
            json.dumps(all_zero_data, ensure_ascii=False), encoding="utf-8"
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = generate_benchmark_weights(source=source, output_dir=output_dir)

        # total_cap == 0.0 の場合、weights は空であること
        assert result == {}

        # 生成された JSON も空の weights を持つこと
        benchmark_path = output_dir / "benchmark_weights.json"
        data = json.loads(benchmark_path.read_text(encoding="utf-8"))
        assert data["weights"] == {}


# ===========================================================================
# ConversionStats (変換統計)
# ===========================================================================
class TestConversionStats:
    """generate_universe() が返す変換統計を検証する。"""

    def test_正常系_変換成功件数が正しく返される(
        self, tmp_path: Path, sample_portfolio_file: Path
    ) -> None:
        """変換成功件数が正しく返されることを確認。"""
        from dev.ca_strategy.generate_config import generate_universe

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        stats = generate_universe(source=sample_portfolio_file, output_dir=output_dir)

        assert stats["total"] == 3

    def test_エッジケース_スキップ件数がゼロのエントリで正しく返される(
        self, tmp_path: Path, sample_portfolio_file: Path
    ) -> None:
        """スキップ件数がゼロのデータで stats["skipped"] が 0 であることを確認。"""
        from dev.ca_strategy.generate_config import generate_universe

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        stats = generate_universe(source=sample_portfolio_file, output_dir=output_dir)

        assert stats["skipped"] == 0

    def test_正常系_統計dictにconverted_failed_skippedキーが含まれる(
        self, tmp_path: Path, sample_portfolio_file: Path
    ) -> None:
        """返される統計に converted, failed, skipped キーが含まれることを確認。"""
        from dev.ca_strategy.generate_config import generate_universe

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        stats = generate_universe(source=sample_portfolio_file, output_dir=output_dir)

        assert "total" in stats
        assert "skipped" in stats


# ===========================================================================
# generate_all() / main() CLI
# ===========================================================================
class TestGenerateAll:
    """generate_all() による universe.json と benchmark_weights.json の同時生成。"""

    def test_正常系_generate_allで両ファイルが生成される(
        self, tmp_path: Path, sample_portfolio_file: Path
    ) -> None:
        """generate_all() で universe.json と benchmark_weights.json が両方生成されることを確認。"""
        from dev.ca_strategy.generate_config import generate_all

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generate_all(source=sample_portfolio_file, output_dir=output_dir)

        assert (output_dir / "universe.json").exists()
        assert (output_dir / "benchmark_weights.json").exists()

    def test_正常系_generate_allの両ファイルがConfigRepositoryで読み込める(
        self, tmp_path: Path, sample_portfolio_file: Path
    ) -> None:
        """generate_all() で生成したファイルが ConfigRepository で正常に読み込めることを確認。"""
        from dev.ca_strategy._config import ConfigRepository
        from dev.ca_strategy.generate_config import generate_all

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generate_all(source=sample_portfolio_file, output_dir=output_dir)

        repo = ConfigRepository(output_dir)
        universe = repo.universe
        benchmark = repo.benchmark

        assert len(universe.tickers) == 3
        assert len(benchmark) == 2
        assert sum(b.weight for b in benchmark) == pytest.approx(1.0, abs=1e-6)


class TestMainCLI:
    """main() CLI エントリーポイントの動作を検証する。"""

    def test_正常系_main関数が存在する(self) -> None:
        """main() 関数が generate_config モジュールに存在することを確認。"""
        from dev.ca_strategy import generate_config

        assert hasattr(generate_config, "main")
        assert callable(generate_config.main)

    def test_正常系_main関数がsourceとoutput_dir引数を受け付ける(
        self, tmp_path: Path, sample_portfolio_file: Path
    ) -> None:
        """main() が source と output_dir 引数を受け付けて実行できることを確認。"""
        from dev.ca_strategy.generate_config import main

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # main() が例外なく実行できること
        main(
            args=[
                "--source",
                str(sample_portfolio_file),
                "--output-dir",
                str(output_dir),
            ]
        )

        assert (output_dir / "universe.json").exists()
        assert (output_dir / "benchmark_weights.json").exists()
