"""Unit tests for market.nse.analysis.owner_classification module.

NSE の株主構成集計値から owner_flag を導出する ``classify_owner_flag`` の
テストスイート。

判定軸は原則として株主数 (``*_num``) である。保有比率は小数第2位で丸められる
ため、持株会社経由で支配する一族が個人名義で名目的な株数のみ保有する場合に
0.00% となり、比率ベースでは「自然人 promoter 不在」と誤読される
（実例: INOXGREEN は自然人3名で計500株、発行済4.01億株に対し hufi_pct=0.00%）。

Test TODO List:
- [x] Tier 4: promoter 総保有が閾値未満 → excluded_low_promoter
- [x] Tier 4: 政府保有が閾値以上 → excluded_state_dominant
- [x] Tier 4: 除外判定は Tier 1 より優先される
- [x] Tier 1: 自然人 + 役員 → individual_and_director
- [x] Tier 1: hufi_pct が丸めで0でも株主数があれば individual_and_director
- [x] Tier 1: 自然人のみ → individual
- [x] Tier 1: 自然人なし + 役員のみ → director_only
- [x] Tier 1: nri がいる場合は director_only にしない
- [x] Tier 3: 外資優勢 → ambiguous_mnc_jv_candidate
- [x] Tier 3: 自然人の保有が微少 → ambiguous_minor_individual
- [x] Tier 2: 海外個人のみ → probable_nri_family
- [x] Tier 2: 親族・信託のみ → probable_relatives_trust
- [x] Tier 3: 自然人不在 + 国内法人保有 → ambiguous_holding_indian
- [x] Tier 3: 自然人不在 + 外国法人保有 → ambiguous_holding_foreign
- [x] 該当なし → excluded_no_natural_no_holding
- [x] derive_owner_flag_final(): owner_confirmed_* / owner_probable_* → OWNER
- [x] derive_owner_flag_final(): excluded_* → NOT_OWNER
- [x] derive_owner_flag_final(): ambiguous_* → OWNER_WEAK
- [x] compute_govt_pct(): 内訳と合計行の二重計上を防ぐ
- [x] compute_govt_pct(): 一方のみ開示のケース
- [x] 集計定数: OtherForeignShareholders を外資に含む
- [x] 集計定数: 政府系の内訳と合計を分離
"""

from typing import TypedDict, Unpack

import pytest

from market.nse.analysis.owner_classification import (
    FOREIGN_NON_GOVT_SUBS,
    GOVT_COMPONENT_SUBS,
    GOVT_ROLLUP_SUBS,
    classify_owner_flag,
    compute_govt_pct,
    derive_owner_flag_final,
)


class _Composition(TypedDict):
    """``classify_owner_flag`` の全キーワード引数。

    株主数 (``*_num``) は集計時に ``int()`` へ丸めた実数値であり
    (``notebook/NSE/scripts/persist_and_classify.py`` 参照)、保有比率
    (``*_pct``) は float である。両者を ``dict[str, float]`` に潰すと
    株主数の型が実装と食い違うため、TypedDict でキーごとに型を保持する。
    """

    promoter_total_pct: float
    hufi_num: int
    hufi_pct: float
    nri_num: int
    dir_num: int
    kmp_num: int
    rel_num: int
    trust_num: int
    natural_num_sum: int
    govt_pct: float
    other_indian_pct: float
    other_foreign_pct: float
    foreign_non_govt_pct: float


class _CompositionOverrides(TypedDict, total=False):
    """:class:`_Composition` の部分指定版（``_composition`` の kwargs 用）。"""

    promoter_total_pct: float
    hufi_num: int
    hufi_pct: float
    nri_num: int
    dir_num: int
    kmp_num: int
    rel_num: int
    trust_num: int
    natural_num_sum: int
    govt_pct: float
    other_indian_pct: float
    other_foreign_pct: float
    foreign_non_govt_pct: float


def _composition(**overrides: Unpack[_CompositionOverrides]) -> _Composition:
    """promoter 50% のみを持つベース構成に overrides を適用して返す。"""
    base: _Composition = {
        "promoter_total_pct": 50.0,
        "hufi_num": 0,
        "hufi_pct": 0.0,
        "nri_num": 0,
        "dir_num": 0,
        "kmp_num": 0,
        "rel_num": 0,
        "trust_num": 0,
        "natural_num_sum": 0,
        "govt_pct": 0.0,
        "other_indian_pct": 0.0,
        "other_foreign_pct": 0.0,
        "foreign_non_govt_pct": 0.0,
    }
    base.update(overrides)
    return base


