import asyncio
import json
import logging
import os
import re
import mimetypes
import urllib.parse
from datetime import date, datetime, timedelta
from pathlib import Path
import secrets
from typing import Any, Dict, List, Optional

import httpx
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Query,
    Request,
    Security,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.config import settings
from database.connection import async_session, init_db
from database.crud import (
    create_task,
    get_or_create_subject,
    get_subjects,
    get_subject_by_id,
    get_tasks,
    get_task_by_id,
    update_task_status,
)
from database.models import Subject, Task
from services.bb_scraper import BlackboardScraper
from services.gemini_service import GeminiService, resolve_relative_deadline
from services.kai_api import (
    KaiApiClient,
    Lesson,
    get_week_parity,
    merge_and_deduplicate_lessons,
    KaiApiError,
)

logger = logging.getLogger("kai_assistant.api")

app = FastAPI(
    title="KAI Assistant 5108",
    description="Mobile PWA and REST API for KAI Student Assistant (IREF-TsT, Group 5108, Subgroup 2)",
    version="1.0.0",
)

# Restrict CORS to trusted origins & local tunnels
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
        "https://194-226-123-205.sslip.io",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|.*\.sslip\.io|.*\.lhr\.life|.*\.trycloudflare\.com)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security_bearer = HTTPBearer(auto_error=False)


