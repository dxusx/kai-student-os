"""
Canonical Subject Registry & Subject Identity Resolution for KAI Student OS.
Provides:
- Canonical subject IDs
- Deterministic canonical aliases
- Hierarchical resolution (Canonical ID -> Canonical Name -> Registered DB Name -> Alias -> Fuzzy Fallback)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


# Canonical subject dictionary for Group 5108 / IREF-CT curriculum
CANONICAL_SUBJECTS: Dict[str, Dict[str, Any]] = {
    "math": {
        "canonical_name": "Высшая математика",
        "aliases": [
            "математика", "высшая математика", "матан", "вышмат",
            "математический анализ", "алгебра", "линал", "диффуры"
        ],
    },
    "physics": {
        "canonical_name": "Физика",
        "aliases": [
            "физика", "общая физика", "механика", "оптика",
            "термодинамика", "электромагнетизм", "квантовая физика"
        ],
    },
    "it_arch": {
        "canonical_name": "ИТ-Архитектура",
        "aliases": [
            "ит-архитектура", "ит архитектура", "информатика", "архитектура ис",
            "архитектура вычислительных систем", "информационные технологии", "эвм"
        ],
    },
    "networks": {
        "canonical_name": "Инфокоммуникационные системы",
        "aliases": [
            "инфокоммуникационные системы", "икс", "сети", "компьютерные сети",
            "телекоммуникации", "сетевые технологии", "инфоком"
        ],
    },
    "circuits": {
        "canonical_name": "Схемотехника",
        "aliases": [
            "схемотехника", "электроника", "цифровая схемотехника",
            "аналоговая схемотехника", "микросхемотехника"
        ],
    },
    "history": {
        "canonical_name": "История России",
        "aliases": [
            "история", "история россии", "история науки", "всемирная история"
        ],
    },
    "philosophy": {
        "canonical_name": "Философия",
        "aliases": [
            "философия", "фил"
        ],
    },
    "electrical": {
        "canonical_name": "Электротехника",
        "aliases": [
            "электротехника", "тоэ", "toe", "теоретические основы электротехники",
            "основы электротехники", "электротехника и электроника"
        ],
    },
    "discrete_math": {
        "canonical_name": "Дискретная математика",
        "aliases": [
            "дискретная математика", "дискретка", "дискретные структуры"
        ],
    },
    "oop": {
        "canonical_name": "Объектно-ориентированное программирование",
        "aliases": [
            "ооп", "объектно-ориентированное программирование", "программирование",
            "языки программирования", "разработка по"
        ],
    },
    "databases": {
        "canonical_name": "Базы данных",
        "aliases": [
            "базы данных", "бд", "субд", "sql", "проектирование бд"
        ],
    },
    "general": {
        "canonical_name": "Общие задачи",
        "aliases": [
            "общие задачи", "общее", "учеба", "разное", "задания", "деканат"
        ],
    },
}


def normalize_subject_key(text: str) -> str:
    """Normalize input text for comparison (lower, strip, collapse spaces, remove punctuation)."""
    clean = (text or "").strip().lower()
    clean = re.sub(r"[^\w\s-]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def resolve_canonical_subject(
    text_or_name: str,
    available_subjects: Optional[List[str]] = None,
) -> Tuple[str, str]:
    """
    Resolve subject identity with strict hierarchical precedence:
    1. Canonical ID exact match (e.g. 'physics', 'math')
    2. Canonical name exact match
    3. Available registered DB subject exact match
    4. Canonical alias match (substring / keyword)
    5. Fallback: fuzzy substring match against available subjects
    6. Ultimate fallback: 'Общие задачи'

    Returns:
        Tuple[str, str]: (canonical_id, matched_subject_name)
    """
    raw = (text_or_name or "").strip()
    norm = normalize_subject_key(raw)
    if not norm:
        return "general", "Общие задачи"

    # Step 1: Exact match on canonical_id
    if norm in CANONICAL_SUBJECTS:
        return norm, CANONICAL_SUBJECTS[norm]["canonical_name"]

    # Step 2: Exact match on canonical_name
    for cid, info in CANONICAL_SUBJECTS.items():
        if normalize_subject_key(info["canonical_name"]) == norm:
            return cid, info["canonical_name"]

    # Step 3: Exact match on registered DB subjects
    if available_subjects:
        for s in available_subjects:
            if normalize_subject_key(s) == norm:
                # Find if this subject maps to a known canonical_id
                matched_cid = "general"
                for cid, info in CANONICAL_SUBJECTS.items():
                    if normalize_subject_key(info["canonical_name"]) == norm or any(
                        normalize_subject_key(a) == norm for a in info["aliases"]
                    ):
                        matched_cid = cid
                        break
                return matched_cid, s

    # Step 4: Canonical alias match (alias word boundary or substring match)
    for cid, info in CANONICAL_SUBJECTS.items():
        for alias in info["aliases"]:
            alias_norm = normalize_subject_key(alias)
            # Full word or alias inside phrase
            if alias_norm in norm or norm in alias_norm:
                # If we have available_subjects, see if one matches this canonical name
                if available_subjects:
                    for s in available_subjects:
                        s_norm = normalize_subject_key(s)
                        if alias_norm in s_norm or normalize_subject_key(info["canonical_name"]) == s_norm:
                            return cid, s
                return cid, info["canonical_name"]

    # Step 5: Fuzzy fallback match against available_subjects
    if available_subjects:
        # Check 4-character stems
        for s in available_subjects:
            s_low = s.lower()
            stem = s_low[:4] if len(s_low) >= 4 else s_low
            if stem in norm or (len(s_low) > 3 and s_low in norm):
                return "general", s

        # First available subject if nothing else matched
        return "general", available_subjects[0]

    return "general", "Общие задачи"