class TestTier4Exclusions:
    """Tier 4（先行除外）のテスト。"""

    def test_正常系_promoter総保有が閾値未満なら除外(self) -> None:
        """promoter_total_pct < 10% なら excluded_low_promoter。"""
        result = classify_owner_flag(
            **_composition(promoter_total_pct=9.99, hufi_num=3, natural_num_sum=3)
        )

        assert result == "excluded_low_promoter"

    def test_エッジケース_promoter総保有が閾値ちょうどなら除外しない(self) -> None:
        """promoter_total_pct == 10% は除外対象外であること。"""
        result = classify_owner_flag(
            **_composition(promoter_total_pct=10.0, hufi_num=3, natural_num_sum=3)
        )

        assert result == "owner_confirmed_individual"

    def test_正常系_政府保有が閾値以上なら除外(self) -> None:
        """govt_pct >= 10% なら excluded_state_dominant。"""
        result = classify_owner_flag(**_composition(govt_pct=10.0))

        assert result == "excluded_state_dominant"

    def test_正常系_政府保有は自然人promoterより優先して除外される(self) -> None:
        """自然人 promoter がいても政府保有が閾値以上なら除外されること。"""
        result = classify_owner_flag(
            **_composition(hufi_num=5, natural_num_sum=5, govt_pct=51.0)
        )

        assert result == "excluded_state_dominant"


class TestTier1OwnerConfirmed:
    """Tier 1（オーナー確定）のテスト。"""

    def test_正常系_自然人と役員がいる場合はindividual_and_director(self) -> None:
        """hufi_num>=1 かつ dir/kmp>=1 なら individual_and_director。"""
        result = classify_owner_flag(
            **_composition(hufi_num=3, hufi_pct=25.0, dir_num=2, natural_num_sum=5)
        )

        assert result == "owner_confirmed_individual_and_director"

    def test_正常系_hufi_pctが丸めで0でも株主数があればindividual_and_director(
        self,
    ) -> None:
        """持株会社経由支配で hufi_pct=0.00 でも自然人の存在を認識すること。

        INOXGREEN の実データ（自然人3名・計500株、kmp 1名）を再現する。
        """
        result = classify_owner_flag(
            **_composition(
                promoter_total_pct=56.12,
                hufi_num=3,
                hufi_pct=0.0,
                kmp_num=1,
                natural_num_sum=4,
                other_indian_pct=56.12,
            )
        )

        assert result == "owner_confirmed_individual_and_director"

    def test_正常系_自然人のみならindividual(self) -> None:
        """dir/kmp がいない場合は individual。"""
        result = classify_owner_flag(
            **_composition(hufi_num=2, hufi_pct=45.0, natural_num_sum=2)
        )

        assert result == "owner_confirmed_individual"

    def test_正常系_自然人がおらず役員のみならdirector_only(self) -> None:
        """hufi_num==0 かつ nri_num==0 かつ dir/kmp>=1 なら director_only。"""
        result = classify_owner_flag(**_composition(kmp_num=1, natural_num_sum=1))

        assert result == "owner_confirmed_director_only"

    def test_エッジケース_nriがいる場合はdirector_onlyにしない(self) -> None:
        """nri_num>=1 のときは director_only ではなく probable_nri_family。"""
        result = classify_owner_flag(
            **_composition(nri_num=2, dir_num=1, natural_num_sum=3)
        )

        assert result == "owner_probable_nri_family"


class TestTier3Ambiguous:
    """Tier 3（判定保留）のテスト。"""

    def test_正常系_外資保有が過半なら_mnc_jv候補(self) -> None:
        """自然人がいても foreign_non_govt_pct>=50% なら MNC-JV 候補。"""
        result = classify_owner_flag(
            **_composition(hufi_num=2, natural_num_sum=2, foreign_non_govt_pct=50.0)
        )

        assert result == "ambiguous_mnc_jv_candidate"

    def test_正常系_自然人の保有が微少ならminor_individual(self) -> None:
        """外資優勢で Tier 1 を外れた微少個人保有は minor_individual。"""
        result = classify_owner_flag(
            **_composition(
                hufi_num=1,
                hufi_pct=0.2,
                natural_num_sum=1,
                foreign_non_govt_pct=60.0,
            )
        )

        # 外資ガードが先に効くため MNC-JV 候補が優先される
        assert result == "ambiguous_mnc_jv_candidate"

    def test_正常系_自然人不在で国内法人保有ならholding_indian(self) -> None:
        """natural_num_sum==0 かつ国内法人保有が閾値以上なら holding_indian。"""
        result = classify_owner_flag(**_composition(other_indian_pct=45.0))

        assert result == "ambiguous_holding_indian"

    def test_正常系_自然人不在で外国法人保有ならholding_foreign(self) -> None:
        """natural_num_sum==0 かつ外国法人保有が閾値以上なら holding_foreign。"""
        result = classify_owner_flag(**_composition(other_foreign_pct=45.0))

        assert result == "ambiguous_holding_foreign"