async def verify_app_token(
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    x_app_token: Optional[str] = Header(None, alias="X-App-Token"),
    token: Optional[str] = Query(None, alias="token"),
):
    """
    Validate application authentication token.
    Supports Authorization: Bearer <token>, X-App-Token: <token>, and ?token=<token>
    """
    expected = settings.app_auth_token
    if not expected:
        return True

    supplied_token = None
    if auth and auth.credentials:
        supplied_token = auth.credentials.strip()
    elif x_app_token:
        supplied_token = x_app_token.strip()
    elif token:
        supplied_token = token.strip()

    if not supplied_token or not secrets.compare_digest(supplied_token, expected):
        raise HTTPException(
            status_code=401,
            detail="Неавторизованный доступ: неверный или отсутствующий токен авторизации",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True


api_router = APIRouter(prefix="/api", dependencies=[Depends(verify_app_token)])


@app.get("/api/health")
async def health_check():
    """Public health check endpoint."""
    return {"status": "ok", "app": "KAI Assistant 5108"}

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
REAL_SCHEDULE_FILE = Path(__file__).resolve().parent.parent / "real_schedule_5108.json"

# In-memory schedule cache to avoid spamming kai.ru
_schedule_cache: Dict[str, Any] = {
    "data": None,
    "timestamp": None,
}

_is_syncing_bb = False

RUSSIAN_WEEKDAYS = {
    1: "Понедельник",
    2: "Вторник",
    3: "Среда",
    4: "Четверг",
    5: "Пятница",
    6: "Суббота",
    7: "Воскресенье",
}


def parse_task_attachments(details: Optional[str]) -> List[Dict[str, str]]:
    """Extract guidelines and attachment URLs from task details."""
    if not details:
        return []
    attachments = []
    # Match pattern "📎 Name: URL"
    matches = re.findall(r"📎\s*([^:\n]+):\s*(https?://[^\s\)]+)", details)
    for name, url in matches:
        attachments.append({"name": name.strip(), "url": url.strip()})
    return attachments


def get_cached_raw_schedule() -> Dict[str, List[Dict[str, Any]]]:
    """Retrieve schedule from KAI API or fallback to local real_schedule_5108.json."""
    now = datetime.now()
    if (
        _schedule_cache["data"] is not None
        and _schedule_cache["timestamp"] is not None
        and (now - _schedule_cache["timestamp"]).total_seconds() < 1800
    ):
        return _schedule_cache["data"]

    client = KaiApiClient(base_url=settings.kai_api_url, timeout=6)
    try:
        group_id = client.search_group_id(settings.kai_group)
        raw_schedule = client.get_schedule(group_id)
        _schedule_cache["data"] = raw_schedule
        _schedule_cache["timestamp"] = now
        return raw_schedule
    except Exception as e:
        logger.warning("Could not fetch live schedule from KAI API (%s), using local backup.", e)
        if REAL_SCHEDULE_FILE.exists():
            try:
                with open(REAL_SCHEDULE_FILE, "r", encoding="utf-8") as f:
                    backup_data = json.load(f)
                    _schedule_cache["data"] = backup_data
                    _schedule_cache["timestamp"] = now
                    return backup_data
            except Exception as fe:
                logger.error("Failed to load backup schedule: %s", fe)
        raise HTTPException(status_code=503, detail=f"Schedule unavailable: {e}")


def match_subject_ids_for_discipline(discipl_name: str, subjects: List[Subject]) -> List[int]:
    """Match schedule discipline name with database Subject IDs to compute debt count."""
    disc_norm = re.sub(r"[^\w\s]", "", discipl_name.lower()).strip()
    words = [w for w in disc_norm.split() if len(w) > 2]
    matched = []
    for s in subjects:
        s_norm = re.sub(r"[^\w\s]", "", s.name.lower()).strip()
        if disc_norm in s_norm or s_norm in disc_norm:
            matched.append(s.id)
        elif any(w in s_norm for w in words):
            matched.append(s.id)
    return list(dict.fromkeys(matched))


@app.on_event("startup")
async def startup_event():
    await init_db()
    logger.info("FastAPI KAI Assistant 5108 started.")


# -------------------------------------------------------------
# REST API ENDPOINTS
# -------------------------------------------------------------

@api_router.get("/stats")
async def get_stats():
    """Overall semester progress stats."""
    async with async_session() as session:
        all_tasks = await get_tasks(session)
        subjects = await get_subjects(session)

    total_tasks = len(all_tasks)
    done_tasks = sum(1 for t in all_tasks if t.status == "done")
    todo_tasks = total_tasks - done_tasks
    progress_pct = round((done_tasks / total_tasks) * 100) if total_tasks > 0 else 0

    return {
        "total_tasks": total_tasks,
        "done_tasks": done_tasks,
        "todo_tasks": todo_tasks,
        "progress_percent": progress_pct,
        "total_subjects": len(subjects),
    }


@api_router.get("/subjects")
async def list_subjects():
    """Subjects list with task counts and progress percentages."""
    async with async_session() as session:
        subjects = await get_subjects(session)
        tasks = await get_tasks(session)

    stats_by_subj: Dict[int, Dict[str, int]] = {}
    for s in subjects:
        stats_by_subj[s.id] = {"total": 0, "done": 0, "todo": 0}

    for t in tasks:
        sid = t.subject_id
        if sid in stats_by_subj:
            stats_by_subj[sid]["total"] += 1
            if t.status == "done":
                stats_by_subj[sid]["done"] += 1
            else:
                stats_by_subj[sid]["todo"] += 1

    result = []
    for s in subjects:
        st = stats_by_subj[s.id]
        total = st["total"]
        done = st["done"]
        pct = round((done / total) * 100) if total > 0 else 0
        result.append({
            "id": s.id,
            "name": s.name,
            "teacher": s.teacher or "",
            "total_tasks": total,
            "done_tasks": done,
            "todo_tasks": st["todo"],
            "progress_percent": pct,
        })

    result.sort(key=lambda x: (-x["total_tasks"], x["name"]))
    return result


BB_COURSE_MAP = {
    "Введение в профессиональную деятельность": "https://bb.kai.ru/webapps/blackboard/execute/launcher?type=Course&id=_10403_1&url=",
    "Входное тестирование по иностранному языку 1 курс": "https://bb.kai.ru/webapps/blackboard/execute/launcher?type=Course&id=_17041_1&url=",
    "Высшая математика 1.1": "https://bb.kai.ru/webapps/blackboard/execute/launcher?type=Course&id=_15511_1&url=",
    "Высшая математика 1.2": "https://bb.kai.ru/webapps/blackboard/execute/launcher?type=Course&id=_15536_1&url=",
    "Инженерная графика - ИРЭТ": "https://bb.kai.ru/webapps/blackboard/execute/launcher?type=Course&id=_10392_1&url=",
    "Компьютерная графика": "https://bb.kai.ru/webapps/blackboard/execute/launcher?type=Course&id=_17086_1&url=",
    "Основы российской государственности": "https://bb.kai.ru/webapps/blackboard/execute/launcher?type=Course&id=_17754_1&url=",
    "ФИЛОСОФИЯ_3 раздела_зачет": "https://bb.kai.ru/webapps/blackboard/execute/launcher?type=Course&id=_18447_1&url=",
    "Физика 1": "https://bb.kai.ru/webapps/blackboard/execute/launcher?type=Course&id=_9332_1&url=",
    "Физическая культура и спорт (элективная дисциплина) 2026-2027": "https://bb.kai.ru/webapps/blackboard/execute/launcher?type=Course&id=_18442_1&url=",
    "Физическая культура и спорт 2026-2027": "https://bb.kai.ru/webapps/blackboard/execute/launcher?type=Course&id=_18441_1&url=",
}


@api_router.get("/tasks")
async def list_tasks(
    subject_id: Optional[int] = Query(None, description="Filter by subject ID"),
    status: Optional[str] = Query("all", description="Filter by status: todo, done, all"),
):
    """Tasks list with details, enhanced attachments with direct download URLs, and Blackboard course links."""
    filter_status = None if (not status or status == "all") else status.strip().lower()

    async with async_session() as session:
        tasks = await get_tasks(session, status=filter_status, subject_id=subject_id)

    response_items = []
    for t in tasks:
        subj_name = t.subject.name if t.subject else "Неизвестный предмет"
        attachments = parse_task_attachments(t.details)
        enhanced_attachments = []
        for i, att in enumerate(attachments):
            enhanced_attachments.append({
                "name": att["name"],
                "url": att["url"],
                "download_url": f"/api/tasks/{t.id}/download?idx={i}",
            })

        bb_course_url = BB_COURSE_MAP.get(
            subj_name,
            "https://bb.kai.ru/webapps/portal/execute/tabs/tabAction?tab_tab_group_id=_1_1"
        )

        response_items.append({
            "id": t.id,
            "subject_id": t.subject_id,
            "subject_name": subj_name,
            "title": t.title,
            "task_type": t.task_type,
            "deadline": t.deadline.isoformat() if t.deadline else None,
            "status": t.status,
            "source": t.source,
            "details": t.details,
            "file_url": t.file_url,
            "file_name": t.file_name,
            "external_url": t.external_url,
            "attachments": enhanced_attachments,
            "bb_course_url": bb_course_url,
            "has_files": bool(t.file_url or enhanced_attachments),
        })

    return response_items


@api_router.get("/tasks/{task_id}/download")
async def download_task_file(
    task_id: int,
    idx: int = Query(0, description="Attachment index if task has multiple files"),
):
    """Directly stream Blackboard attachment file to client using student's stored session."""
    async with async_session() as session:
        task = await get_task_by_id(session, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Задание не найдено")

    file_url = None
    target_name = None

    if task.file_url:
        file_url = task.file_url
        target_name = task.file_name
    else:
        attachments = parse_task_attachments(task.details)
        if attachments:
            if idx < 0 or idx >= len(attachments):
                idx = 0
            file_url = attachments[idx]["url"]
            target_name = attachments[idx]["name"]

    if not file_url:
        raise HTTPException(
            status_code=404,
            detail="К этой задаче не прикреплен отдельный файл в Blackboard"
        )

    # Load session cookies
    session_file = Path("data/bb_session.json")
    cookies = {}
    if session_file.exists():
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                s_data = json.load(f)
                cookies = {c["name"]: c["value"] for c in s_data.get("cookies", [])}
        except Exception as e:
            logger.warning("Error reading bb_session.json: %s", e)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://bb.kai.ru/",
    }

    try:
        async with httpx.AsyncClient(cookies=cookies, headers=headers, follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(file_url)

            # If expired or redirected to login, re-authenticate via Playwright
            if resp.status_code in (401, 403) or "login" in str(resp.url).lower():
                logger.info("Blackboard session expired during download. Re-authenticating...")
                try:
                    from playwright.async_api import async_playwright
                    scraper = BlackboardScraper()
                    async with async_playwright() as p:
                        b = await p.chromium.launch(headless=True)
                        ctx = await b.new_context()
                        page = await ctx.new_page()
                        await scraper.authenticate(ctx, page)
                        await b.close()

                    if session_file.exists():
                        with open(session_file, "r", encoding="utf-8") as f:
                            s_data = json.load(f)
                            cookies = {c["name"]: c["value"] for c in s_data.get("cookies", [])}

                    # Retry download with fresh cookies
                    async with httpx.AsyncClient(cookies=cookies, headers=headers, follow_redirects=True, timeout=30.0) as retry_client:
                        resp = await retry_client.get(file_url)
                except Exception as e:
                    logger.error("Failed to re-authenticate on Blackboard: %s", e)
    except Exception as e:
        logger.error("Download error from Blackboard: %s", e)
        raise HTTPException(status_code=502, detail=f"Ошибка соединения с Blackboard: {e}")

    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Не удалось скачать файл с Blackboard (HTTP {resp.status_code})"
        )

    content_type = resp.headers.get("content-type", "application/octet-stream")

    # Determine original filename
    filename = None
    cd = resp.headers.get("content-disposition")
    if cd:
        m_utf = re.search(r"filename\*=UTF-8''([^;]+)", cd, re.IGNORECASE)
        if m_utf:
            filename = urllib.parse.unquote(m_utf.group(1))
        else:
            m = re.search(r'filename="?([^";]+)"?', cd)
            if m:
                filename = m.group(1).strip()

    if not filename or filename.startswith("xid-"):
        # Extract from redirect URL path (e.g. .../Тема_1.pdf)
        path_leaf = urllib.parse.unquote(resp.url.path.split("/")[-1])
        if path_leaf and "." in path_leaf and not path_leaf.startswith("xid-"):
            filename = path_leaf

    if not filename or "." not in filename:
        att_name = (target_name or "file").strip()
        if "." not in att_name:
            ext = mimetypes.guess_extension(content_type) or ".bin"
            filename = f"{att_name}{ext}"
        else:
            filename = att_name

    # Build safe ASCII-only fallback for older clients and percent-encoded UTF-8 for modern browsers
    parts = filename.rsplit(".", 1)
    ext = f".{parts[1]}" if len(parts) > 1 and len(parts[1]) <= 6 else ""
    ascii_chars = [c for c in parts[0] if c.isascii() and (c.isalnum() or c in "-_")]
    base = "".join(ascii_chars).strip("-_")
    if not base:
        base = f"kai_task_{task_id}_file"
    ascii_fallback = f"{base}{ext}"

    quoted_name = urllib.parse.quote(filename)
    clean_media_type = content_type.split(";")[0].strip() or "application/octet-stream"

    resp_headers = {
        "Content-Disposition": f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{quoted_name}',
        "Access-Control-Expose-Headers": "Content-Disposition",
    }

    return Response(content=resp.content, media_type=clean_media_type, headers=resp_headers)


@api_router.post("/tasks/{task_id}/toggle")
async def toggle_task_status(task_id: int):
    """Toggle task status between todo and done."""
    async with async_session() as session:
        task = await get_task_by_id(session, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        new_status = "done" if task.status == "todo" else "todo"
        updated = await update_task_status(session, task_id=task_id, status=new_status)

    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update task")

    return {
        "id": updated.id,
        "subject_id": updated.subject_id,
        "subject_name": updated.subject.name if updated.subject else "",
        "title": updated.title,
        "task_type": updated.task_type,
        "status": updated.status,
        "attachments": parse_task_attachments(updated.details),
    }


@api_router.get("/schedule")
async def get_schedule(
    day: Optional[int] = Query(None, description="Weekday 1..6 (1=Mon, 6=Sat)"),
    week: Optional[str] = Query(None, description="Week parity: even/odd or чет/нечет"),
):
    """Schedule for group 5108 (2nd subgroup) for a specific day."""
    today = date.today()
    current_parity = get_week_parity(today)

    if day is None:
        weekday = today.weekday() + 1
        day = 1 if weekday > 6 else weekday

    if not week:
        target_parity = current_parity
    else:
        week_lower = week.lower().strip()
        if "even" in week_lower or "чет" in week_lower and "неч" not in week_lower:
            target_parity = "чет"
        else:
            target_parity = "нечет"

    raw_schedule = get_cached_raw_schedule()
    day_lessons_raw = raw_schedule.get(str(day), [])

    parsed = [Lesson.from_raw_dict(item) for item in day_lessons_raw]
    filtered = [
        l for l in parsed
        if l.is_for_subgroup(settings.kai_subgroup) and l.is_active_on_parity(target_parity)
    ]
    merged = merge_and_deduplicate_lessons(filtered)

    # Attach pending tasks count for each lesson
    async with async_session() as session:
        subjects = await get_subjects(session)
        todo_tasks = await get_tasks(session, status="todo")

    subj_todo_counts = {}
    for t in todo_tasks:
        subj_todo_counts[t.subject_id] = subj_todo_counts.get(t.subject_id, 0) + 1

    lessons_result = []
    for l in merged:
        matched_sids = match_subject_ids_for_discipline(l.discipl_name, subjects)
        todo_count = sum(subj_todo_counts.get(sid, 0) for sid in matched_sids)

        lessons_result.append({
            "discipl_name": l.discipl_name,
            "discipl_type": l.discipl_type,
            "day_num": l.day_num,
            "day_time": l.day_time,
            "day_date": l.day_date,
            "aud_num": l.aud_num,
            "build_num": l.build_num,
            "prepod_name": l.prepod_name,
            "potok": l.potok,
            "org_unit_name": l.org_unit_name,
            "todo_tasks_count": todo_count,
        })

    return {
        "day": day,
        "day_name": RUSSIAN_WEEKDAYS.get(day, "День"),
        "week_parity": target_parity,
        "is_current_week": (target_parity == current_parity),
        "lessons": lessons_result,
    }


@api_router.get("/schedule/week")
async def get_schedule_week(
    week: Optional[str] = Query(None, description="Week parity: even/odd or чет/нечет")
):
    """Full week schedule grid (Monday to Saturday)."""
    today = date.today()
    current_parity = get_week_parity(today)

    if not week:
        target_parity = current_parity
    else:
        week_lower = week.lower().strip()
        if "even" in week_lower or "чет" in week_lower and "неч" not in week_lower:
            target_parity = "чет"
        else:
            target_parity = "нечет"

    raw_schedule = get_cached_raw_schedule()

    async with async_session() as session:
        subjects = await get_subjects(session)
        todo_tasks = await get_tasks(session, status="todo")

    subj_todo_counts = {}
    for t in todo_tasks:
        subj_todo_counts[t.subject_id] = subj_todo_counts.get(t.subject_id, 0) + 1

    days_result = {}
    for day_num in range(1, 7):
        raw_lessons = raw_schedule.get(str(day_num), [])
        parsed = [Lesson.from_raw_dict(item) for item in raw_lessons]
        filtered = [
            l for l in parsed
            if l.is_for_subgroup(settings.kai_subgroup) and l.is_active_on_parity(target_parity)
        ]
        merged = merge_and_deduplicate_lessons(filtered)

        day_lessons = []
        for l in merged:
            matched_sids = match_subject_ids_for_discipline(l.discipl_name, subjects)
            todo_count = sum(subj_todo_counts.get(sid, 0) for sid in matched_sids)
            day_lessons.append({
                "discipl_name": l.discipl_name,
                "discipl_type": l.discipl_type,
                "day_num": l.day_num,
                "day_time": l.day_time,
                "day_date": l.day_date,
                "aud_num": l.aud_num,
                "build_num": l.build_num,
                "prepod_name": l.prepod_name,
                "potok": l.potok,
                "org_unit_name": l.org_unit_name,
                "todo_tasks_count": todo_count,
            })

        days_result[str(day_num)] = {
            "day_num": day_num,
            "day_name": RUSSIAN_WEEKDAYS.get(day_num, ""),
            "lessons": day_lessons,
        }

    return {
        "week_parity": target_parity,
        "is_current_week": (target_parity == current_parity),
        "days": days_result,
    }


async def _run_bb_sync_worker():
    """Background task runner for Blackboard synchronization."""
    global _is_syncing_bb
    try:
        scraper = BlackboardScraper()
        res = await scraper.run_sync()
        logger.info(
            "Blackboard background sync completed. Auth: %s, created: %d, skipped: %d",
            res.is_authenticated, res.tasks_created, res.tasks_skipped
        )
    except Exception as e:
        logger.exception("Blackboard background sync error: %s", e)
    finally:
        _is_syncing_bb = False


@api_router.post("/sync-bb")
async def trigger_bb_sync(background_tasks: BackgroundTasks):
    """Trigger background synchronization with Blackboard."""
    global _is_syncing_bb
    if _is_syncing_bb:
        return {"status": "already_running", "message": "Синхронизация с Blackboard уже выполняется."}

    _is_syncing_bb = True
    background_tasks.add_task(_run_bb_sync_worker)
    return {
        "status": "started",
        "message": "Синхронизация с Blackboard запущена в фоновом режиме."
    }


# -------------------------------------------------------------
# GOOGLE GEMINI AI ENDPOINTS
# -------------------------------------------------------------

class AiParseTaskRequest(BaseModel):
    text: str


class CreateTaskRequest(BaseModel):
    subject_name: str
    title: str
    task_type: str = "задание"
    deadline: Optional[str] = None  # ISO format string or raw phrase
    deadline_raw: Optional[str] = None
    requirements: Optional[str] = None
    details: Optional[str] = None
    source: str = "manual_ai"


_task_summaries_cache: Dict[int, Dict[str, Any]] = {}


@api_router.post("/ai/parse-task")
async def ai_parse_task(req: AiParseTaskRequest):
    """Recognize task from free-form natural language text using Google Gemini AI (preview only, does not save to DB)."""
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Текст задачи не может быть пустым")

    gemini_svc = GeminiService()
    if not gemini_svc.is_available():
        raise HTTPException(
            status_code=503,
            detail="Google Gemini API не настроен. Укажите GEMINI_API_KEY в файле .env"
        )

    # 1. Retrieve registered academic disciplines
    async with async_session() as session:
        db_subjects = await get_subjects(session)
        subj_names = [s.name for s in db_subjects]

    if not subj_names:
        subj_names = ["Общие задачи"]

    try:
        parsed = gemini_svc.parse_natural_task(req.text, subj_names)
    except Exception as e:
        logger.error("Gemini parse_natural_task error: %s", e)
        raise HTTPException(status_code=502, detail=f"Ошибка Gemini AI: {e}")

    subj_name = parsed.get("subject") or (subj_names[0] if subj_names else "Общие задачи")
    title = parsed.get("title") or req.text.strip()[:60]
    task_type = parsed.get("task_type") or "задание"
    deadline_raw = parsed.get("deadline_raw")
    deadline_iso = parsed.get("deadline_iso")
    requirements = parsed.get("requirements")

    return {
        "subject_name": subj_name,
        "title": title,
        "task_type": task_type,
        "deadline_raw": deadline_raw,
        "deadline_iso": deadline_iso,
        "requirements": requirements,
        "original_text": req.text.strip(),
    }


@api_router.post("/tasks")
async def create_new_task(req: CreateTaskRequest):
    """Persist confirmed task to SQLite database."""
    if not req.title or not req.title.strip():
        raise HTTPException(status_code=400, detail="Название задачи не может быть пустым")
    if not req.subject_name or not req.subject_name.strip():
        raise HTTPException(status_code=400, detail="Название предмета не может быть пустым")

    deadline_dt: Optional[datetime] = None
    if req.deadline:
        try:
            deadline_dt = datetime.fromisoformat(req.deadline)
        except Exception:
            deadline_dt = resolve_relative_deadline(req.deadline)
    elif req.deadline_raw:
        deadline_dt = resolve_relative_deadline(req.deadline_raw)

    details = req.details or ""
    if not details:
        details_parts = []
        if req.deadline_raw:
            details_parts.append(f"⏰ Срок: {req.deadline_raw}")
        elif deadline_dt:
            details_parts.append(f"⏰ Срок: {deadline_dt.strftime('%d.%m.%Y %H:%M')}")
        if req.requirements:
            details_parts.append(f"📝 Требования: {req.requirements}")
        details_parts.append("Источник: Создано через Gemini AI")
        details = "\n\n".join(details_parts)

    async with async_session() as session:
        subject = await get_or_create_subject(session, name=req.subject_name.strip())
        new_task = await create_task(
            session=session,
            subject_id=subject.id,
            title=req.title.strip(),
            task_type=req.task_type.strip(),
            deadline=deadline_dt,
            status="todo",
            source=req.source,
            details=details,
        )

    return {
        "id": new_task.id,
        "subject_id": new_task.subject_id,
        "subject_name": subject.name,
        "title": new_task.title,
        "task_type": new_task.task_type,
        "deadline": new_task.deadline.isoformat() if new_task.deadline else None,
        "deadline_raw": req.deadline_raw,
        "status": new_task.status,
        "source": new_task.source,
        "details": new_task.details,
    }


@api_router.post("/ai/summarize-task/{task_id}")
async def ai_summarize_task(task_id: int):
    """Generate concise student lab cheat-sheet using Google Gemini AI."""
    if task_id in _task_summaries_cache:
        return _task_summaries_cache[task_id]

    async with async_session() as session:
        task = await get_task_by_id(session, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Задание не найдено")

    gemini_svc = GeminiService()
    if not gemini_svc.is_available():
        raise HTTPException(
            status_code=503,
            detail="Google Gemini API не настроен. Укажите GEMINI_API_KEY в файле .env"
        )

    try:
        summary_data = gemini_svc.summarize_lab_work(
            title=task.title,
            details=task.details or ""
        )
        _task_summaries_cache[task_id] = summary_data
        return summary_data
    except Exception as e:
        logger.error("Gemini summarize_lab_work error: %s", e)
        raise HTTPException(status_code=502, detail=f"Ошибка Gemini AI: {e}")


app.include_router(api_router)


# -------------------------------------------------------------
# STATIC FILES AND PWA ROUTES
# -------------------------------------------------------------

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


@app.get("/")
@app.head("/")
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file), headers=NO_CACHE_HEADERS)
    return JSONResponse({"message": "KAI Assistant API running. Static files not yet created."})


@app.get("/manifest.json")
async def serve_manifest():
    manifest_file = STATIC_DIR / "manifest.json"
    if manifest_file.exists():
        return FileResponse(str(manifest_file), media_type="application/manifest+json", headers=NO_CACHE_HEADERS)
    return JSONResponse({"name": "КАИ Ассистент 5108"})


@app.get("/sw.js")
async def serve_service_worker():
    sw_file = STATIC_DIR / "sw.js"
    if sw_file.exists():
        return FileResponse(str(sw_file), media_type="application/javascript", headers=NO_CACHE_HEADERS)
    return JSONResponse({"status": "no_sw"})
