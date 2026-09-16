"""
Google Gemini AI service module for KAI Assistant 5108.
Provides structured natural language task parsing and automated lab work cheat-sheets.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from core.config import settings

logger = logging.getLogger("kai_assistant.gemini")


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
        subjects_formatted = ", ".join(f"'{s}'" for s in available_subjects)
        prompt = (
            "Ты — умный студенческий AI-ассистент группы 5108 (ИРЭФ-ЦТ, КАИ).\n"
            "Твоя задача — извлечь параметры учебной задачи из сообщения студента или старосты.\n\n"
            f"Список реальных зарегистрированных предметов студента:\n[{subjects_formatted}]\n\n"
            "Инструкции:\n"
            "1. Поле 'subject': сопоставь упомянутый предмет с максимально подходящим из списка выше. "
            "Если предмет не указан явно, постарайся определить по контексту или выбери наиболее подходящий.\n"
            "2. Поле 'title': сделай короткое емкое название задачи на русском языке.\n"
            "3. Поле 'task_type': выбери из 'лабораторная', 'доклад', 'конспект', 'оргвопрос', 'практическая', 'зачет', 'задание'.\n"
            "4. Поле 'deadline_raw': извлеки срок сдачи, если он упомянут (например, 'к следующей среде', 'до пятницы').\n"
            "5. Поле 'requirements': перечисли, что нужно подготовить (отчет, титульный лист, презентацию и т.д.).\n\n"
            f"Текст сообщения студента:\n{text.strip()}"
        )

        parsed: ParsedTask = self._call_with_fallback(contents=prompt, response_schema=ParsedTask)
        return parsed.model_dump()

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
