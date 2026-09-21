"""
Unit tests for Kapipara API client (services/para_api.py).
Verifies:
1. Kapipara JSON grid parsing and normalization
2. Lesson change / transfer detection (is_changed flag)
3. Transparent fallback to KaiApiClient when Kapipara fails
4. Day and week schedule filtering and deduplication
"""

import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.kai_api import KaiApiClient, Lesson
from services.para_api import (
    KapiparaApiError,
    KapiparaClient,
    is_kapipara_change,
)


@pytest.fixture
def real_kapipara_data():
    file_path = Path(__file__).resolve().parent.parent / "data" / "real_kapipara_5108.json"
    assert file_path.exists(), f"File {file_path} must exist"
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_is_kapipara_change_detection():
    # 1. Single isolated date (e.g. transfer on 28.12)
    item_transfer = {
        "disciplname": "Основы российской государственности",
        "daytime": "09:40",
        "daydate": "28.12",
        "auditory": "505",
    }
    assert is_kapipara_change(item_transfer) is True

    # 2. Regular semester recurring dates (bi-weekly)
    item_regular = {
        "disciplname": "История России",
        "daytime": "09:40",
        "daydate": "07.09 21.09 05.10 19.10 02.11 16.11 30.11 14.12",
        "auditory": "505",
    }
    assert is_kapipara_change(item_regular) is False

    # 3. Explicit status or boolean flag
    assert is_kapipara_change({"disciplname": "Математика", "is_changed": True}) is True
    assert is_kapipara_change({"disciplname": "Математика", "status": "transfer"}) is True
    assert is_kapipara_change({"disciplname": "Математика", "status": "замена"}) is True

    # 4. Textual replacement keyword in name or type
    assert is_kapipara_change({"disciplname": "Философия (Замена)", "daydate": "01.09 08.09"}) is True
    assert is_kapipara_change({"disciplname": "Физика", "discipltype": "перенос", "daydate": ""}) is True


def test_kapipara_parse_schedule_grid(real_kapipara_data):
    raw_schedule = real_kapipara_data["result"]["schedule"]
    assert len(raw_schedule) == 35

    grid = KapiparaClient.parse_schedule_grid(raw_schedule)
    assert set(grid.keys()) == {"1", "2", "3", "4", "5", "6"}
    total_in_grid = sum(len(items) for items in grid.values())
    assert total_in_grid == 35

    # Day 1 has 8 lessons
    assert len(grid["1"]) == 8

    # Check that changed items on Day 1 have is_changed=True
    changed_day1 = [item for item in grid["1"] if item.get("is_changed")]
    assert len(changed_day1) == 2
    for item in changed_day1:
        assert item["daydate"] == "28.12"
        assert item["auditory"] == "505"


def test_kapipara_mapping_to_lesson_model(real_kapipara_data):
    raw_schedule = real_kapipara_data["result"]["schedule"]
    lessons = [Lesson.from_raw_dict(item) for item in raw_schedule]

    assert len(lessons) == 35
    changed_lessons = [l for l in lessons if l.is_changed]
    assert len(changed_lessons) == 2

    for l in changed_lessons:
        assert l.day_date == "28.12"
        assert l.aud_num == "505"
        assert l.day_num == 1


def test_kapipara_day_and_week_filtering(real_kapipara_data):
    raw_schedule = real_kapipara_data["result"]["schedule"]
    grid = KapiparaClient.parse_schedule_grid(raw_schedule)
    client = KapiparaClient()

    # Target: Monday 2026-09-14 (even week)
    target_monday = date(2026, 9, 14)
    monday_lessons = client.get_lessons_for_day(
        grid,
        target_date=target_monday,
        subgroup=2,
        strict_date=True,
        deduplicate=True,
    )

    assert len(monday_lessons) > 0
    disc_names = [l.discipl_name for l in monday_lessons]
    assert "Высшая математика" in disc_names
    assert "Основы российской государственности" in disc_names

    # Check week schedule returns all days Monday to Saturday
    week_sched = client.get_week_schedule(
        grid,
        target_monday=target_monday,
        subgroup=2,
        strict_date=True,
        deduplicate=True,
    )
    assert len(week_sched) == 6


def test_kapipara_fallback_to_kai_api():
    mock_kai_client = MagicMock(spec=KaiApiClient)
    mock_kai_client.search_group_id.return_value = "9999"
    mock_kai_client.get_schedule.return_value = {
        "1": [{"disciplName": "Тест KAI", "dayNum": "1", "dayTime": "08:00"}]
    }

    client = KapiparaClient(fallback_kai_client=mock_kai_client)

    # Simulate Kapipara failure
    with patch.object(client, "get_schedule_raw", side_effect=KapiparaApiError("Connection failed")):
        grid = client.get_schedule_grid("5108", fallback_on_error=True)
        assert "1" in grid
        assert grid["1"][0]["disciplName"] == "Тест KAI"
        mock_kai_client.search_group_id.assert_called_once_with("5108")
        mock_kai_client.get_schedule.assert_called_once_with("9999")
