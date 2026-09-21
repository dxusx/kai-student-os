"""
Kapipara API Client Module (services/para_api.py).
Interfaces with the modern Kapipara schedule service (https://api.capypara.ru/api),
maps schedule entries into normalized KAI Student OS models with change detection (is_changed),
and provides seamless fallback to KaiApiClient if Kapipara is unreachable.
"""

from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional
import requests
import urllib3

from core.config import settings
from services.kai_api import (
    KaiApiClient,
    KaiApiError,
    Lesson,
    get_week_parity,
    is_even_week,
    merge_and_deduplicate_lessons,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger("kai_assistant.para_api")


class KapiparaApiError(Exception):
    """Exception raised when Kapipara API request fails or returns invalid data."""
    pass


def is_kapipara_change(item: Dict[str, Any]) -> bool:
    """
    Determine if a Kapipara schedule entry represents a lesson change, replacement, or transfer.
    Checks:
    1. Explicit boolean flag is_changed / isChanged
    2. Status field indicating change, replacement or transfer
    3. Keywords in disciplname, discipltype or daydate
    4. Isolated one-off calendar date (e.g. '28.12' overriding regular bi-weekly class)
    """
    if bool(item.get("is_changed") or item.get("isChanged")):
        return True

    status = str(item.get("status") or "").lower().strip()
    if status in {"change", "replace", "transfer", "замена", "перенос"}:
        return True

    discipl_name = str(item.get("disciplname") or item.get("disciplName") or "")
    discipl_type = str(item.get("discipltype") or item.get("disciplType") or "")
    day_date = str(item.get("daydate") or item.get("dayDate") or "")

    combined_text = f"{discipl_name} {discipl_type} {day_date}".lower()
    if any(k in combined_text for k in ["замен", "перенос"]):
        return True

    # Check for single isolated date (e.g. '28.12' in semester schedule where regular classes have 3+ dates)
    dates = re.findall(r"\b\d{1,2}\.\d{1,2}\b", day_date)
    if len(dates) == 1 and "/" not in day_date:
        return True

    return False


class KapiparaClient:
    """Client for fetching and parsing group schedules from Kapipara API."""

    DEFAULT_BASE_URL = "https://api.capypara.ru/api"

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 8,
        fallback_kai_client: Optional[KaiApiClient] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.fallback_kai_client = fallback_kai_client or KaiApiClient(
            base_url=settings.kai_api_url,
            timeout=timeout,
        )
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "application/json",
        })

    def search_groups(self, query: str = "5108") -> List[Dict[str, Any]]:
        """
        Search for group metadata via GET /schedule_public/groups?query={query}.
        Returns list of matching dicts, e.g. [{'id': '28676', 'groupNum': '5108', 'specNum': '25.05.03'}].
        """
        url = f"{self.base_url}/schedule_public/groups"
        params = {"query": str(query).strip()}
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout, verify=False)
            if resp.status_code != 200:
                raise KapiparaApiError(f"Kapipara search returned HTTP {resp.status_code}: {resp.text[:150]}")
            data = resp.json()
            return data.get("result", {}).get("groups", [])
        except requests.RequestException as e:
            raise KapiparaApiError(f"Network error querying Kapipara groups: {e}") from e

    def get_schedule_raw(self, group_num: str = "5108") -> List[Dict[str, Any]]:
        """
        Retrieve raw schedule list from GET /schedule_public/{groupNum}.
        Returns raw list of lesson dictionaries.
        """
        url = f"{self.base_url}/schedule_public/{group_num}"
        try:
            resp = self.session.get(url, timeout=self.timeout, verify=False)
            if resp.status_code != 200:
                raise KapiparaApiError(f"Kapipara returned HTTP {resp.status_code}: {resp.text[:150]}")
            data = resp.json()
            if not isinstance(data, dict) or "result" not in data:
                raise KapiparaApiError(f"Invalid JSON envelope from Kapipara: {resp.text[:200]}")
            schedule = data.get("result", {}).get("schedule", [])
            if not isinstance(schedule, list):
                raise KapiparaApiError(f"Expected schedule list in Kapipara result, got {type(schedule)}")
            return schedule
        except requests.RequestException as e:
            raise KapiparaApiError(f"Network error querying Kapipara schedule for {group_num}: {e}") from e

    @staticmethod
    def parse_schedule_grid(raw_items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Convert flat list of Kapipara schedule items into a day-indexed grid:
        {'1': [...], '2': [...], ..., '6': [...]}
        Also augments each item with normalized keys and is_changed flag.
        """
        grid: Dict[str, List[Dict[str, Any]]] = {str(d): [] for d in range(1, 7)}
        for item in raw_items:
            day_str = str(item.get("daynum") if item.get("daynum") is not None else item.get("dayNum", "1")).strip()
            if day_str not in grid:
                grid[day_str] = []

            # Ensure item carries is_changed
            item_copy = dict(item)
            if "is_changed" not in item_copy:
                item_copy["is_changed"] = is_kapipara_change(item)

            grid[day_str].append(item_copy)

        return grid

    def get_schedule_grid(
        self,
        group_num: str = "5108",
        fallback_on_error: bool = True,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve schedule as day grid {'1': [...], ..., '6': [...]}.
        If Kapipara fails and fallback_on_error is True, transparently queries legacy KaiApiClient.
        """
        try:
            raw_items = self.get_schedule_raw(group_num=group_num)
            if raw_items:
                return self.parse_schedule_grid(raw_items)
            raise KapiparaApiError(f"Empty schedule list received for group {group_num}")
        except Exception as pe:
            logger.warning("Kapipara API error for group %s: %s", group_num, pe)
            if fallback_on_error and self.fallback_kai_client:
                logger.info("Engaging fallback to KaiApiClient for group %s", group_num)
                try:
                    group_id = self.fallback_kai_client.search_group_id(group_num)
                    legacy_schedule = self.fallback_kai_client.get_schedule(group_id)
                    return legacy_schedule
                except Exception as fe:
                    logger.error("Fallback to KaiApiClient also failed: %s", fe)
                    raise KapiparaApiError(f"Both Kapipara and KAI API failed: {pe} | fallback: {fe}") from fe
            raise

    def get_lessons_for_day(
        self,
        raw_schedule: Dict[str, List[Dict[str, Any]]],
        target_date: Optional[date] = None,
        subgroup: int = 2,
        strict_date: bool = True,
        deduplicate: bool = True,
    ) -> List[Lesson]:
        """
        Filter and deduplicate lessons for a specific calendar date and subgroup.
        """
        if target_date is None:
            target_date = date.today()

        day_num_str = str(target_date.weekday() + 1)
        raw_lessons = raw_schedule.get(day_num_str, [])
        parsed_lessons = [Lesson.from_raw_dict(item) for item in raw_lessons]

        filtered: List[Lesson] = []
        for lesson in parsed_lessons:
            if not lesson.is_for_subgroup(subgroup):
                continue

            if strict_date:
                if not lesson.is_active_on_date(target_date):
                    continue

            filtered.append(lesson)

        if deduplicate:
            filtered = merge_and_deduplicate_lessons(filtered)

        filtered.sort(key=lambda x: x.day_time)
        return filtered

    def get_week_schedule(
        self,
        raw_schedule: Dict[str, List[Dict[str, Any]]],
        target_monday: Optional[date] = None,
        subgroup: int = 2,
        strict_date: bool = True,
        deduplicate: bool = True,
    ) -> Dict[date, List[Lesson]]:
        """
        Return schedule mapped by calendar dates for the entire study week (Monday to Saturday).
        """
        if target_monday is None:
            today = date.today()
            target_monday = today - timedelta(days=today.weekday())

        week_schedule: Dict[date, List[Lesson]] = {}
        for day_offset in range(6):
            current_day = target_monday + timedelta(days=day_offset)
            lessons = self.get_lessons_for_day(
                raw_schedule,
                target_date=current_day,
                subgroup=subgroup,
                strict_date=strict_date,
                deduplicate=deduplicate,
            )
            week_schedule[current_day] = lessons

        return week_schedule
