import asyncio
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from core.config import settings
from services.gemini_service import GeminiService

def test_gemini():
    print("=" * 80)
    print("           GOOGLE GEMINI AI INTEGRATION TEST (KAI ASSISTANT 5108)")
    print("=" * 80)
    print(f"API Key present: {bool(settings.gemini_api_key)}")
    print(f"Configured Model: {settings.gemini_model}")

    service = GeminiService()
    if not service.is_available():
        print("[-] ОШИБКА: GeminiService недоступен. Проверьте GEMINI_API_KEY в .env")
        sys.exit(1)

    print("[+] Сервис успешно инициализирован.")

    # 1. Test Task Parsing
    test_phrase = "К следующей среде по физике сделать отчет по лабе 2 и распечатать титульник"
    sample_subjects = [
        "Введение в профессиональную деятельность",
        "Высшая математика 1.1",
        "Инженерная графика - ИРЭТ",
        "Физика 1",
        "Основы российской государственности"
    ]

    print(f"\n[1] Тестирование распознавания естественного языка:")
    print(f'    Входная фраза: "{test_phrase}"')
    print(f"    Доступные предметы: {sample_subjects}")
    print("    Отправка запроса в Gemini...")

    parsed = service.parse_natural_task(test_phrase, sample_subjects)
    print("\n[+] Результат структурированного распознавания (JSON):")
    print(json.dumps(parsed, ensure_ascii=False, indent=2))

    assert "subject" in parsed, "Поле 'subject' отсутствует в результате"
    assert "title" in parsed, "Поле 'title' отсутствует в результате"
    assert "task_type" in parsed, "Поле 'task_type' отсутствует в результате"
    print("\n[OK] Распознавание задачи выполнено успешно!")

    # 2. Test Lab Summarization
    print("\n[2] Тестирование генерации шпаргалки по лабораторной работе:")
    lab_title = "Лабораторная работа №2. Исследование экранирования катушек индуктивности"
    lab_details = (
        "Цель работы: экспериментальное исследование влияния электромагнитных экранов "
        "на индуктивность и добротность катушек. Применяются генератор сигналов Г3-112, "
        "осциллограф С1-65А и измерительный стенд. Подготовить отчет и титульный лист по ГОСТ."
    )
    summary = service.summarize_lab_work(title=lab_title, details=lab_details)
    print("\n[+] Результат генерации шпаргалки (JSON):")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    assert "summary" in summary, "Поле 'summary' отсутствует в шпаргалке"
    assert "to_bring" in summary, "Поле 'to_bring' отсутствует в шпаргалке"
    assert "key_steps" in summary, "Поле 'key_steps' отсутствует в шпаргалке"
    print("\n[OK] Генерация шпаргалки выполнена успешно!")
    print("=" * 80)
    print("ВСЕ ТЕСТЫ GEMINI AI УСПЕШНО ПРОЙДЕНЫ!")

if __name__ == "__main__":
    test_gemini()
