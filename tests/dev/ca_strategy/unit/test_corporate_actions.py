"""単体テスト: corporate_actions.json のスキーマバリデーション。

対象ファイル: research/ca_strategy_poc/config/corporate_actions.json

ユニバース内消失8企業のコーポレートアクション情報が正しく定義されていることを検証する。
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

# =============================================================================
# Constants
# =============================================================================
_CONFIG_DIR = (
    Path(__file__).resolve().parents[4] / "research" / "ca_strategy_poc" / "config"
)
_CORPORATE_ACTIONS_PATH = _CONFIG_DIR / "corporate_actions.json"
_UNIVERSE_PATH = _CONFIG_DIR / "universe.json"

_EXPECTED_TICKERS = frozenset({"ALTR", "ARM", "EMC", "MON", "CA", "LIN", "UTX", "S"})
_ALLOWED_ACTION_TYPES = frozenset({"delisting", "merger"})
_PORTFOLIO_DATE = date(2015, 12, 31)
_REQUIRED_FIELDS = frozenset(
    {"ticker", "company_name", "action_date", "action_type", "reason"}
)


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture(scope="module")
def corporate_actions_data() -> dict[str, Any]:
    """corporate_actions.json の内容を読み込むフィクスチャ。"""
    raw = _CORPORATE_ACTIONS_PATH.read_text(encoding="utf-8")
    return json.loads(raw)


@pytest.fixture(scope="module")
def actions_list(corporate_actions_data: dict[str, Any]) -> list[dict[str, Any]]:
    """corporate_actions リストを返すフィクスチャ。"""
    return corporate_actions_data["corporate_actions"]


@pytest.fixture(scope="module")
def universe_tickers() -> set[str]:
    """universe.json の全ティッカーを返すフィクスチャ。"""
    raw = _UNIVERSE_PATH.read_text(encoding="utf-8")
    data = json.loads(raw)
    return {t["ticker"] for t in data["tickers"]}


# =============================================================================
# JSON ファイルの読み込みとスキーマバリデーション
# =============================================================================
class TestCorporateActionsSchema:
    """corporate_actions.json のスキーマバリデーションテスト。"""

    def test_正常系_JSONファイルが存在する(self) -> None:
        """corporate_actions.json が所定のパスに存在することを確認。"""
        assert _CORPORATE_ACTIONS_PATH.exists(), (
            f"corporate_actions.json not found: {_CORPORATE_ACTIONS_PATH}"
        )

    def test_正常系_JSONとして正しくパースできる(self) -> None:
        """corporate_actions.json が有効なJSONとしてパース可能であることを確認。"""
        raw = _CORPORATE_ACTIONS_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)

        assert isinstance(data, dict)

    def test_正常系_corporate_actionsキーが存在する(
        self, corporate_actions_data: dict[str, Any]
    ) -> None:
        """トップレベルに corporate_actions キーが存在することを確認。"""
        assert "corporate_actions" in corporate_actions_data

    def test_正常系_corporate_actionsがリストである(
        self, actions_list: list[dict[str, Any]]
    ) -> None:
        """corporate_actions がリスト型であることを確認。"""
        assert isinstance(actions_list, list)

    def test_正常系_各エントリに必須フィールドが含まれる(
        self, actions_list: list[dict[str, Any]]
    ) -> None:
        """各エントリに ticker, company_name, action_date, action_type, reason が含まれることを確認。"""
        for action in actions_list:
            missing = _REQUIRED_FIELDS - set(action.keys())
            assert not missing, (
                f"ticker={action.get('ticker', '?')}: missing fields: {missing}"
            )


# =============================================================================
# ティッカーの存在確認
# =============================================================================
class TestCorporateActionsTickers:
    """消失8企業のティッカー存在確認テスト。"""

    def test_正常系_全8社のティッカーが存在する(
        self, actions_list: list[dict[str, Any]]
    ) -> None:
        """全8社のエントリが存在することを確認。"""
        actual_tickers = {a["ticker"] for a in actions_list}

        assert actual_tickers == _EXPECTED_TICKERS

    def test_正常系_エントリ数が8件である(
        self, actions_list: list[dict[str, Any]]
    ) -> None:
        """エントリ数が正確に8件であることを確認。"""
        assert len(actions_list) == 8

    def test_正常系_全ティッカーがuniverse_jsonに存在する(
        self, actions_list: list[dict[str, Any]], universe_tickers: set[str]
    ) -> None:
        """全ティッカーが universe.json に含まれることを確認。"""
        for action in actions_list:
            ticker = action["ticker"]
            assert ticker in universe_tickers, (
                f"ticker={ticker} not found in universe.json"
            )

    def test_正常系_ティッカーに重複がない(
        self, actions_list: list[dict[str, Any]]
    ) -> None:
        """ティッカーに重複がないことを確認。"""
        tickers = [a["ticker"] for a in actions_list]

        assert len(tickers) == len(set(tickers)), (
            f"Duplicate tickers found: {[t for t in tickers if tickers.count(t) > 1]}"
        )


# =============================================================================
# action_date の日付形式バリデーション
# =============================================================================
class TestCorporateActionsDate:
    """action_date の日付バリデーションテスト。"""

    def test_正常系_全action_dateがISO8601形式である(
        self, actions_list: list[dict[str, Any]]
    ) -> None:
        """全 action_date が date.fromisoformat() で変換可能であることを確認。"""
        for action in actions_list:
            ticker = action["ticker"]
            action_date_str = action["action_date"]
            try:
                parsed = date.fromisoformat(action_date_str)
            except ValueError:
                pytest.fail(
                    f"ticker={ticker}: action_date='{action_date_str}' is not valid ISO 8601"
                )
            assert isinstance(parsed, date)

    def test_正常系_全action_dateがPORTFOLIO_DATE以降である(
        self, actions_list: list[dict[str, Any]]
    ) -> None:
        """全 action_date が PORTFOLIO_DATE (2015-12-31) 以降であることを確認。"""
        for action in actions_list:
            ticker = action["ticker"]
            action_date = date.fromisoformat(action["action_date"])
            assert action_date >= _PORTFOLIO_DATE, (
                f"ticker={ticker}: action_date={action_date} is before "
                f"PORTFOLIO_DATE={_PORTFOLIO_DATE}"
            )

    @pytest.mark.parametrize(
        ("ticker", "expected_date"),
        [
            ("ALTR", "2015-12-31"),
            ("ARM", "2016-09-05"),
            ("EMC", "2016-09-07"),
            ("MON", "2018-06-07"),
            ("CA", "2018-11-05"),
            ("LIN", "2018-10-31"),
            ("UTX", "2020-04-03"),
            ("S", "2020-04-01"),
        ],
    )
    def test_正常系_各銘柄のaction_dateが正しい(
        self,
        actions_list: list[dict[str, Any]],
        ticker: str,
        expected_date: str,
    ) -> None:
        """各銘柄の action_date が期待値と一致することを確認。"""
        action = next(a for a in actions_list if a["ticker"] == ticker)

        assert action["action_date"] == expected_date


# =============================================================================
# action_type の許可値バリデーション
# =============================================================================
class TestCorporateActionsType:
    """action_type のバリデーションテスト。"""

    def test_正常系_全action_typeが許可値のみである(
        self, actions_list: list[dict[str, Any]]
    ) -> None:
        """全 action_type が 'delisting' または 'merger' のいずれかであることを確認。"""
        for action in actions_list:
            ticker = action["ticker"]
            action_type = action["action_type"]
            assert action_type in _ALLOWED_ACTION_TYPES, (
                f"ticker={ticker}: action_type='{action_type}' is not in "
                f"{_ALLOWED_ACTION_TYPES}"
            )

    def test_正常系_delistingとmergerの両方が使用されている(
        self, actions_list: list[dict[str, Any]]
    ) -> None:
        """delisting と merger の両方のタイプが存在することを確認。"""
        actual_types = {a["action_type"] for a in actions_list}

        assert actual_types == _ALLOWED_ACTION_TYPES


# =============================================================================
# メタデータのバリデーション
# =============================================================================
class TestCorporateActionsMetadata:
    """_metadata のバリデーションテスト。"""

    def test_正常系_metadataが存在する(
        self, corporate_actions_data: dict[str, Any]
    ) -> None:
        """_metadata キーが存在することを確認。"""
        assert "_metadata" in corporate_actions_data

    def test_正常系_total_actionsがエントリ数と一致する(
        self,
        corporate_actions_data: dict[str, Any],
        actions_list: list[dict[str, Any]],
    ) -> None:
        """_metadata.total_actions が実際のエントリ数と一致することを確認。"""
        expected = corporate_actions_data["_metadata"]["total_actions"]

        assert expected == len(actions_list)
