"""SCI / SRI / i-SSP ローダーの単体テスト."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from digital_twin.data.loader import load_issp_logs, load_sci_panel, load_sri_sales
from digital_twin.data.schema import (
    DigitalJourney,
    MonthlyPurchaseRecord,
    StoreSalesRecord,
    WebActionType,
    WebBehaviorLog,
)


@pytest.fixture()
def sci_csv(tmp_path: Path) -> Path:
    """SCI パネルのダミー CSV を作成する."""
    p = tmp_path / "sci_panel.csv"
    with p.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "consumer_id", "month", "category", "brand",
                "is_new_purchase", "is_repeat_purchase", "quantity", "amount_yen",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "consumer_id": "C001",
            "month": "2025-01",
            "category": "サプリ",
            "brand": "ヤクルト1000",
            "is_new_purchase": "true",
            "is_repeat_purchase": "false",
            "quantity": "2",
            "amount_yen": "600",
        })
        writer.writerow({
            "consumer_id": "C001",
            "month": "2025-02",
            "category": "サプリ",
            "brand": "ヤクルト1000",
            "is_new_purchase": "false",
            "is_repeat_purchase": "true",
            "quantity": "3",
            "amount_yen": "900",
        })
    return p


@pytest.fixture()
def sri_csv(tmp_path: Path) -> Path:
    """SRI 店舗POS のダミー CSV を作成する."""
    p = tmp_path / "sri_sales.csv"
    with p.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "region", "channel", "category", "brand",
                "month", "sales_volume", "sales_amount_yen", "purchase_rate",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "region": "kanto",
            "channel": "ドラッグストア",
            "category": "サプリ",
            "brand": "ヤクルト1000",
            "month": "2025-01",
            "sales_volume": "15000",
            "sales_amount_yen": "4500000",
            "purchase_rate": "0.12",
        })
    return p


@pytest.fixture()
def issp_csv(tmp_path: Path) -> Path:
    """i-SSP ウェブ行動ログのダミー CSV を作成する."""
    p = tmp_path / "issp_logs.csv"
    with p.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "consumer_id", "timestamp", "action_type",
                "url", "domain", "page_title", "duration_seconds",
                "search_keyword", "ad_campaign_id",
                "related_brand", "related_category",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "consumer_id": "C001",
            "timestamp": "2025-01-15T10:30:00",
            "action_type": "search",
            "url": "",
            "domain": "google.com",
            "page_title": "",
            "duration_seconds": "0",
            "search_keyword": "睡眠 サプリ おすすめ",
            "ad_campaign_id": "",
            "related_brand": "",
            "related_category": "サプリ",
        })
        writer.writerow({
            "consumer_id": "C001",
            "timestamp": "2025-01-15T10:31:00",
            "action_type": "page_view",
            "url": "https://example.com/review/yakult1000",
            "domain": "example.com",
            "page_title": "ヤクルト1000 口コミ",
            "duration_seconds": "120",
            "search_keyword": "",
            "ad_campaign_id": "",
            "related_brand": "ヤクルト1000",
            "related_category": "サプリ",
        })
        writer.writerow({
            "consumer_id": "C001",
            "timestamp": "2025-01-15T10:35:00",
            "action_type": "ad_click",
            "url": "https://ad.example.com/yakult",
            "domain": "ad.example.com",
            "page_title": "",
            "duration_seconds": "5",
            "search_keyword": "",
            "ad_campaign_id": "CAMP-001",
            "related_brand": "ヤクルト1000",
            "related_category": "サプリ",
        })
    return p


class TestLoadSciPanel:
    def test_loads_records(self, sci_csv: Path) -> None:
        records = load_sci_panel(sci_csv)
        assert len(records) == 2
        assert all(isinstance(r, MonthlyPurchaseRecord) for r in records)

    def test_first_record_fields(self, sci_csv: Path) -> None:
        rec = load_sci_panel(sci_csv)[0]
        assert rec.consumer_id == "C001"
        assert rec.month == "2025-01"
        assert rec.category == "サプリ"
        assert rec.brand == "ヤクルト1000"
        assert rec.is_new_purchase is True
        assert rec.is_repeat_purchase is False
        assert rec.quantity == 2
        assert rec.amount_yen == 600

    def test_repeat_record(self, sci_csv: Path) -> None:
        rec = load_sci_panel(sci_csv)[1]
        assert rec.is_new_purchase is False
        assert rec.is_repeat_purchase is True


class TestLoadSriSales:
    def test_loads_records(self, sri_csv: Path) -> None:
        records = load_sri_sales(sri_csv)
        assert len(records) == 1
        assert isinstance(records[0], StoreSalesRecord)

    def test_fields(self, sri_csv: Path) -> None:
        rec = load_sri_sales(sri_csv)[0]
        assert rec.region == "kanto"
        assert rec.channel == "ドラッグストア"
        assert rec.category == "サプリ"
        assert rec.brand == "ヤクルト1000"
        assert rec.month == "2025-01"
        assert rec.sales_volume == 15000
        assert rec.sales_amount_yen == 4500000
        assert rec.purchase_rate == pytest.approx(0.12)


class TestLoadIsspLogs:
    def test_loads_records(self, issp_csv: Path) -> None:
        logs = load_issp_logs(issp_csv)
        assert len(logs) == 3
        assert all(isinstance(log, WebBehaviorLog) for log in logs)

    def test_search_log(self, issp_csv: Path) -> None:
        log = load_issp_logs(issp_csv)[0]
        assert log.consumer_id == "C001"
        assert log.action_type == WebActionType.SEARCH
        assert log.search_keyword == "睡眠 サプリ おすすめ"
        assert log.domain == "google.com"

    def test_page_view_log(self, issp_csv: Path) -> None:
        log = load_issp_logs(issp_csv)[1]
        assert log.action_type == WebActionType.PAGE_VIEW
        assert log.related_brand == "ヤクルト1000"
        assert log.duration_seconds == 120

    def test_ad_click_log(self, issp_csv: Path) -> None:
        log = load_issp_logs(issp_csv)[2]
        assert log.action_type == WebActionType.AD_CLICK
        assert log.ad_campaign_id == "CAMP-001"


class TestDigitalJourney:
    def test_create_journey_from_logs(self, issp_csv: Path) -> None:
        """ログから DigitalJourney を組み立てられることを確認."""
        logs = load_issp_logs(issp_csv)
        journey = DigitalJourney(
            consumer_id="C001",
            session_id="S001",
            session_date="2025-01-15",
            logs=logs,
            resulted_in_purchase=False,
        )
        assert journey.consumer_id == "C001"
        assert len(journey.logs) == 3
        assert journey.resulted_in_purchase is False

    def test_journey_with_purchase(self) -> None:
        journey = DigitalJourney(
            consumer_id="C002",
            session_id="S002",
            session_date="2025-02-01",
            resulted_in_purchase=True,
            purchased_brand="ヤクルト1000",
        )
        assert journey.resulted_in_purchase is True
        assert journey.purchased_brand == "ヤクルト1000"
