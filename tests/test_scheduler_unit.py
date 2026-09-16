"""
Unit tests for Scheduler fuzzy subject matching and date helpers.
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scheduler.jobs import match_subject


def test_subject_fuzzy_matching():
    # Direct match
    assert match_subject("История России", "История России")
    # Substring / variant match
    assert match_subject("Физика", "Физика 1")
    assert match_subject("Философия", "ФИЛОСОФИЯ_3 раздела_зачет")
    assert match_subject("Введение в профессиональную деятельность", "Введение в профессиональную деятельность")
    assert match_subject("Инженерная графика / Компьютерная графика", "Инженерная графика - машиностроение")

    # Negative matches
    assert not match_subject("История России", "Физика 1")
    assert not match_subject("Философия", "Информатика")


if __name__ == "__main__":
    test_subject_fuzzy_matching()
    print("Scheduler unit tests passed successfully!")
