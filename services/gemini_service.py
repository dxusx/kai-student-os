"""
Google Gemini AI service module for KAI Assistant 5108.
Provides structured natural language task parsing and automated lab work cheat-sheets.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
import re
import time as time_mod
from datetime import datetime, date, time, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None  # type: ignore
    types = None  # type: ignore

from core.config import settings

logger = logging.getLogger("kai_assistant.gemini")

# -------------------------------------------------------------
# AI ERROR TAXONOMY & CLASSIFICATION
# -------------------------------------------------------------

class AiErrorCategory(str, Enum):
    RATE_LIMIT = "RATE_LIMIT"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    UPSTREAM_UNAVAILABLE = "UPSTREAM_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    AUTH_ERROR = "AUTH_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"


class AiServiceError(Exception):
    """Structured AI service exception encapsulating classification and metadata."""
    def __init__(
        self,
        category: AiErrorCategory,
        message: str,
        original_error: Optional[Exception] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.category = category
        self.message = message
        self.original_error = original_error
        self.metadata = metadata or {}
        super().__init__(message)


def sanitize_text(text: str) -> str:
    """Strip API keys and sensitive tokens from error text."""
    if not text:
        return ""
    # Mask potential Google API keys (AIza...)
    sanitized = re.sub(r"AIza[0-9A-Za-z\-_]{20,50}", "[REDACTED_API_KEY]", text)
    # Mask Bearer tokens
    sanitized = re.sub(r"Bearer\s+[A-Za-z0-9\._\-]+", "Bearer [REDACTED_TOKEN]", sanitized)
    return sanitized


def classify_ai_error(err: Exception) -> AiErrorCategory:
    """
    Classify any upstream or local AI failure into one of 7 canonical categories:
    - RATE_LIMIT
    - QUOTA_EXCEEDED
    - UPSTREAM_UNAVAILABLE
    - TIMEOUT
    - INVALID_RESPONSE
    - AUTH_ERROR
    - NETWORK_ERROR
    """
    if isinstance(err, AiServiceError):
        return err.category

    err_str = str(err).lower()
    err_type = type(err).__name__.lower()
    status_code = getattr(err, "status_code", getattr(err, "code", None))

    # 1. AUTH_ERROR (check first to avoid mixing with quota/rate limit)
    if (
        status_code in (401, 403)
        and any(k in err_str for k in ["api_key", "unauthorized", "invalid api key", "permission", "unauthenticated", "forbidden", "key not found", "credentials"])
    ) or any(k in err_str for k in ["api_key_invalid", "invalid_api_key", "api key not valid", "unregistered api key", "gemini_api_key не сконфигурирован", "api key is not configured"]):
        return AiErrorCategory.AUTH_ERROR

    # 2. QUOTA_EXCEEDED (distinguish from temporary rate limit)
    if any(k in err_str for k in [
        "quota", "quota_exceeded", "exceeded your current quota",
        "free tier", "billing", "credit", "daily limit", "insufficient_quota"
    ]):
        return AiErrorCategory.QUOTA_EXCEEDED

    # 3. RATE_LIMIT
    if status_code == 429 or any(k in err_str for k in [
        "429", "rate_limit", "resource_exhausted", "too many requests",
        "requests per minute", "tokens per minute", "rpm limit", "tpm limit"
    ]):
        return AiErrorCategory.RATE_LIMIT

    # 4. TIMEOUT
    if isinstance(err, (TimeoutError, asyncio.TimeoutError)) or any(k in err_type for k in ["timeout", "timeouterror"]) or any(k in err_str for k in [
        "timeout", "timed out", "deadline exceeded", "readtimeout", "connecttimeout"
    ]):
        return AiErrorCategory.TIMEOUT

    # 5. UPSTREAM_UNAVAILABLE
    if status_code in (500, 502, 503, 504) or any(k in err_str for k in [
        "503", "502", "504", "unavailable", "bad gateway", "gateway timeout",
        "service unavailable", "overloaded", "model is overloaded", "high demand",
        "server is temporarily unable", "backend error", "upstream"
    ]):
        return AiErrorCategory.UPSTREAM_UNAVAILABLE

    # 6. NETWORK_ERROR
    if isinstance(err, (ConnectionError, OSError)) or any(k in err_type for k in ["connection", "network", "dns", "ssl", "socket"]) or any(k in err_str for k in [
        "connection refused", "dns lookup", "failed to resolve", "getaddrinfo",
        "network is unreachable", "connection reset", "broken pipe", "ssl error"
    ]):
        return AiErrorCategory.NETWORK_ERROR

    # 7. INVALID_RESPONSE
    if isinstance(err, (json.JSONDecodeError, ValueError)) or any(k in err_type for k in ["json", "validation", "pydantic", "decode"]) or any(k in err_str for k in [
        "jsondecodeerror", "validation error", "invalid json", "schema", "parse error",
        "empty response", "truncated response", "malformed"
    ]):
        return AiErrorCategory.INVALID_RESPONSE

    # Default fallback
    return AiErrorCategory.UPSTREAM_UNAVAILABLE


def get_ai_error_ui_info(category: AiErrorCategory) -> Dict[str, Any]:
    """
    Generate student-reassuring user messages and retry guidelines based on error category.
    Never shows raw 502/503 errors to the user.
    """
    base_title = "AI временно недоступен"
    reassurance = "Это не повлияло на сохранённые задания."

    details_map = {
        AiErrorCategory.RATE_LIMIT: {
            "detail": "Превышен лимит одновременных обращений к AI. Пожалуйста, подождите пару секунд и повторите попытку.",
            "retryable": True,
            "retry_after": 2.0,
        },
        AiErrorCategory.QUOTA_EXCEEDED: {
            "detail": "Дневной лимит обращений к AI исчерпан. Повторите попытку позже или обратитесь к старосте/администратору.",
            "retryable": False,
            "retry_after": None,
        },
        AiErrorCategory.UPSTREAM_UNAVAILABLE: {
            "detail": "Сервер генерации сейчас перегружен. Ваши данные в полной безопасности, повторите попытку через мгновение.",
            "retryable": True,
            "retry_after": 1.0,
        },
        AiErrorCategory.TIMEOUT: {
            "detail": "Время ожидания ответа AI истекло из-за задержек сети. Пожалуйста, попробуйте еще раз.",
            "retryable": True,
            "retry_after": 1.0,
        },
        AiErrorCategory.INVALID_RESPONSE: {
            "detail": "Ответ AI не удалось обработать. Попробуйте повторить запрос с другим текстом задания.",
            "retryable": False,
            "retry_after": None,
        },
        AiErrorCategory.AUTH_ERROR: {
            "detail": "Не настроен или недействителен ключ доступа к Google Gemini API.",
            "retryable": False,
            "retry_after": None,
        },
        AiErrorCategory.NETWORK_ERROR: {
            "detail": "Проблема сетевого подключения к сервису AI. Проверьте подключение к интернету.",
            "retryable": True,
            "retry_after": 2.0,
        },
    }

    info = details_map.get(category, {
        "detail": "Сервис AI временно недоступен. Попробуйте снова чуть позже.",
        "retryable": True,
        "retry_after": 1.0,
    })

    return {
        "title": base_title,
        "reassurance": reassurance,
        "full_message": f"{base_title}. {reassurance}",
        "detail": info["detail"],
        "retryable": info["retryable"],
        "retry_after": info["retry_after"],
    }


# -------------------------------------------------------------
# SERVER-SIDE DETERMINISTIC CACHE
# -------------------------------------------------------------

class DeterministicAiCache:
    """Thread-safe LRU / TTL cache for deterministic AI responses (lab summaries, documents)."""
    def __init__(self, max_entries: int = 500, ttl_seconds: int = 86400 * 3):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._max_entries = max_entries
        self._ttl_seconds = ttl_seconds

    @staticmethod
    def compute_key(*parts: Any) -> str:
        h = hashlib.sha256()
        for p in parts:
            if p is not None:
                h.update(str(p).strip().encode("utf-8"))
                h.update(b"::")
        return h.hexdigest()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        entry = self._cache.get(key)
        if not entry:
            return None
        now = time_mod.time()
        if now - entry["timestamp"] > self._ttl_seconds:
            self._cache.pop(key, None)
            return None
        return entry["data"]

    def set(self, key: str, data: Dict[str, Any]):
        if len(self._cache) >= self._max_entries:
            keys_to_remove = sorted(self._cache.keys(), key=lambda k: self._cache[k]["timestamp"])[:max(1, self._max_entries // 10)]
            for k in keys_to_remove:
                self._cache.pop(k, None)
        self._cache[key] = {
            "timestamp": time_mod.time(),
            "data": data,
        }

    def clear(self):
        self._cache.clear()


global_ai_cache = DeterministicAiCache()

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
    auditorium: Optional[str] = Field(
        default=None,
        description="Номер аудитории или корпус, если упомянут в тексте (например, '301', 'ауд. 441', 'КСК Олимп')"
    )
    materials_summary: Optional[str] = Field(
        default=None,
        description="Краткая сводка материалов или файлов (например, '2 файла', 'методичка', 'бланк отчета')"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Краткое понятное объяснение (1-2 предложения), почему выбраны именно такие дедлайн, предмет и аудитория на основе контекста"
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
        self.model = model or settings.gemini_model or "gemini-3.6-flash"
        self.candidate_models = [self.model]
        if "gemini-3.6-flash" not in self.candidate_models:
            self.candidate_models.append("gemini-3.6-flash")
        elif "gemini-3.7-flash" not in self.candidate_models:
            self.candidate_models.append("gemini-3.7-flash")
        self._client: Optional[genai.Client] = None
        if self.api_key:
            try:
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error("Failed to initialize Google GenAI Client: %s", e)

    def is_available(self) -> bool:
        """Check if Gemini API key is configured and client initialized."""
        return bool(self._client and self.api_key)

    def _call_with_fallback(
        self,
        contents: str,
        response_schema: Any,
        max_retries: int = 1,
        initial_backoff: float = 0.2,
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        Execute generate_content with automatic candidate model fallback and bounded exponential backoff.
        Only retries safe transient errors (RATE_LIMIT, UPSTREAM_UNAVAILABLE, TIMEOUT, NETWORK_ERROR).
        Never retries AUTH_ERROR, QUOTA_EXCEEDED, or INVALID_RESPONSE.
        Returns tuple of (validated_model, execution_metadata).
        """
        started_at = datetime.now(timezone.utc).isoformat()
        t0 = time_mod.perf_counter()

        if not self._client:
            duration_ms = int((time_mod.perf_counter() - t0) * 1000)
            meta = {
                "started_at": started_at,
                "duration_ms": duration_ms,
                "provider": "google-gemini",
                "model": self.model,
                "success": False,
                "failure_category": AiErrorCategory.AUTH_ERROR.value,
                "cached": False,
            }
            raise AiServiceError(
                category=AiErrorCategory.AUTH_ERROR,
                message="GEMINI_API_KEY не сконфигурирован в .env",
                metadata=meta,
            )

        last_error = None
        seen_models = set()

        for m_name in self.candidate_models:
            if m_name in seen_models:
                continue
            seen_models.add(m_name)

            for attempt in range(max_retries + 1):
                try:
                    logger.info("Calling Gemini model: %s (attempt %d/%d)", m_name, attempt + 1, max_retries + 1)
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
                        validated = response_schema.model_validate_json(resp.text)
                        duration_ms = int((time_mod.perf_counter() - t0) * 1000)
                        meta = {
                            "started_at": started_at,
                            "duration_ms": duration_ms,
                            "provider": "google-gemini",
                            "model": m_name,
                            "success": True,
                            "failure_category": None,
                            "cached": False,
                        }
                        return validated, meta
                    else:
                        raise ValueError("Empty response received from Gemini API")
                except Exception as e:
                    last_error = e
                    cat = classify_ai_error(e)
                    logger.warning(
                        "Gemini model %s call failed on attempt %d (%s: %s).",
                        m_name, attempt + 1, cat.value, sanitize_text(str(e))
                    )

                    # Non-retryable errors: stop retrying this model immediately
                    if cat in (AiErrorCategory.AUTH_ERROR, AiErrorCategory.QUOTA_EXCEEDED, AiErrorCategory.INVALID_RESPONSE) or "404" in str(e) or "not_found" in str(e).lower():
                        break

                    # Safe transient errors: apply exponential backoff if attempts remain
                    if attempt < max_retries:
                        backoff = initial_backoff * (2 ** attempt) + random.uniform(0.02, 0.08)
                        logger.info("Retrying model %s in %.2fs (exponential backoff)...", m_name, backoff)
                        time_mod.sleep(backoff)

        # All models and retries exhausted
        duration_ms = int((time_mod.perf_counter() - t0) * 1000)
        final_cat = classify_ai_error(last_error) if last_error else AiErrorCategory.UPSTREAM_UNAVAILABLE
        sanitized_msg = sanitize_text(str(last_error)) if last_error else "Все кандидаты моделей Gemini завершились с ошибкой"
        meta = {
            "started_at": started_at,
            "duration_ms": duration_ms,
            "provider": "google-gemini",
            "model": self.model,
            "success": False,
            "failure_category": final_cat.value,
            "cached": False,
        }
        raise AiServiceError(
            category=final_cat,
            message=sanitized_msg,
            original_error=last_error,
            metadata=meta,
        )

    def _rule_based_fallback(
        self,
        text: str,
        available_subjects: List[str]
    ) -> Dict[str, Any]:
        """
        Deterministic heuristic parser used when Google Gemini API is offline,
        unconfigured, or experiencing quota/rate limits.
        """
        text_lower = text.lower()
        now_msk = datetime.now(MSK_TZ)

        # 1. Match subject
        matched_subject = None
        for s in available_subjects:
            s_low = s.lower()
            stem = s_low[:4] if len(s_low) >= 4 else s_low
            if stem in text_lower or (len(s_low) > 3 and s_low in text_lower):
                matched_subject = s
                break

        if not matched_subject:
            # Common abbreviations / synonyms
            if any(k in text_lower for k in ["вышмат", "матан", "матем", "алгебр"]):
                for s in available_subjects:
                    if "матем" in s.lower():
                        matched_subject = s
                        break
            elif "физик" in text_lower:
                for s in available_subjects:
                    if "физик" in s.lower():
                        matched_subject = s
                        break
            elif any(k in text_lower for k in ["орг", "государственност", "росси"]):
                for s in available_subjects:
                    if any(sub in s.lower() for sub in ["орг", "государственност"]):
                        matched_subject = s
                        break
            elif any(k in text_lower for k in ["информ", "програм"]):
                for s in available_subjects:
                    if any(sub in s.lower() for sub in ["информ", "програм"]):
                        matched_subject = s
                        break

        if not matched_subject:
            matched_subject = available_subjects[0] if available_subjects else "Общие задачи"

        # 2. Match task type
        task_type = "задание"
        if any(k in text_lower for k in ["лаб", "л/р", "лр", "лабораторн"]):
            task_type = "лабораторная"
        elif any(k in text_lower for k in ["пз", "п/з", "практик"]):
            task_type = "практическая"
        elif any(k in text_lower for k in ["доклад", "презентац", "реферат"]):
            task_type = "доклад"
        elif any(k in text_lower for k in ["конспект", "лекци"]):
            task_type = "конспект"
        elif any(k in text_lower for k in ["зачет", "экзамен", "коллоквиум", "кр", "контрольн"]):
            task_type = "зачет"
        elif any(k in text_lower for k in ["орг", "старост", "собрани", "взнос", "опрос"]):
            task_type = "оргвопрос"

        # 3. Detect number & build title
        num_match = re.search(r"(?:№|номер|#|\b)\s*(\d+)", text)
        num_str = f" №{num_match.group(1)}" if num_match else ""

        if task_type == "лабораторная":
            title = f"Лабораторная работа{num_str}"
        elif task_type == "практическая":
            title = f"Практическое занятие{num_str}"
        elif task_type == "доклад":
            title = f"Доклад{num_str}"
        elif task_type == "конспект":
            title = f"Конспект лекции{num_str}"
        elif task_type == "зачет":
            title = f"Подготовка к зачету/контрольной{num_str}"
        elif task_type == "оргвопрос":
            title = "Организационный вопрос"
        else:
            first_line = text.strip().split("\n")[0]
            title = first_line[:50].strip() or "Учебное задание"

        # 4. Detect auditorium
        auditorium = None
        aud_m = re.search(r"(?:ауд\.?|аудитори[яи]|каб\.?)\s*([0-9]+[а-яА-Я]?)", text, re.I)
        if aud_m:
            auditorium = aud_m.group(1)
        else:
            v_aud_m = re.search(r"\bв\s+([0-9]{3}[а-яА-Я]?)\b", text, re.I)
            if v_aud_m:
                auditorium = v_aud_m.group(1)

        # 5. Detect materials
        materials_summary = None
        files_m = re.search(r"(\d+)\s*(?:файл|документ)", text, re.I)
        if files_m:
            count = int(files_m.group(1))
            materials_summary = f"{count} файла" if 2 <= count <= 4 else f"{count} файлов"
        elif "методичк" in text_lower:
            materials_summary = "Методические указания"
        elif "бланк" in text_lower:
            materials_summary = "Бланк отчета"

        # 6. Detect deadline
        deadline_raw = None
        deadline_iso = None
        deadline_patterns = [
            r"(?:до|к)\s+следующ[а-я]*\s+[а-я]+",
            r"(?:до|к)\s+[а-я]+",
            r"через\s+\d+\s*(?:дн|ден|сут|нед)[а-я]*",
            r"(?:сегодня|завтра|послезавтра)",
            r"(?:до|к)\s+\d{1,2}\s+[а-я]+",
        ]
        for pat in deadline_patterns:
            dm = re.search(pat, text_lower)
            if dm:
                deadline_raw = dm.group(0).strip()
                break

        if deadline_raw:
            dt = resolve_relative_deadline(deadline_raw, base_dt=now_msk)
            if dt:
                deadline_iso = dt.isoformat()

        # 7. Requirements
        requirements = None
        if "распечат" in text_lower or "титульн" in text_lower:
            requirements = "Распечатать титульный лист и материалы"
        elif "презентац" in text_lower or "слайд" in text_lower:
            requirements = "Подготовить слайды презентации"

        return {
            "subject": matched_subject,
            "title": title,
            "task_type": task_type,
            "deadline_raw": deadline_raw,
            "deadline_iso": deadline_iso,
            "requirements": requirements,
            "auditorium": auditorium,
            "materials_summary": materials_summary,
            "reasoning": f"Распознано по ключевым фразам: предмет «{matched_subject or 'Общие'}», срок «{deadline_raw or 'не указан'}», аудитория «{auditorium or 'по расписанию'}».",
        }

    def parse_natural_task(
        self,
        text: str,
        available_subjects: List[str]
    ) -> Dict[str, Any]:
        """
        Extract structured task metadata from natural student language or forwarded chat messages.
        Utilizes Google Gemini AI Structured Outputs with seamless fallback to heuristic parsing.
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
            "6. Поле 'requirements': перечисли, что нужно подготовить (отчет, титульный лист, презентацию и т.д.).\n"
            "7. Поле 'auditorium': номер аудитории или корпус, если упомянут (например, '301', 'ауд. 441', 'КСК Олимп').\n"
            "8. Поле 'materials_summary': краткая сводка файлов/материалов, если упомянуты (например, '2 файла', 'методичка').\n"
            "9. Поле 'reasoning': кратко и понятно для студента объясни (1 фраза), почему именно так определены дедлайн и предмет (например, 'Срок определен по расписанию среды следующей недели, аудитория указана в сообщении').\n\n"
            f"Текст сообщения студента:\n{text.strip()}"
        )

        if not self.is_available():
            logger.info("Gemini client not configured, using rule-based fallback parser.")
            fallback_res = self._rule_based_fallback(text, available_subjects)
            fallback_res["_metadata"] = {
                "started_at": datetime.now(timezone.utc).isoformat(),
                "duration_ms": 1,
                "provider": "rule_based_fallback",
                "model": "heuristic",
                "success": True,
                "failure_category": None,
                "cached": False,
                "source": "heuristic_fallback",
            }
            return fallback_res

        try:
            parsed, metadata = self._call_with_fallback(contents=prompt, response_schema=ParsedTask)
            res = parsed.model_dump()
            if not res.get("deadline_iso") and res.get("deadline_raw"):
                resolved = resolve_relative_deadline(res["deadline_raw"], base_dt=now_msk)
                if resolved:
                    res["deadline_iso"] = resolved.isoformat()
            res["_metadata"] = metadata
            res["_metadata"]["source"] = "google-gemini"
            return res
        except Exception as e:
            cat = classify_ai_error(e)
            logger.warning("Gemini AI parse failed (%s: %s), falling back to rule-based parser.", cat.value, e)
            fallback_res = self._rule_based_fallback(text, available_subjects)
            fallback_res["_metadata"] = {
                "started_at": datetime.now(timezone.utc).isoformat(),
                "duration_ms": 1,
                "provider": "rule_based_fallback",
                "model": "heuristic",
                "success": True,
                "failure_category": cat.value,
                "cached": False,
                "source": "heuristic_fallback",
                "ai_error_category": cat.value,
            }
            return fallback_res

    def summarize_lab_work(
        self,
        title: str,
        details: str = "",
        file_text: Optional[str] = None,
        cache_user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a concise, actionable student cheat-sheet for a laboratory assignment.
        Integrates server-side deterministic cache and metadata.
        """
        cache_key = global_ai_cache.compute_key("lab_summary", cache_user_id or "shared", title, details, file_text)
        cached_result = global_ai_cache.get(cache_key)
        if cached_result:
            result_copy = dict(cached_result)
            result_copy["_metadata"] = {
                "started_at": datetime.now(timezone.utc).isoformat(),
                "duration_ms": 1,
                "provider": "google-gemini",
                "model": self.model,
                "success": True,
                "failure_category": None,
                "cached": True,
            }
            return result_copy

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

        summary_model, metadata = self._call_with_fallback(contents=prompt, response_schema=LabSummary)
        res = summary_model.model_dump()
        res["_metadata"] = metadata
        global_ai_cache.set(cache_key, res)
        return res
