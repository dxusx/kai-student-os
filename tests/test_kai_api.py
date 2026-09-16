"""
Unit tests for KAI API module.
Verifies subgroup filtering logic across real fields, week parity calculation, and schedule parsing.
"""

import json
import sys
from pathlib import Path

# Add project root to python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date
from services.kai_api import Lesson, get_week_parity, is_even_week, KaiApiClient


def test_week_parity():
    # 2026-09-11 is Friday of ISO week 37 -> odd ("нечет")
    d1 = date(2026, 9, 11)
    assert get_week_parity(d1) == "нечет"
    assert not is_even_week(d1)

    # 2026-09-18 is Friday of ISO week 38 -> even ("чет")
    d2 = date(2026, 9, 18)
    assert get_week_parity(d2) == "чет"
    assert is_even_week(d2)


def test_lesson_subgroup_filtering():
    # 1. Lesson strictly for subgroup 1 via potok
    l_sg1 = Lesson(
        discipl_name="Лабораторная 1",
        day_num=1,
        day_time="08:00",
        potok="1 подгр."
    )
    assert not l_sg1.is_for_subgroup(2)
    assert l_sg1.is_for_subgroup(1)

    # 2. Lesson strictly for subgroup 2 via potok
    l_sg2 = Lesson(
        discipl_name="Лабораторная 2",
        day_num=1,
        day_time="08:00",
        potok="2 подгр."
    )
    assert l_sg2.is_for_subgroup(2)
    assert not l_sg2.is_for_subgroup(1)

    # 3. Common stream lecture (no subgroup marker)
    l_common = Lesson(
        discipl_name="Высшая математика",
        day_num=1,
        day_time="08:00",
        potok=""
    )
    assert l_common.is_for_subgroup(2)
    assert l_common.is_for_subgroup(1)

    # 4. Marker embedded in discipline name: "Физика (1 п/г)"
    l_embed_sg1 = Lesson(
        discipl_name="Физика (1 п/г)",
        day_num=1,
        day_time="08:00",
        potok=""
    )
    assert not l_embed_sg1.is_for_subgroup(2)
    assert l_embed_sg1.is_for_subgroup(1)

    # 5. Marker embedded in discipline name: "Физика (2 п/г)"
    l_embed_sg2 = Lesson(
        discipl_name="Физика (2 п/г)",
        day_num=1,
        day_time="08:00",
        potok=""
    )
    assert l_embed_sg2.is_for_subgroup(2)
    assert not l_embed_sg2.is_for_subgroup(1)

    # 6. Marker with (1) and (2)
    l_paren_1 = Lesson(
        discipl_name="Компьютерные сети (1)",
        day_num=1,
        day_time="08:00"
    )
    assert not l_paren_1.is_for_subgroup(2)
    assert l_paren_1.is_for_subgroup(1)

    l_paren_2 = Lesson(
        discipl_name="Компьютерные сети (2)",
        day_num=1,
        day_time="08:00"
    )
    assert l_paren_2.is_for_subgroup(2)
    assert not l_paren_2.is_for_subgroup(1)

    # 7. Marker in audNum
    l_aud_sg1 = Lesson(
        discipl_name="Английский язык",
        aud_num="441 (1 подгр)",
        day_num=1,
        day_time="08:00"
    )
    assert not l_aud_sg1.is_for_subgroup(2)

    # 8. Lecture hall "ЛЗ №1" must NOT trigger subgroup 1!
    l_lz1 = Lesson(
        discipl_name="Высшая математика",
        aud_num="ЛЗ №1",
        build_num="2",
        day_num=1,
        day_time="11:20"
    )
    assert l_lz1.is_for_subgroup(2)
    assert l_lz1.is_for_subgroup(1)


def test_real_schedule_parsing():
    json_path = Path(__file__).resolve().parent.parent / "real_schedule_5108.json"
    assert json_path.exists(), "real_schedule_5108.json must exist in project root"

    with open(json_path, "r", encoding="utf-8") as f:
        real_schedule = json.load(f)

    client = KaiApiClient()
    # Monday 2026-09-14
    target_date = date(2026, 9, 14)
    lessons = client.get_lessons_for_day(real_schedule, target_date=target_date, subgroup=2, strict_date=True)

    assert len(lessons) > 0, "Should have lessons for Monday 14.09.2026"
    disciplines = [l.discipl_name for l in lessons]
    assert "Высшая математика" in disciplines


def test_deduplication_physics_tuesday():
    json_path = Path(__file__).resolve().parent.parent / "real_schedule_5108.json"
    with open(json_path, "r", encoding="utf-8") as f:
        real_schedule = json.load(f)

    client = KaiApiClient()
    # Tuesday 2026-09-15
    tuesday = date(2026, 9, 15)
    lessons = client.get_lessons_for_day(real_schedule, target_date=tuesday, subgroup=2, strict_date=True, deduplicate=True)

    times = [l.day_time for l in lessons]
    assert times.count("11:20") == 1, f"Expected exactly 1 lesson at 11:20, got {times.count('11:20')}"

    l_1120 = next(l for l in lessons if l.day_time == "11:20")
    assert "Шарипова" in l_1120.prepod_name and "Фархутдинова" in l_1120.prepod_name
    assert " / " in l_1120.prepod_name


def test_deduplication_graphics_wednesday():
    json_path = Path(__file__).resolve().parent.parent / "real_schedule_5108.json"
    with open(json_path, "r", encoding="utf-8") as f:
        real_schedule = json.load(f)

    client = KaiApiClient()
    # Wednesday 2026-09-16
    wednesday = date(2026, 9, 16)
    lessons = client.get_lessons_for_day(real_schedule, target_date=wednesday, subgroup=2, strict_date=True, deduplicate=True)

    times = [l.day_time for l in lessons]
    assert times.count("09:40") == 1
    assert times.count("11:20") == 1

    for time_slot in ["09:40", "11:20"]:
        l = next(l for l in lessons if l.day_time == time_slot)
        assert "210 (Инженерная) / 227 (Компьютерная)" in l.aud_num


if __name__ == "__main__":
    test_week_parity()
    test_lesson_subgroup_filtering()
    test_real_schedule_parsing()
    test_deduplication_physics_tuesday()
    test_deduplication_graphics_wednesday()
    print("All unit tests in test_kai_api.py passed successfully!")

