"""
KAI Schedule API integration module.
Implements real HTTP interactions with KAI schedule portal (https://kai.ru/web/studentu/raspisanie1),
subgroup filtering across real fields, collision deduplication, and week parity / date matching.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional
import requests
import urllib3
from pydantic import BaseModel, Field

# Disable SSL verification warnings caused by Russian digital ministry root certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class KaiApiError(Exception):
    """Exception raised when KAI API request fails or returns an error."""
    pass


# Subgroup detection patterns
SUBGROUP_1_PATTERN = re.compile(
    r"(?<![a-zA-Zа-яА-Я0-9№])1\s*(?:п/?г|п\.г\.|подгр(?:упп[а-я]*)?)|(?<=\()1(?=\))|(?<=\()1\s*п/?г(?=\))",
    re.IGNORECASE
)
SUBGROUP_2_PATTERN = re.compile(
    r"(?<![a-zA-Zа-яА-Я0-9№])2\s*(?:п/?г|п\.г\.|подгр(?:упп[а-я]*)?)|(?<=\()2(?=\))|(?<=\()2\s*п/?г(?=\))",
    re.IGNORECASE
)


def format_short_teacher(full_name: str) -> str:
    """Format 'ФАМИЛИЯ ИМЯ ОТЧЕСТВО' into 'Фамилия И. О.'"""
    parts = full_name.strip().split()
    if len(parts) >= 3:
        return f"{parts[0].capitalize()} {parts[1][0].upper()}. {parts[2][0].upper()}."
    elif len(parts) == 2:
        return f"{parts[0].capitalize()} {parts[1][0].upper()}."
    return full_name.strip().title()


class Lesson(BaseModel):
    """Normalized lesson representation from KAI API / Kapipara API."""
    discipl_name: str = Field(..., description="Название дисциплины")
    discipl_type: str = Field("", description="Тип занятия (лек, пр, л.р., лаб)")
    day_num: int = Field(..., description="День недели (1 - Пн, 6 - Сб, 7 - Вс)")
    day_time: str = Field(..., description="Время начала пары (например 08:00)")
    day_date: str = Field("", description="Периодичность, даты проведения или четность")
    aud_num: str = Field("", description="Номер аудитории")
    build_num: str = Field("", description="Номер здания/корпуса")
    prepod_name: str = Field("", description="ФИО преподавателя")
    potok: str = Field("", description="Поток или подгруппа")
    org_unit_name: str = Field("", description="Кафедра / подразделение")
    is_changed: bool = Field(False, description="Флаг оперативной замены или переноса пары")

    @classmethod
    def from_raw_dict(cls, data: Dict[str, Any]) -> "Lesson":
        """Build a Lesson instance from raw KAI API or Kapipara JSON dictionary."""
        day_num_val = data.get("dayNum") if data.get("dayNum") is not None else data.get("daynum", "1")
        try:
            day_num = int(day_num_val)
        except (ValueError, TypeError):
            day_num = 1

        discipl_name = str(data.get("disciplName") or data.get("disciplname") or "").strip()
        discipl_type = str(data.get("disciplType") or data.get("discipltype") or "").strip()
        day_time = str(data.get("dayTime") or data.get("daytime") or "").strip()
        day_date = str(data.get("dayDate") or data.get("daydate") or "").strip()
        aud_num = str(data.get("audNum") or data.get("auditory") or "").strip()
        build_num = str(data.get("buildNum") or data.get("building") or "").strip()
        prepod_name = str(data.get("prepodName") or data.get("prepodfio") or "").strip()
        potok = str(data.get("potok") or "").strip()
        org_unit_name = str(data.get("orgUnitName") or data.get("kafTitle") or "").strip()

        is_changed = bool(data.get("is_changed") or data.get("isChanged"))
        if not is_changed:
            status = str(data.get("status") or "").lower().strip()
            if status in {"change", "replace", "transfer", "замена", "перенос"}:
                is_changed = True
            elif any(k in f"{discipl_name} {discipl_type} {day_date}".lower() for k in ["замен", "перенос"]):
                is_changed = True
            else:
                # Detect isolated single-day rescheduled classes in Kapipara
                dates = re.findall(r"\b\d{1,2}\.\d{1,2}\b", day_date)
                if len(dates) == 1 and "/" not in day_date:
                    is_changed = True

        return cls(
            discipl_name=discipl_name,
            discipl_type=discipl_type,
            day_num=day_num,
            day_time=day_time,
            day_date=day_date,
            aud_num=aud_num,
            build_num=build_num,
            prepod_name=prepod_name,
            potok=potok,
            org_unit_name=org_unit_name,
            is_changed=is_changed,
        )

    def is_for_subgroup(self, subgroup: int = 2) -> bool:
        """
        Check if lesson is applicable for target subgroup.
        Checks fields: disciplName, dayDate, prepodName, audNum, potok, disciplType.
        Rules:
        - If explicitly marked for subgroup 1 -> discard for subgroup 2.
        - If explicitly marked for subgroup 2 -> keep for subgroup 2.
        - If no subgroup marker (common stream/lecture) -> keep for both.
        """
        search_blob = f"{self.discipl_name} {self.day_date} {self.prepod_name} {self.aud_num} {self.potok} {self.discipl_type}"

        has_sg1 = bool(SUBGROUP_1_PATTERN.search(search_blob))
        has_sg2 = bool(SUBGROUP_2_PATTERN.search(search_blob))

        if subgroup == 2:
            if has_sg1 and not has_sg2:
                return False
            return True
        elif subgroup == 1:
            if has_sg2 and not has_sg1:
                return False
            return True

        return True

    def is_active_on_parity(self, parity: str) -> bool:
        """
        Check if lesson occurs on the specified week parity ('чет' or 'нечет').
        Supports explicit parity tags and lists of calendar dates (dd.mm).
        """
        raw_parity = self.day_date.lower().strip()
        if not raw_parity:
            return True

        if "/" in raw_parity or ("чет" in raw_parity and "неч" in raw_parity):
            return True

        if "неч" in raw_parity or "чет" in raw_parity:
            if parity == "нечет":
                return "неч" in raw_parity
            elif parity == "чет":
                return "чет" in raw_parity and "неч" not in raw_parity

        # If day_date has specific dates, verify if any date matches the requested parity
        specific_dates = re.findall(r"\b(\d{1,2})\.(\d{1,2})\b", raw_parity)
        if specific_dates:
            curr_year = date.today().year
            for d_str, m_str in specific_dates:
                m, d = int(m_str), int(d_str)
                yr = curr_year if m >= 8 else (curr_year + 1)
                try:
                    dt = date(yr, m, d)
                    if get_week_parity(dt) == parity:
                        return True
                except ValueError:
                    pass
            return False

        return True

    def is_active_on_date(self, target_date: date) -> bool:
        """
        Check if lesson occurs on a specific calendar date.
        Supports:
        - Specific dates list (e.g. '02.09 16.09 30.09 ...')
        - Parity terms ('чет', 'неч', 'чет/неч')
        - Empty string (every week)
        """
        raw_date = self.day_date.strip()
        if not raw_date:
            return True

        specific_dates = set(re.findall(r"\b\d{1,2}\.\d{1,2}\b", raw_date))
        if specific_dates:
            target_str = f"{target_date.day:02d}.{target_date.month:02d}"
            target_alt = f"{target_date.day}.{target_date.month:02d}"
            return (target_str in specific_dates) or (target_alt in specific_dates)

        parity = get_week_parity(target_date)
        return self.is_active_on_parity(parity)


def merge_and_deduplicate_lessons(lessons: List[Lesson]) -> List[Lesson]:
    """
    Merge colliding lessons scheduled at the exact same start time:
    - Same room + same subject + multiple teachers -> single card with 'Teacher1 / Teacher2'
    - Different rooms + parallel subgroup subjects -> single card with '210 (Subj1) / 227 (Subj2)'
    """
    if not lessons:
        return []

    # Group lessons by start time
    by_time: Dict[str, List[Lesson]] = {}
    for l in lessons:
        by_time.setdefault(l.day_time, []).append(l)

    merged: List[Lesson] = []
    for time_slot, slot_lessons in by_time.items():
        if len(slot_lessons) == 1:
            merged.append(slot_lessons[0])
            continue

        first_disc = slot_lessons[0].discipl_name.strip().lower()
        same_discipline = all(l.discipl_name.strip().lower() == first_disc for l in slot_lessons)

        slot_changed = any(l.is_changed for l in slot_lessons)

        if same_discipline:
            # Case 1: Same subject in the same room with multiple teachers (e.g. physics lab)
            teachers = [format_short_teacher(l.prepod_name) for l in slot_lessons if l.prepod_name]
            unique_teachers = list(dict.fromkeys(teachers))
            merged_teacher = " / ".join(unique_teachers) if unique_teachers else slot_lessons[0].prepod_name

            base_lesson = slot_lessons[0]
            merged_lesson = base_lesson.model_copy(update={"prepod_name": merged_teacher, "is_changed": slot_changed})
            merged.append(merged_lesson)
        else:
            # Case 2: Parallel subgroup disciplines in different rooms (e.g. engineering vs computer graphics)
            disc_names = [l.discipl_name for l in slot_lessons]
            combined_discipl = " / ".join(dict.fromkeys(disc_names))

            aud_parts = []
            for l in slot_lessons:
                short_disc = l.discipl_name.split()[0]
                aud_parts.append(f"{l.aud_num} ({short_disc})")
            combined_aud = " / ".join(aud_parts)

            teachers = [format_short_teacher(l.prepod_name) for l in slot_lessons if l.prepod_name]
            unique_teachers = list(dict.fromkeys(teachers))
            combined_teacher = " / ".join(unique_teachers)

            build_nums = list(dict.fromkeys([l.build_num for l in slot_lessons if l.build_num]))
            combined_build = " / ".join(build_nums) if build_nums else slot_lessons[0].build_num

            types = list(dict.fromkeys([l.discipl_type for l in slot_lessons if l.discipl_type]))
            combined_type = " / ".join(types) if types else slot_lessons[0].discipl_type

            combined_lesson = Lesson(
                discipl_name=combined_discipl,
                discipl_type=combined_type,
                day_num=slot_lessons[0].day_num,
                day_time=time_slot,
                day_date=slot_lessons[0].day_date,
                aud_num=combined_aud,
                build_num=combined_build,
                prepod_name=combined_teacher,
                potok=slot_lessons[0].potok,
                org_unit_name=slot_lessons[0].org_unit_name,
                is_changed=slot_changed,
            )
            merged.append(combined_lesson)

    merged.sort(key=lambda x: x.day_time)
    return merged


def get_week_parity(target_date: Optional[date] = None) -> str:
    """
    Calculate week parity according to ISO calendar (SPEC.md section 1.4).
    Returns 'чет' for even ISO week numbers and 'нечет' for odd ones.
    """
    if target_date is None:
        target_date = date.today()

    iso_week = target_date.isocalendar()[1]
    return "чет" if iso_week % 2 == 0 else "нечет"


def is_even_week(target_date: Optional[date] = None) -> bool:
    """Returns True if ISO week is even."""
    return get_week_parity(target_date) == "чет"


class KaiApiClient:
    """Client for fetching and parsing KAI schedule from real portal."""

    BASE_URL = "https://kai.ru/web/studentu/raspisanie1"

    def __init__(self, base_url: str = BASE_URL, timeout: int = 15):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        })

    def search_group_id(self, group_name: str = "5108") -> str:
        """
        Search for groupId via GET request to https://kai.ru/web/studentu/raspisanie1.
        Raises KaiApiError if network fails or group is not found.
        """
        params = {
            "p_p_id": "pubStudentSchedule_WAR_publicStudentSchedule10",
            "p_p_lifecycle": "2",
            "p_p_resource_id": "getGroupsURL",
            "query": str(group_name),
        }

        try:
            resp = self.session.get(
                self.base_url,
                params=params,
                verify=False,
                timeout=self.timeout
            )
        except requests.RequestException as exc:
            raise KaiApiError(f"Сетевая ошибка при поиске группы '{group_name}': {exc}") from exc

        if resp.status_code != 200:
            raise KaiApiError(
                f"Ошибка сервера КАИ при поиске группы '{group_name}': HTTP {resp.status_code}"
            )

        try:
            data = resp.json()
        except Exception as exc:
            raise KaiApiError(f"Сервер КАИ вернул некорректный ответ (не JSON): {resp.text[:200]}") from exc

        if not isinstance(data, list) or len(data) == 0:
            raise KaiApiError(f"Группа '{group_name}' не найдена в системе расписания КАИ.")

        for item in data:
            if str(item.get("group", "")).strip() == str(group_name):
                return str(item.get("id"))

        first_id = data[0].get("id")
        if first_id:
            return str(first_id)

        raise KaiApiError(f"Не удалось извлечь id для группы '{group_name}' из ответа: {data}")

    def get_schedule(self, group_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve raw schedule grid via POST request to https://kai.ru/web/studentu/raspisanie1.
        Raises KaiApiError if network fails or schedule is empty.
        """
        params = {
            "p_p_id": "pubStudentSchedule_WAR_publicStudentSchedule10",
            "p_p_lifecycle": "2",
            "p_p_resource_id": "schedule",
        }
        data = {
            "groupId": str(group_id),
        }

        try:
            resp = self.session.post(
                self.base_url,
                params=params,
                data=data,
                verify=False,
                timeout=self.timeout
            )
        except requests.RequestException as exc:
            raise KaiApiError(f"Сетевая ошибка при получении расписания для groupId={group_id}: {exc}") from exc

        if resp.status_code != 200:
            raise KaiApiError(
                f"Ошибка сервера КАИ при получении расписания для groupId={group_id}: HTTP {resp.status_code}"
            )

        try:
            result = resp.json()
        except Exception as exc:
            raise KaiApiError(f"Сервер КАИ вернул некорректный JSON расписания: {resp.text[:200]}") from exc

        if not isinstance(result, dict) or not any(k in result for k in ["1", "2", "3", "4", "5", "6"]):
            raise KaiApiError(f"Получено пустое или невалидное расписание для groupId={group_id}: {result}")

        return result

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
        Return schedule mapped by calendar dates for the entire Monday-Saturday study week.
        """
        from datetime import timedelta

        if target_monday is None:
            today = date.today()
            target_monday = today - timedelta(days=today.weekday())

        week_schedule: Dict[date, List[Lesson]] = {}
        for day_offset in range(6):  # Monday to Saturday
            current_day = target_monday + timedelta(days=day_offset)
            lessons = self.get_lessons_for_day(
                raw_schedule,
                target_date=current_day,
                subgroup=subgroup,
                strict_date=strict_date,
                deduplicate=deduplicate
            )
            week_schedule[current_day] = lessons

        return week_schedule
