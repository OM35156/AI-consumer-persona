"""loader.py の単体テスト."""

from __future__ import annotations

import json
from pathlib import Path

from digital_twin.data.loader import load_consumers, load_dataset, split_holdout
from digital_twin.data.schema import (
    AgeGroup,
    CategoryProfile,
    Consumer,
    ConsumerDemographics,
    Gender,
    Region,
)


def _make_consumers(n: int) -> list[Consumer]:
    return [
        Consumer(
            consumer_id=f"C{i:03d}",
            demographics=ConsumerDemographics(
                age_group=AgeGroup.AGE_35_44,
                gender=Gender.FEMALE if i % 2 == 0 else Gender.MALE,
                region=Region.KANTO,
            ),
            category_profile=CategoryProfile(category="スキンケア"),
        )
        for i in range(n)
    ]


class TestLoadConsumers:
    def test_load_from_json(self, tmp_path: Path) -> None:
        consumers = _make_consumers(3)
        p = tmp_path / "consumers.json"
        p.write_text(
            json.dumps([c.model_dump(mode="json") for c in consumers], ensure_ascii=False),
            encoding="utf-8",
        )
        loaded = load_consumers(p)
        assert len(loaded) == 3
        assert all(isinstance(c, Consumer) for c in loaded)
        assert loaded[0].consumer_id == "C000"


class TestLoadDataset:
    def test_load_consumers_only(self, tmp_path: Path) -> None:
        consumers = _make_consumers(2)
        (tmp_path / "consumers.json").write_text(
            json.dumps([c.model_dump(mode="json") for c in consumers], ensure_ascii=False),
            encoding="utf-8",
        )
        c, s, sc = load_dataset(tmp_path)
        assert len(c) == 2
        assert s == []
        assert sc == []


class TestSplitHoldout:
    def test_split_ratio(self) -> None:
        consumers = _make_consumers(10)
        train, holdout = split_holdout(consumers, holdout_ratio=0.3, seed=0)
        assert len(train) == 7
        assert len(holdout) == 3

    def test_split_deterministic(self) -> None:
        consumers = _make_consumers(10)
        t1, h1 = split_holdout(consumers, seed=42)
        t2, h2 = split_holdout(consumers, seed=42)
        assert [c.consumer_id for c in t1] == [c.consumer_id for c in t2]
        assert [c.consumer_id for c in h1] == [c.consumer_id for c in h2]
