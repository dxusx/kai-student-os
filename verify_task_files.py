import asyncio
import sqlite3
import sys
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def verify_tasks():
    conn = sqlite3.connect("kai_assistant.db")
    cursor = conn.cursor()

    query = """
        SELECT s.name, t.title, t.task_type, t.file_name, t.file_url, t.external_url
        FROM tasks t
        JOIN subjects s ON t.subject_id = s.id
        WHERE t.source = 'bb'
        ORDER BY s.name, t.id
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    total_bb = len(rows)
    with_files = [r for r in rows if r[4]]
    without_files = [r for r in rows if not r[4]]

    print("=" * 80)
    print("           BLACKBOARD SCRAPER 2.0 VERIFICATION & INTEGRITY AUDIT")
    print("=" * 80)
    print(f"Всего задач и материалов из Blackboard: {total_bb}")
    print(f"  - С прикрепленным изолированным файлом: {len(with_files)}")
    print(f"  - Без отдельного файла (file_url = None): {len(without_files)}")

    # Leakage check: Count file_url frequencies
    file_urls = [r[4] for r in with_files]
    url_counts = Counter(file_urls)
    duplicates = {url: count for url, count in url_counts.items() if count > 1}

    print("\n[1] ПРОВЕРКА НА УТЕЧКИ (FILE ISOLATION / LEAKAGE CHECK):")
    if not duplicates:
        print("  [OK] Все прикрепленные файлы 100% уникальны для каждой задачи!")
    else:
        print(f"  Замечено {len(duplicates)} файлов, общих для нескольких пунктов:")
        for url, count in list(duplicates.items())[:5]:
            matched_tasks = [f"{r[0]}: {r[1]}" for r in with_files if r[4] == url]
            print(f"    - Встречается {count} раз: {url}")
            print(f"      Задачи: {matched_tasks[:3]}")

    # Deep Link check
    with_upload = [r for r in rows if r[5] and "uploadAssignment" in r[5]]
    with_content = [r for r in rows if r[5] and "listContent" in r[5]]
    print(f"\n[2] ПРОВЕРКА DEEP LINKS:")
    print(f"  - Задач с прямой ссылкой на форму сдачи (uploadAssignment): {len(with_upload)}")
    print(f"  - Материалов с точной ссылкой на подраздел (listContent): {len(with_content)}")
    print(f"  - Всего задач с точным external_url: {len([r for r in rows if r[5]])}")

    # Print Table
    print("\n[3] ВЫБОРКА ПЕРВЫХ 25 ЗАДАЧ:")
    print(f"{'Предмет':<25} | {'Название задачи':<30} | {'Имя файла':<22} | {'Точный URL в BB':<35}")
    print("-" * 120)

    for row in rows[:25]:
        subj = (row[0][:23] + "..") if len(row[0]) > 25 else row[0]
        title = (row[1][:28] + "..") if len(row[1]) > 30 else row[1]
        fname = (row[3][:20] + "..") if row[3] and len(row[3]) > 22 else (row[3] or "[Без файла]")
        ext_url = (row[5][:33] + "..") if row[5] and len(row[5]) > 35 else (row[5] or "")
        print(f"{subj:<25} | {title:<30} | {fname:<22} | {ext_url:<35}")

    print("-" * 120)
    print("=" * 80)

if __name__ == "__main__":
    verify_tasks()
