"""anonymizer.py の単体テスト."""

from __future__ import annotations

from digital_twin.data.anonymizer import (
    _demographic_key,
    anonymize_dataset,
    check_k_anonymity,
    enforce_k_anonymity,
    strip_pii,
)
from digital_twin.data.schema import (
    AgeGroup,
    CategoryProfile,
    Consumer,
    ConsumerDemographics,
    Gender,
    LifeStage,
    Region,
)


def _make(n: int, region: Region = Region.KANTO) -> list[Consumer]:
    return [
        Consumer(
            consumer_id=f"C{i:03d}",
            demographics=ConsumerDemographics(
                age_group=AgeGroup.AGE_35_44,
                gender=Gender.FEMALE,
                region=region,
                life_stage=LifeStage.MARRIED_WITH_CHILDREN,
            ),
            category_profile=CategoryProfile(category="X"),
        )
        for i in range(n)
    ]


class TestDemographicKey:
    def test_returns_quasi_identifier(self) -> None:
        c = _make(1)[0]
        key = _demographic_key(c)
        assert key == ("35-44", "female", "kanto", "married_with_children")


class TestCheckKAnonymity:
    def test_uniform_group(self) -> None:
        report = check_k_anonymity(_make(10), k=5)
        assert report.total_consumers == 10
        assert report.k_anonymity_achieved == 10
        assert report.suppressed_consumers == 0
        assert report.warnings == []

    def test_detects_violation(self) -> None:
        report = check_k_anonymity(_make(2), k=5)
        assert report.k_anonymity_achieved == 2
        assert len(report.warnings) >= 1


class TestEnforceKAnonymity:
    def test_suppresses_small_group(self) -> None:
        big = _make(6, region=Region.KANTO)
        small = _make(2, region=Region.HOKKAIDO)
        safe, report = enforce_k_anonymity(big + small, k=5)
        assert len(safe) == 6
        assert report.suppressed_consumers == 2


class TestStripPii:
    def test_replaces_consumer_id(self) -> None:
        c = _make(1)[0]
        anon = strip_pii(c)
        assert anon.consumer_id != c.consumer_id
        assert anon.consumer_id.startswith("ANON_")
        # 他フィールドは維持
        assert anon.demographics == c.demographics


class TestAnonymizeDataset:
    def test_integrated_flow(self) -> None:
        big = _make(5, region=Region.KANTO)
        small = _make(2, region=Region.HOKKAIDO)
        safe, report = anonymize_dataset(big + small, k=5)
        assert len(safe) == 5
        assert all(c.consumer_id.startswith("ANON_") for c in safe)
        assert report.suppressed_consumers == 2
