"""
Verification Script for Student Group 5108 (IREF-TsT, Subgroup 2)
Checks all Blackboard courses, scraped assignments, and reference materials in SQLite.
"""

import asyncio
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from database.connection import async_session
from database.crud import get_subjects, get_tasks

# Blackboard launcher URLs for student Group 5108
BB_COURSES = [
    {
        "num": 1,
        "name": "Введение в профессиональную деятельность",
        "bb_id": "_10403_1",
        "url": "https://bb.kai.ru/webapps/blackboard/execute/launcher?type=Course&id=_10403_1&url=",
    },
    {
        "num": 2,
        "name": "Входное тестирование по иностранному языку 1 курс",
        "bb_id": "_17041_1",
        "url": "https://bb.kai.ru/webapps/blackboard/execute/launcher?type=Course&id=_17041_1&url=",
    },
    {
        "num": 3,
        "name": "Высшая математика 1.1",
        "bb_id": "_15511_1",
        "url": "https://bb.kai.ru/webapps/blackboard/execute/launcher?type=Course&id=_15511_1&url=",
    },
    {
        "num": 4,
        "name": "Высшая математика 1.2",
        "bb_id": "_15536_1",
        "url": "https://bb.kai.ru/webapps/blackboard/execute/launcher?type=Course&id=_15536_1&url=",
    },
    {
        "num": 5,
        "name": "Инженерная графика - ИРЭТ",
        "bb_id": "_10392_1",
        "url": "https://bb.kai.ru/webapps/blackboard/execute/launcher?type=Course&id=_10392_1&url=",
    },
    {
        "num": 6,
        "name": "Компьютерная графика",
        "bb_id": "_17086_1",
        "url": "https://bb.kai.ru/webapps/blackboard/execute/launcher?type=Course&id=_17086_1&url=",
    },
    {
        "num": 7,
        "name": "Основы российской государственности",
        "bb_id": "_17754_1",
        "url": "https://bb.kai.ru/webapps/blackboard/execute/launcher?type=Course&id=_17754_1&url=",
    },
    {
        "num": 8,
        "name": "ФИЛОСОФИЯ_3 раздела_зачет",
        "bb_id": "_18447_1",
        "url": "https://bb.kai.ru/webapps/blackboard/execute/launcher?type=Course&id=_18447_1&url=",
    },
    {
        "num": 9,
        "name": "Физика 1",
        "bb_id": "_9332_1",
        "url": "https://bb.kai.ru/webapps/blackboard/execute/launcher?type=Course&id=_9332_1&url=",
    },
]

REF_KEYWORDS = [
    "программ", "лекци", "фос", "методическ", "указани", "руководств",
    "инструкци", "бланк", "литератур", "конспект", "справочник", "введение",
    "история", "вопросы к", "титульн", "список", "план", "учебник", "пособие",
    "силлабус", "критери", "тема ", "презентац", "материал", "слайд"
]
ACT_KEYWORDS = [
    "лабораторн", "практическ", "задани", "отчет", "контрольн", "зачет",
    "аттестац", "проверочн", "тестирован", "тест", "доклад", "семестров",
    "курсов", "ргр", "дз", "экзамен", "коллоквиум", "расчет"
]


def is_ref(title: str) -> bool:
    t = title.lower()
    has_ref = any(k in t for k in REF_KEYWORDS)
    has_act = any(k in t for k in ACT_KEYWORDS)
    if has_ref and not has_act:
        return True
    if has_act and not has_ref:
        return False
    if "методическ" in t or "программ" in t:
        return True
    if has_act:
        return False
    return has_ref


async def run_verification():
    async with async_session() as session:
        subjects = await get_subjects(session)
        tasks = await get_tasks(session)

    print("=" * 90)
    print("🎓 ВЕРИФИКАЦИЯ КУРСОВ И МАТЕРИАЛОВ СТУДЕНТА (Группа 5108, ИРЭФ-ЦТ)")
    print("=" * 90)
    print(f"Всего дисциплин в базе: {len(subjects)} | Всего спарсенных материалов: {len(tasks)}")
    print("-" * 90)

    total_core_tasks = 0
    total_core_act = 0
    total_core_ref = 0

    subj_map = {s.name.strip(): s for s in subjects}

    for c in BB_COURSES:
        name = c["name"]
        subj = subj_map.get(name)

        if not subj:
            print(f"❌ [{c['num']}] {name} — НЕ НАЙДЕН В БАЗЕ ДАННЫХ!")
            continue

        c_tasks = [t for t in tasks if t.subject_id == subj.id]
        act_tasks = [t for t in c_tasks if not is_ref(t.title)]
        ref_tasks = [t for t in c_tasks if is_ref(t.title)]

        total_core_tasks += len(c_tasks)
        total_core_act += len(act_tasks)
        total_core_ref += len(ref_tasks)

        print(f"\n📚 [{c['num']}/9] {name}")
        print(f"    🔗 Blackboard ID: {c['bb_id']} | Ссылка: {c['url']}")
        print(f"    📊 Материалов: всего {len(c_tasks)} (к сдаче: {len(act_tasks)}, метод. файлы: {len(ref_tasks)})")
        print("    📝 Примеры работ:")
        for idx, t in enumerate(c_tasks[:3], 1):
            category = "📁 ФАЙЛ" if is_ref(t.title) else "🎯 К СДАЧЕ"
            print(f"       {idx}. [{category}] [{t.task_type}] {t.title}")

    print("\n" + "=" * 90)
    print(f"ИТОГ ПО 9 АКАДЕМИЧЕСКИМ КУРСАМ 1-ГО СЕМЕСТРА ГРУППЫ 5108:")
    print(f"  • Всего заданий и материалов: {total_core_tasks}")
    print(f"  • К сдаче (лабораторные, тесты, отчеты): {total_core_act}")
    print(f"  • Методические указания и файлы: {total_core_ref}")
    print("=" * 90)

    extra_subjs = [s for s in subjects if s.name not in [c["name"] for c in BB_COURSES] and s.id != 1]
    if extra_subjs:
        print("\n🏃 ДОПОЛНИТЕЛЬНЫЕ ЭЛЕКТИВНЫЕ КУРСЫ (ФИЗКУЛЬТУРА 2026-2027):")
        for s in extra_subjs:
            s_tasks = [t for t in tasks if t.subject_id == s.id]
            print(f"  • {s.name}: {len(s_tasks)} материалов")
        print("=" * 90)


if __name__ == "__main__":
    asyncio.run(run_verification())
