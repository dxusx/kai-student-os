"""
Google Gemini AI service module for KAI Assistant 5108.
Provides structured natural language task parsing and automated lab work cheat-sheets.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, date, time, timedelta
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None  # type: ignore
    types = None  # type: ignore

from core.config import settings

logger = logging.getLogger("kai_assistant.gemini")

try:
    from zoneinfo import ZoneInfo
    MSK_TZ = ZoneInfo("Europe/Moscow")
except Exception:
    import datetime as _dt
    MSK_TZ = _dt.timezone(_dt.timedelta(hours=3))

WEEKDAYS_STEMS = [
    ("понедельн", 0), ("пн", 0),
    ("вторник", 1), ("вт", 1),
    ("сред", 2), ("ср", 2),
    ("четверг", 3), ("чт", 3),
    ("пятниц", 4), ("пт", 4),
    ("суббот", 5), ("сб", 5),
    ("воскресен", 6), ("вс", 6),
]

MONTHS_MAP = {
    "январ": 1, "феврал": 2, "март": 3, "апрел": 4,
    "ма": 5, "июн": 6, "июл": 7, "август": 8,
    "сентябр": 9, "октябр": 10, "ноябр": 11, "декабр": 12,
}


def resolve_relative_deadline(
    deadline_raw: Optional[str],
    base_dt: Optional[datetime] = None
) -> Optional[datetime]:
    """
    Resolve Russian natural language deadline phrase to concrete datetime in Europe/Moscow timezone.
    Examples:
      - 'к следующей среде' -> next week's Wednesday at 18:00
      - 'до пятницы' -> upcoming Friday at 18:00
      - 'завтра' -> tomorrow at 23:59
      - 'через 2 дня' -> base_dt + 2 days at 18:00
      - 'до 25 октября' -> 25th of October at 18:00
    """
    if not deadline_raw or not deadline_raw.strip():
        return None

    raw = deadline_raw.strip().lower()

    if base_dt is None:
        base_dt = datetime.now(MSK_TZ)
    elif base_dt.tzinfo is None:
        base_dt = base_dt.replace(tzinfo=MSK_TZ)

    # 1. Direct ISO format check
    try:
        if re.match(r"^\d{4}-\d{2}-\d{2}", raw):
            parsed_iso = datetime.fromisoformat(raw)
            if parsed_iso.tzinfo is None:
                parsed_iso = parsed_iso.replace(tzinfo=MSK_TZ)
            return parsed_iso
    except Exception:
        pass

    # 2. Today / tomorrow / day after tomorrow
    if "сегодня" in raw:
        return datetime.combine(base_dt.date(), time(23, 59, 0), tzinfo=MSK_TZ)
    if "послезавтра" in raw:
        return datetime.combine(base_dt.date() + timedelta(days=2), time(23, 59, 0), tzinfo=MSK_TZ)
    if "завтра" in raw:
        return datetime.combine(base_dt.date() + timedelta(days=1), time(23, 59, 0), tzinfo=MSK_TZ)

    # 3. Relative days ("через N дней/дня/суток")
    days_match = re.search(r"через\s+(\d+)\s*(дн|ден|сут)", raw)
    if days_match:
        n_days = int(days_match.group(1))
        return datetime.combine(base_dt.date() + timedelta(days=n_days), time(18, 0, 0), tzinfo=MSK_TZ)

    # 4. Relative weeks ("через N недель/недели")
    weeks_match = re.search(r"через\s+(\d+)\s*(нед)", raw)
    if weeks_match:
        n_weeks = int(weeks_match.group(1))
        return datetime.combine(base_dt.date() + timedelta(weeks=n_weeks), time(18, 0, 0), tzinfo=MSK_TZ)

    # 5. Month dates ("до 25 октября", "к 12 ноября")
    for m_stem, m_num in MONTHS_MAP.items():
        date_pattern = rf"(\d{{1,2}})\s+{m_stem}[а-я]*"
        dm = re.search(date_pattern, raw)
        if dm:
            day = int(dm.group(1))
            year = base_dt.year
            if m_num < base_dt.month or (m_num == base_dt.month and day < base_dt.day):
                year += 1
            try:
                return datetime(year, m_num, day, 18, 0, 0, tzinfo=MSK_TZ)
            except ValueError:
                pass

    # 6. Weekdays ("к следующей среде", "до пятницы", "во вторник")
    is_next_week = any(w in raw for w in ["следующ", "след."])
    curr_w = base_dt.weekday()
    for w_stem, w_idx in WEEKDAYS_STEMS:
        if w_stem in raw:
            if is_next_week:
                days_ahead = (w_idx - curr_w) % 7 + 7
            else:
                days_ahead = w_idx - curr_w
                if days_ahead <= 0:
                    days_ahead += 7
            target_date = base_dt.date() + timedelta(days=days_ahead)
            return datetime.combine(target_date, time(18, 0, 0), tzinfo=MSK_TZ)

    return None


class ParsedTask(BaseModel):
    subject: str = Field(
        description="Название учебной дисциплины, максимально точно сопоставленное со списком доступных предметов"
    )
    title: str = Field(
        description="Краткая и четкая суть задачи (например, 'Отчет по лабораторной работе №2')"
    )
    task_type: str = Field(
        default="лабораторная",
        description="Тип задачи: 'лабораторная', 'доклад', 'конспект', 'оргвопрос', 'практическая', 'зачет' или 'задание'"
    )
    deadline_raw: Optional[str] = Field(
        default=None,
        description="Срок выполнения в исходном виде из текста (например, 'к следующей среде', 'до 25 мая', 'на следующей неделе')"
    )
    deadline_iso: Optional[str] = Field(
        default=None,
        description="Вычисленная точная дата и время дедлайна в формате YYYY-MM-DDTHH:MM:SS, если возможно определить относительно текущей даты"
    )
    requirements: Optional[str] = Field(
        default=None,
        description="Требования, что распечатать или подготовить (например, 'Распечатать титульный лист и отчет')"
    )


class LabSummary(BaseModel):
    summary: str = Field(
        description="Суть и цель работы в 2 емких и понятных студенту предложениях"
    )
    to_bring: List[str] = Field(
        default_factory=list,
        description="Чек-лист: что обязательно взять с собой на пару (распечатки, флешка, тетрадь, калькулятор и т.д.)"
    )
    key_steps: List[str] = Field(
        default_factory=list,
        description="3-4 главных практических шага выполнения лабораторной работы"
    )


class GeminiService:
    """Service wrapper for Google Gemini API with fallback resiliency."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model or "gemini-3.5-flash"
        self.candidate_models = [
            self.model,
            "gemini-2.5-flash-lite",
            "gemini-3.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-3.7-flash",
        ]
        self._client: Optional[genai.Client] = None
        if self.api_key:
            try:
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error("Failed to initialize Google GenAI Client: %s", e)

    def is_available(self) -> bool:
        """Check if Gemini API key is configured and client initialized."""
        return bool(self._client and self.api_key)

    def _call_with_fallback(self, contents: str, response_schema: Any) -> Any:
        """Execute generate_content with automatic model fallback in case of 503/404."""
        if not self._client:
            raise RuntimeError("GEMINI_API_KEY не сконфигурирован в .env")

        last_error = None
        seen_models = set()

        for m_name in self.candidate_models:
            if m_name in seen_models:
                continue
            seen_models.add(m_name)

            try:
                logger.info("Calling Gemini model: %s", m_name)
                resp = self._client.models.generate_content(
                    model=m_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=response_schema,
                        temperature=0.2,
                    ),
                )
                if resp.text:
                    return response_schema.model_validate_json(resp.text)
            except Exception as e:
                last_error = e
                logger.warning("Gemini model %s call failed (%s). Trying next candidate...", m_name, e)

        raise RuntimeError(f"Все кандидаты моделей Gemini завершились с ошибкой: {last_error}")

    def parse_natural_task(
        self,
        text: str,
        available_subjects: List[str]
    ) -> Dict[str, Any]:
        """
        Extract structured task metadata from natural student language or forwarded chat messages.
        """
        now_msk = datetime.now(MSK_TZ)
        now_str = now_msk.strftime("%Y-%m-%d (%A, %H:%M MSK)")
        subjects_formatted = ", ".join(f"'{s}'" for s in available_subjects)
        prompt = (
            "Ты — умный студенческий AI-ассистент группы 5108 (ИРЭФ-ЦТ, КАИ).\n"
            f"Текущая дата и время: {now_str}.\n"
            "Твоя задача — извлечь параметры учебной задачи из сообщения студента или старосты.\n\n"
            f"Список реальных зарегистрированных предметов студента:\n[{subjects_formatted}]\n\n"
            "Инструкции:\n"
            "1. Поле 'subject': сопоставь упомянутый предмет с максимально подходящим из списка выше. "
            "Если предмет не указан явно, постарайся определить по контексту или выбери наиболее подходящий.\n"
            "2. Поле 'title': сделай короткое емкое название задачи на русском языке.\n"
            "3. Поле 'task_type': выбери из 'лабораторная', 'доклад', 'конспект', 'оргвопрос', 'практическая', 'зачет', 'задание'.\n"
            "4. Поле 'deadline_raw': извлеки срок сдачи в исходном виде (например, 'к следующей среде', 'до пятницы', 'через 2 дня').\n"
            "5. Поле 'deadline_iso': вычисли точную дату и время дедлайна в формате YYYY-MM-DDTHH:MM:SS, учитывая текущую дату.\n"
            "6. Поле 'requirements': перечисли, что нужно подготовить (отчет, титульный лист, презентацию и т.д.).\n\n"
            f"Текст сообщения студента:\n{text.strip()}"
        )

        parsed: ParsedTask = self._call_with_fallback(contents=prompt, response_schema=ParsedTask)
        res = parsed.model_dump()
        if not res.get("deadline_iso") and res.get("deadline_raw"):
            resolved = resolve_relative_deadline(res["deadline_raw"], base_dt=now_msk)
            if resolved:
                res["deadline_iso"] = resolved.isoformat()
        return res

    def summarize_lab_work(
        self,
        title: str,
        details: str = "",
        file_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a concise, actionable student cheat-sheet for a laboratory assignment.
        """
        context_parts = [f"Название работы: {title}"]
        if details:
            context_parts.append(f"Описание и методические указания:\n{details[:2500]}")
        if file_text:
            context_parts.append(f"Фрагмент методички/файла:\n{file_text[:2500]}")

        context_str = "\n\n".join(context_parts)

        prompt = (
            "Ты — опытный старшекурсник и студенческий наставник в техническом университете КАИ (ИРЭФ-ЦТ).\n"
            "Составь четкую, лаконичную и практичную студенческую шпаргалку по этой лабораторной/практической работе.\n\n"
            "Требования к шпаргалке:\n"
            "1. 'summary': ровно в 2 понятных предложениях объясни, в чем реальная суть и цель этой работы (без сухой канцелярии).\n"
            "2. 'to_bring': конкретный чек-лист, что студенту обязательно взять с собой на пару (распечатанный отчет, титульник, флешка, карандаш с линейкой, калькулятор и т.д.).\n"
            "3. 'key_steps': список из 3-4 главных практических шагов выполнения работы в лаборатории.\n\n"
            f"Материалы задания:\n{context_str}"
        )

        summary: LabSummary = self._call_with_fallback(contents=prompt, response_schema=LabSummary)
        return summary.model_dump()
