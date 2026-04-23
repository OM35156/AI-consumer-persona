"""toitta インタビューデータカード生成の単体テスト."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from digital_twin.data.data_card import generate_toitta_card, process_toitta_interviews

HEADER = [
    "切片",
    "プロジェクトID",
    "プロジェクト名",
    "インタビュータイトル",
    "インタビューID",
    "切片ID",
    "切片リンク",
    "グループ名(JSON)",
    "お気に入り？",
]


def _write_csv(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(HEADER)
        for row in rows:
            writer.writerow(row)


class TestGenerateToittaCard:
    def test_basic_card(self) -> None:
        card = generate_toitta_card(
            topic="睡眠時間を一定に保ちたい",
            slices=["6時間は寝たい", "規則正しい生活をしている"],
            n_interviewees=2,
        )
        assert "トピック: 睡眠時間を一定に保ちたい" in card.text
        assert "対象者数: 2名" in card.text
        assert "発言数: 2件" in card.text
        assert "6時間は寝たい" in card.text
        assert card.metadata["source"] == "toitta"
        assert card.metadata["topic"] == "睡眠時間を一定に保ちたい"
        assert card.metadata["domain"] == "sleep"
        assert card.metadata["n_interviewees"] == 2
        assert card.metadata["sample_n"] == 2

    def test_no_pii_in_metadata(self) -> None:
        card = generate_toitta_card(topic="テスト", slices=["発言"], n_interviewees=1)
        for key in ("切片リンク", "切片ID", "インタビューID", "link", "interview_id"):
            assert key not in card.metadata


class TestProcessToittaInterviews:
    def test_topic_grouping(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "睡眠対策インタビュー①.csv"
        _write_csv(csv_path, [
            ["朝6時に起きる", "P1", "PJ", "インタビュー①", "I1", "S1", "http://x", '["規則正しい生活"]', "false"],
            ["夜は12時に寝る", "P1", "PJ", "インタビュー①", "I1", "S2", "http://x", '["規則正しい生活"]', "false"],
            ["ヤクルトを飲む", "P1", "PJ", "インタビュー①", "I1", "S3", "http://x", '["ドリンク試行"]', "false"],
        ])

        output = tmp_path / "out.jsonl"
        cards = process_toitta_interviews(tmp_path, output, glob_pattern="*.csv")

        assert len(cards) == 2
        topics = {c.metadata["topic"] for c in cards}
        assert topics == {"規則正しい生活", "ドリンク試行"}

        # 規則正しい生活 のカードに2スライス
        regular_card = next(c for c in cards if c.metadata["topic"] == "規則正しい生活")
        assert regular_card.metadata["sample_n"] == 2

    def test_multi_tag_slice_duplicated(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "睡眠対策インタビュー①.csv"
        _write_csv(csv_path, [
            ["マルチタグ発言", "P1", "PJ", "インタビュー①", "I1", "S1", "http://x", '["トピックA", "トピックB"]', "false"],
        ])

        output = tmp_path / "out.jsonl"
        cards = process_toitta_interviews(tmp_path, output, glob_pattern="*.csv")

        assert len(cards) == 2
        for card in cards:
            assert "マルチタグ発言" in card.text

    def test_empty_group_becomes_unclassified(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "睡眠対策インタビュー①.csv"
        _write_csv(csv_path, [
            ["未分類の発言", "P1", "PJ", "インタビュー①", "I1", "S1", "http://x", "[]", "false"],
        ])

        output = tmp_path / "out.jsonl"
        cards = process_toitta_interviews(tmp_path, output, glob_pattern="*.csv")

        assert len(cards) == 1
        assert cards[0].metadata["topic"] == "未分類"
        assert "未分類の発言" in cards[0].text

    def test_multiple_interviewees_counted(self, tmp_path: Path) -> None:
        for i, name in enumerate(["①", "②"]):
            csv_path = tmp_path / f"睡眠対策インタビュー{name}.csv"
            _write_csv(csv_path, [
                [f"発言{i}", "P1", "PJ", f"インタビュー{name}", f"I{i}", f"S{i}", "http://x", '["共通トピック"]', "false"],
            ])

        output = tmp_path / "out.jsonl"
        cards = process_toitta_interviews(tmp_path, output, glob_pattern="*.csv")

        assert len(cards) == 1
        assert cards[0].metadata["n_interviewees"] == 2
        assert cards[0].metadata["sample_n"] == 2

    def test_jsonl_output_valid(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "睡眠対策インタビュー①.csv"
        _write_csv(csv_path, [
            ["発言A", "P1", "PJ", "インタビュー①", "I1", "S1", "http://x", '["テスト"]', "false"],
        ])

        output = tmp_path / "out.jsonl"
        process_toitta_interviews(tmp_path, output, glob_pattern="*.csv")

        lines = output.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert "text" in data
        assert "metadata" in data
        assert data["metadata"]["source"] == "toitta"

    def test_no_csv_returns_empty(self, tmp_path: Path) -> None:
        output = tmp_path / "out.jsonl"
        cards = process_toitta_interviews(tmp_path, output, glob_pattern="*.csv")
        assert cards == []

    def test_no_pii_in_output(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "睡眠対策インタビュー①.csv"
        _write_csv(csv_path, [
            ["発言", "P1", "PJ", "インタビュー①", "I1", "S1", "http://secret-link.com", '["トピック"]', "false"],
        ])

        output = tmp_path / "out.jsonl"
        process_toitta_interviews(tmp_path, output, glob_pattern="*.csv")

        content = output.read_text(encoding="utf-8")
        assert "secret-link.com" not in content
        assert "I1" not in content or "インタビュー" in content  # インタビュー① is OK as topic context