class TestTier2Probable:
    """Tier 2（オーナーの可能性あり）のテスト。"""

    def test_正常系_海外個人のみならprobable_nri_family(self) -> None:
        """nri_num>=1 かつ hufi_num==0 なら probable_nri_family。"""
        result = classify_owner_flag(**_composition(nri_num=2, natural_num_sum=2))

        assert result == "owner_probable_nri_family"

    def test_正常系_親族や信託のみならprobable_relatives_trust(self) -> None:
        """rel/trust のみが存在する場合は probable_relatives_trust。"""
        result = classify_owner_flag(**_composition(rel_num=3, natural_num_sum=3))

        assert result == "owner_probable_relatives_trust"


class TestFallback:
    """どの Tier にも該当しないケースのテスト。"""

    def test_エッジケース_自然人も法人保有もなければ除外(self) -> None:
        """promoter 保有はあるが内訳が追えない場合は no_natural_no_holding。"""
        result = classify_owner_flag(**_composition())

        assert result == "excluded_no_natural_no_holding"


class TestDeriveOwnerFlagFinal:
    """derive_owner_flag_final() 関数のテスト。"""

    @pytest.mark.parametrize(
        "flag",
        [
            "owner_confirmed_individual_and_director",
            "owner_confirmed_director_only",
            "owner_probable_nri_family",
        ],
    )
    def test_正常系_owner_confirmedとowner_probableはOWNER(self, flag: str) -> None:
        """owner_confirmed_* / owner_probable_* は OWNER に集約されること。"""
        assert derive_owner_flag_final(flag) == "OWNER"

    @pytest.mark.parametrize(
        "flag",
        [
            "excluded_state_dominant",
            "excluded_no_natural_no_holding",
            "excluded_low_promoter",
        ],
    )
    def test_正常系_excludedはNOT_OWNER(self, flag: str) -> None:
        """excluded_* は NOT_OWNER に集約されること。"""
        assert derive_owner_flag_final(flag) == "NOT_OWNER"

    @pytest.mark.parametrize(
        "flag",
        [
            "ambiguous_holding_indian",
            "ambiguous_mnc_jv_candidate",
            "ambiguous_minor_individual",
        ],
    )
    def test_正常系_ambiguousはOWNER_WEAK(self, flag: str) -> None:
        """ambiguous_* は OWNER_WEAK に集約されること。"""
        assert derive_owner_flag_final(flag) == "OWNER_WEAK"


class TestComputeGovtPct:
    """compute_govt_pct() 関数のテスト。

    XBRL は政府系保有を内訳と合計行の両方で開示することがあり、単純加算すると
    二重計上になる（実例: TORNTPOWER は StateGovernmentsOrGovernors 8.35% と
    その合計行 Governments 8.35% が併存し、加算すると 16.70% となって
    誤って state-dominant 判定される）。
    """

    def test_正常系_内訳と合計が併存する場合は二重計上しない(self) -> None:
        """同額の内訳と合計行が併存しても合算せず一方を返すこと。"""
        assert compute_govt_pct(8.35, 8.35) == 8.35

    def test_正常系_合計行のみの場合は合計行を採用(self) -> None:
        """内訳が開示されない銘柄では合計行の値を返すこと。"""
        assert compute_govt_pct(0.0, 5.65) == 5.65

    def test_正常系_内訳のみの場合は内訳を採用(self) -> None:
        """合計行が開示されない銘柄では内訳合計を返すこと。"""
        assert compute_govt_pct(51.0, 0.0) == 51.0

    def test_エッジケース_両方ゼロならゼロ(self) -> None:
        """政府系保有がない場合は 0 を返すこと。"""
        assert compute_govt_pct(0.0, 0.0) == 0.0

    def test_エッジケース_内訳が合計を上回る場合は内訳を採用(self) -> None:
        """開示の不整合で内訳が合計を超える場合は大きい方を採る（保守的）。"""
        assert compute_govt_pct(30.0, 12.0) == 30.0


class TestAggregationConstants:
    """集計対象 sub_category 定数のテスト。"""

    def test_正常系_外資判定にOtherForeignShareholdersを含む(self) -> None:
        """海外親会社の直接保有枠を外すと MNC を検出できないため必須。

        実例: GRINDWELL は Saint-Gobain 系2社が 51.33% を
        OtherForeignShareholders 枠で保有している。
        """
        assert "OtherForeignShareholders" in FOREIGN_NON_GOVT_SUBS

    def test_正常系_政府系の内訳と合計を別定数に分離している(self) -> None:
        """二重計上を防ぐため合計行は内訳と別に保持すること。"""
        assert set(GOVT_COMPONENT_SUBS) & set(GOVT_ROLLUP_SUBS) == set()
        assert "Governments" in GOVT_ROLLUP_SUBS
