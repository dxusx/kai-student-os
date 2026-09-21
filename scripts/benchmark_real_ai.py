"""
Dedicated Real Google Gemini AI Latency Benchmark for KAI Student OS.
Executes live benchmark against the Gemini API in a safe test environment.
Measures p50, p95, p99, and max latencies.
NEVER prints or leaks API keys.
"""

import math
import os
import sys
import time
from typing import List, Optional

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from services.gemini_service import GeminiService, ParsedTask


def calculate_percentile(data: List[float], p: float) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = (len(sorted_data) - 1) * (p / 100.0)
    lower = int(math.floor(idx))
    upper = int(math.ceil(idx))
    if lower == upper:
        return round(sorted_data[int(idx)], 2)
    weight = idx - lower
    return round(sorted_data[lower] * (1.0 - weight) + sorted_data[upper] * weight, 2)


def run_benchmark():
    print("=" * 60)
    print("KAI STUDENT OS — DEDICATED REAL GEMINI AI BENCHMARK")
    print("=" * 60)

    if not settings.gemini_api_key:
        print("[STATUS] GEMINI_API_KEY is not configured.")
        print("[STATUS] REAL AI = NOT VERIFIED")
        return None

    service = GeminiService()
    if not service.is_available():
        print("[STATUS] Gemini client initialization failed or not available.")
        print("[STATUS] REAL AI = NOT VERIFIED")
        return None

    test_inputs = [
        "Ребята, по Схемотехнике нужно сдать отчет по лабе 2 до следующего вторника 18:00.",
        "кароч физичка сказала лабу принести в пн крайняк, иначе незачет",
        "1. Сдать конспект по истории 2. Подготовить доклад по философии к пятнице",
        "ДЗ по высшей математике: решить номера 14, 15, 18 к следующему вторнику",
        "Задание от старосты: заполнить форму для профкома",
        "Тестирование AI: лаба 4 по информатике, написать программу на питоне",
        "Отчет по практике сдать до 15 ноября в деканат 5 зд.",
        "Подготовка к контрольной по физике в субботу в 301 ауд",
        "Сдать титульный лист к диплому до конца месяца",
        "Лабораторная работа по электротехнике №5 к следующей среде в 441 ауд",
    ]

    subjects = [
        "Схемотехника", "Физика", "История", "Философия",
        "Высшая математика", "Информатика", "Электротехника"
    ]

    print(f"Target Model: {service.model}")
    print(f"Iterations:   {len(test_inputs)}")
    print("Running live API inference calls (safe payload, no PII)...")

    latencies_ms: List[float] = []

    for i, inp in enumerate(test_inputs):
        t0 = time.perf_counter()
        try:
            res = service.parse_natural_task(inp, subjects)
            t1 = time.perf_counter()
            dur_ms = round((t1 - t0) * 1000.0, 2)
            source = res.get("_metadata", {}).get("source", "unknown")
            latencies_ms.append(dur_ms)
            print(f"  [{i+1:02d}/10] {dur_ms:7.2f} ms | Source: {source} | Title: {res.get('title', '')[:40]}")
        except Exception as e:
            t1 = time.perf_counter()
            dur_ms = round((t1 - t0) * 1000.0, 2)
            print(f"  [{i+1:02d}/10] FAILED ({dur_ms:.2f} ms): {type(e).__name__}")

    if not latencies_ms:
        print("\n[ERROR] All live benchmark requests failed.")
        return None

    p50 = calculate_percentile(latencies_ms, 50)
    p95 = calculate_percentile(latencies_ms, 95)
    p99 = calculate_percentile(latencies_ms, 99)
    min_lat = round(min(latencies_ms), 2)
    max_lat = round(max(latencies_ms), 2)
    mean_lat = round(sum(latencies_ms) / len(latencies_ms), 2)

    print("\n" + "=" * 60)
    print("REAL GEMINI LATENCY DISTRIBUTION SUMMARY")
    print("=" * 60)
    print(f"Total Requests: {len(latencies_ms)}")
    print(f"Min Latency:    {min_lat} ms")
    print(f"Median (p50):   {p50} ms")
    print(f"Mean Latency:   {mean_lat} ms")
    print(f"p95 Latency:    {p95} ms")
    print(f"p99 Latency:    {p99} ms")
    print(f"Max Latency:    {max_lat} ms")
    print(f"Real AI SLA (<3s): {'PASS' if p95 <= 3000 else 'BREACH'}")
    print("=" * 60)

    return {
        "p50": p50,
        "p95": p95,
        "p99": p99,
        "min": min_lat,
        "max": max_lat,
        "mean": mean_lat,
        "count": len(latencies_ms),
    }


if __name__ == "__main__":
    run_benchmark()
