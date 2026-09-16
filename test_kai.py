"""
Verification script for Sprint 1: KAI API integration.
Fetches real schedule from https://kai.ru/web/studentu/raspisanie1,
filters for group 5108 (subgroup 2),
calculates week parity and displays the real schedule for the current week in console.
"""

import sys
from datetime import date, datetime, timedelta

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.config import settings
from services.kai_api import KaiApiClient, get_week_parity


RUSSIAN_WEEKDAYS = {
    1: "Понедельник",
    2: "Вторник",
    3: "Среда",
    4: "Четверг",
    5: "Пятница",
    6: "Суббота",
    7: "Воскресенье",
}


def main():
    print("=" * 70)
    print("🎓 КНИТУ-КАИ | СТУДЕНЧЕСКИЙ АССИСТЕНТ (СПРИНТ 1)")
    print("=" * 70)

    group = settings.kai_group or "5108"
    subgroup = settings.kai_subgroup or 2

    client = KaiApiClient()

    # 1. Поиск groupId через GET-запрос к реальному порталу
    print(f"\n[1] Поиск groupId для группы {group}...")
    print(f"    GET {client.base_url}?query={group}")
    group_id = client.search_group_id(group)
    print(f"    -> Успешно найден groupId: {group_id}")

    # 2. Получение расписания через POST-запрос к реальному порталу
    print(f"\n[2] Запрос живого расписания...")
    print(f"    POST {client.base_url} (groupId={group_id})")
    raw_schedule = client.get_schedule(group_id)
    total_days = len(raw_schedule)
    total_raw_lessons = sum(len(lessons) for lessons in raw_schedule.values())
    print(f"    -> Загружено учебных дней: {total_days}, всего пар в базе: {total_raw_lessons}")

    # 3. Определение параметров текущей недели
    today = date.today()
    # Понедельник текущей недели
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    iso_week = today.isocalendar()[1]
    parity = get_week_parity(today)
    parity_str = "ЧЕТНАЯ" if parity == "чет" else "НЕЧЕТНАЯ"

    print("\n" + "=" * 70)
    print(f"📅 НАСТОЯЩЕЕ РАСПИСАНИЕ НА ТЕКУЩУЮ НЕДЕЛЮ")
    print(f"   Период: {monday.strftime('%d.%m.%Y')} — {sunday.strftime('%d.%m.%Y')}")
    print(f"   Академическая группа: {group} | Подгруппа: {subgroup}")
    print(f"   ISO-неделя №{iso_week} | Неделя: {parity_str} ({parity})")
    print("=" * 70)

    # 4. Вывод расписания на каждый день недели (Пн - Сб)
    week_schedule = client.get_week_schedule(
        raw_schedule,
        target_monday=monday,
        subgroup=subgroup,
        strict_date=True
    )

    total_lessons_week = 0

    for day_date, lessons in week_schedule.items():
        day_num = day_date.weekday() + 1
        day_name = RUSSIAN_WEEKDAYS.get(day_num, "")
        is_today = (day_date == today)
        today_marker = " 👈 [СЕГОДНЯ]" if is_today else ""

        print(f"\n📌 {day_name.upper()}, {day_date.strftime('%d.%m.%Y')}{today_marker}")
        print("-" * 70)

        if not lessons:
            print("   (Занятий нет / день самостоятельной работы)")
        else:
            total_lessons_week += len(lessons)
            for idx, lesson in enumerate(lessons, 1):
                type_label = lesson.discipl_type.upper() if lesson.discipl_type else "ЗАНЯТИЕ"
                potok_label = f"[{lesson.potok}]" if lesson.potok else "[Поток]"
                print(f"  {idx}. ⏰ {lesson.day_time} | {lesson.discipl_name}")
                print(f"     Тип: {type_label} {potok_label}")
                print(f"     Здание/корпус: {lesson.build_num or '—'}, Аудитория: {lesson.aud_num or '—'}")
                print(f"     Преподаватель: {lesson.prepod_name or '—'}")
                if lesson.day_date:
                    # Показываем даты или регулярность
                    print(f"     Даты занятий: {lesson.day_date}")
                print()

    print("=" * 70)
    print(f"ИТОГО НА НЕДЕЛЮ: {total_lessons_week} пар(ы) для {subgroup}-й подгруппы.")

    # 5. Верификация корректности фильтрации
    print("\n🔍 ВЕРИФИКАЦИЯ ФИЛЬТРАЦИИ ПОДГРУПП:")
    filtered_all = client.filter_for_subgroup(raw_schedule, subgroup=subgroup) if hasattr(client, 'filter_for_subgroup') else None
    
    # Проверяем все занятия в сетке на отсутствие маркеров 1-й подгруппы
    sg1_found = 0
    sg2_found = 0
    common_found = 0

    for day_lessons in week_schedule.values():
        for l in day_lessons:
            blob = f"{l.discipl_name} {l.potok} {l.aud_num}".lower()
            if "1 подгр" in blob or "1 п/г" in blob or "(1)" in blob:
                sg1_found += 1
            if "2 подгр" in blob or "2 п/г" in blob or "(2)" in blob:
                sg2_found += 1
            if not ("подгр" in blob or "п/г" in blob or "(1)" in blob or "(2)" in blob):
                common_found += 1

    print(f"  • Найдено занятий для 2-й подгруппы: {sg2_found}")
    print(f"  • Найдено общих потоковых занятий: {common_found}")
    print(f"  • Обнаружено ошибочных пар 1-й подгруппы: {sg1_found}")
    if sg1_found == 0:
        print("  -> Фильтрация работает ИДЕАЛЬНО: ни одной пары 1-й подгруппы не пропущено! ✅")
    print("=" * 70)


if __name__ == "__main__":
    main()
