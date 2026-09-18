import asyncio
import json
import logging
import os
import re
import mimetypes
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import secrets
from typing import Any, Dict, List, Optional

import httpx
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Cookie,
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
    create_task_attachment,
    get_or_create_subject,
    get_or_create_user,
    get_subjects,
    get_subject_by_id,
    get_tasks,
    get_task_by_id,
    get_task_by_id_and_owner,
    get_task_attachment,
    get_task_attachments,
    get_user_by_id,
    update_task_status,
)
from database.models import Subject, Task, TaskAttachment, User
from services.auth_service import (
    AuthenticatedUser,
    create_user_token,
    decode_user_token,
    get_system_default_user,
)
from services.bb_scraper import BlackboardScraper
from services.gemini_service import (
    GeminiService,
    resolve_relative_deadline,
    AiErrorCategory,
    AiServiceError,
    classify_ai_error,
    get_ai_error_ui_info,
)
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

STORAGE_DIR = Path(__file__).resolve().parent.parent / "data" / "attachments"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

SYNC_STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "sync_state.json"


def get_last_successful_sync() -> Optional[str]:
    """Retrieve ISO timestamp of the last successful sync operation."""
    if SYNC_STATE_FILE.exists():
        try:
            with open(SYNC_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("last_successful_sync")
        except Exception as e:
            logger.warning("Could not read sync state: %s", e)
    return None


def record_successful_sync(source: str = "schedule") -> str:
    """Record successful sync timestamp and persist to sync_state.json."""
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        SYNC_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SYNC_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_successful_sync": now_iso, "source": source}, f, indent=2)
    except Exception as e:
        logger.warning("Could not persist sync state: %s", e)
    return now_iso

security_bearer = HTTPBearer(auto_error=False)


async def verify_app_token(
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    x_app_token: Optional[str] = Header(None, alias="X-App-Token"),
    x_user_token: Optional[str] = Header(None, alias="X-User-Token"),
    session_cookie: Optional[str] = Cookie(None, alias="kai_app_auth_token"),
    user_cookie: Optional[str] = Cookie(None, alias="kai_user_token"),
    x_session_expired: Optional[str] = Header(None, alias="X-Session-Expired"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
):
    """
    Validate application and user authentication.
    Decouples Application Gateway Authentication from User Identity Authentication.

    Authentication hierarchy:
    1. Check for explicit session expiration (X-Session-Expired).
    2. Check for explicit 'expired' token markers.
    3. User Token (JWT HMAC-SHA256 with 2 dots):
       - If Authorization header, X-User-Token, or cookie contains a user token,
         cryptographically verify signature, claims, and expiration via decode_user_token.
       - Sets request.state.current_user to verified AuthenticatedUser.
    4. App Gateway Token (X-App-Token or Bearer matching settings.app_auth_token):
       - Validates client authorization to the API gateway.
       - If an additional user token is supplied, binds that user.
       - If X-User-Id is provided under trusted gateway auth, constructs AuthenticatedUser(id=X-User-Id).
       - Otherwise defaults to system default student user (student_5108).
    5. Tokens passed in query parameters (?token=...) are strictly rejected.
    """
    expected = settings.app_auth_token

    # 1. Check for explicit session expiration
    if x_session_expired and x_session_expired.strip().lower() in ("true", "1", "yes"):
        raise HTTPException(
            status_code=401,
            detail="Срок действия авторизации истек: требуется повторный вход",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token", error_description="The access token expired"'},
        )

    # 2. Extract credential candidates (header or cookie only, NEVER query param)
    bearer_token = auth.credentials.strip() if (auth and auth.credentials) else None
    header_app_token = x_app_token.strip() if x_app_token else None
    header_user_token = x_user_token.strip() if x_user_token else None
    cookie_user_token = user_cookie.strip() if user_cookie else None
    cookie_app_token = session_cookie.strip() if session_cookie else None

    # Primary token candidate
    primary_token = bearer_token or header_user_token or header_app_token or cookie_user_token or cookie_app_token

    # 3. Check for expired token marker
    if primary_token and (primary_token.lower() == "expired" or primary_token.lower().startswith("expired_")):
        raise HTTPException(
            status_code=401,
            detail="Срок действия авторизационного токена истек: требуется повторный вход",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token", error_description="The access token expired"'},
        )

    if not primary_token:
        raise HTTPException(
            status_code=401,
            detail="Неавторизованный доступ: отсутствует токен авторизации",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 4. Check if primary token is a signed User Token (JWT format: 3 dot-separated parts)
    if primary_token.count(".") == 2:
        verified_user = decode_user_token(primary_token)
        request.state.current_user = verified_user
        request.state.auth_type = "user_token"
        return True

    # 5. Check if secondary user token is present (e.g. Bearer was app_token, but header_user_token or cookie has JWT)
    secondary_user_token = header_user_token or cookie_user_token
    verified_user_from_secondary = None
    if secondary_user_token and secondary_user_token.count(".") == 2:
        verified_user_from_secondary = decode_user_token(secondary_user_token)

    # 6. Validate against App Gateway Token
    is_app_token_valid = False
    if expected:
        candidates = [t for t in (bearer_token, header_app_token, cookie_app_token) if t]
        for cand in candidates:
            if secrets.compare_digest(cand, expected):
                is_app_token_valid = True
                break
    else:
        # If no expected app_token configured, gateway auth passes
        is_app_token_valid = True

    if not is_app_token_valid:
        raise HTTPException(
            status_code=401,
            detail="Неавторизованный доступ: неверный или отсутствующий токен авторизации",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 7. Gateway auth succeeded: resolve user identity
    if verified_user_from_secondary:
        request.state.current_user = verified_user_from_secondary
        request.state.auth_type = "user_token"
    elif x_user_id and x_user_id.strip():
        # Trusted gateway caller specifying user identity
        uid = x_user_id.strip()
        request.state.current_user = AuthenticatedUser(
            id=uid,
            username=uid,
            role="student",
            group_num="5108",
            subgroup=2,
        )
        request.state.auth_type = "gateway_user"
    else:
        # Default system student
        request.state.current_user = get_system_default_user()
        request.state.auth_type = "gateway_default"

    return True


def get_current_user(request: Request) -> AuthenticatedUser:
    """Dependency / helper to retrieve the verified AuthenticatedUser from request.state."""
    user = getattr(request.state, "current_user", None)
    if isinstance(user, AuthenticatedUser):
        return user
    if isinstance(user, str) and user:
        return AuthenticatedUser(id=user, username=user)
    return get_system_default_user()


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
        record_successful_sync(source="kai_schedule_api")
        return raw_schedule
    except Exception as e:
        logger.warning("Could not fetch live schedule from KAI API (%s), using local backup.", e)
        if REAL_SCHEDULE_FILE.exists():
            try:
                with open(REAL_SCHEDULE_FILE, "r", encoding="utf-8") as f:
                    backup_data = json.load(f)
                    _schedule_cache["data"] = backup_data
                    _schedule_cache["timestamp"] = now
                    if not get_last_successful_sync():
                        record_successful_sync(source="local_backup")
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

class IssueTokenRequest(BaseModel):
    user_id: str
    username: Optional[str] = None
    role: str = "student"
    group_num: str = "5108"
    subgroup: int = 2


@api_router.post("/auth/token")
async def issue_auth_token(req: IssueTokenRequest):
    """
    Issue a cryptographically signed user token for a given student/user.
    Establishes true user identity for scoped data isolation.
    """
    if not req.user_id or not req.user_id.strip():
        raise HTTPException(status_code=400, detail="Идентификатор пользователя не может быть пустым")

    clean_user_id = req.user_id.strip()
    clean_username = (req.username or clean_user_id).strip()

    # Sync with DB User record
    async with async_session() as session:
        user_record = await get_or_create_user(
            session=session,
            user_id=clean_user_id,
            username=clean_username,
            role=req.role,
            group_num=req.group_num,
            subgroup=req.subgroup,
        )

    token = create_user_token(
        user_id=clean_user_id,
        username=clean_username,
        role=req.role,
        group_num=req.group_num,
        subgroup=req.subgroup,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_record.id,
            "username": user_record.username,
            "role": user_record.role,
            "group_num": user_record.group_num,
            "subgroup": user_record.subgroup,
        }
    }


@api_router.get("/auth/me")
async def get_current_user_profile(request: Request):
    """Return the authenticated user profile."""
    user = get_current_user(request)
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "group_num": user.group_num,
        "subgroup": user.subgroup,
        "is_admin": user.is_admin,
        "auth_type": getattr(request.state, "auth_type", "user_token"),
    }


@api_router.get("/stats")
async def get_stats(request: Request):
    """Overall semester progress stats scoped strictly to current user."""
    user = get_current_user(request)
    async with async_session() as session:
        all_tasks = await get_tasks(session, owner_id=user.id)
        subjects = await get_subjects(session)

    total_tasks = len(all_tasks)
    done_tasks = sum(1 for t in all_tasks if t.status == "done")
    todo_tasks = total_tasks - done_tasks
    progress_pct = round((done_tasks / total_tasks) * 100) if total_tasks > 0 else 0

    last_sync = get_last_successful_sync()

    return {
        "user_id": user.id,
        "total_tasks": total_tasks,
        "done_tasks": done_tasks,
        "todo_tasks": todo_tasks,
        "progress_percent": progress_pct,
        "total_subjects": len(subjects),
        "last_successful_sync": last_sync,
        "sync_freshness_thresholds": {
            "fresh_minutes": settings.sync_fresh_threshold_minutes,
            "recent_minutes": settings.sync_recent_threshold_minutes,
        },
    }


@api_router.get("/subjects")
async def list_subjects(request: Request):
    """Subjects list with task counts and progress percentages scoped strictly to current user."""
    user = get_current_user(request)
    async with async_session() as session:
        subjects = await get_subjects(session)
        tasks = await get_tasks(session, owner_id=user.id)

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
    request: Request,
    subject_id: Optional[int] = Query(None, description="Filter by subject ID"),
    status: Optional[str] = Query("all", description="Filter by status: todo, done, all"),
):
    """Tasks list scoped strictly to current authenticated user."""
    filter_status = None if (not status or status == "all") else status.strip().lower()
    user = get_current_user(request)

    async with async_session() as session:
        tasks = await get_tasks(
            session,
            status=filter_status,
            subject_id=subject_id,
            owner_id=user.id if not user.is_admin else None,
        )

    response_items = []
    for t in tasks:
        subj_name = t.subject.name if t.subject else "Неизвестный предмет"
        enhanced_attachments = []
        if t.attachments:
            for att in t.attachments:
                enhanced_attachments.append({
                    "id": att.id,
                    "name": att.file_name,
                    "download_url": f"/api/tasks/{t.id}/download?attachment_id={att.id}",
                })
        else:
            attachments = parse_task_attachments(t.details)
            for i, att in enumerate(attachments):
                enhanced_attachments.append({
                    "id": None,
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
            "owner_id": t.owner_id,
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
            "has_files": bool(t.file_url or (t.attachments and len(t.attachments) > 0) or enhanced_attachments),
        })

    return response_items


@api_router.get("/tasks/{task_id}")
async def get_task_detail(task_id: int, request: Request):
    """
    Retrieve single task detail by ID.
    Enforces strict IDOR / BOLA authorization check:
    Non-owners are returned 403 Forbidden.
    """
    user = get_current_user(request)

    async with async_session() as session:
        task = await get_task_by_id(session, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Задание не найдено")

        if task.owner_id and task.owner_id != user.id and not user.is_admin:
            raise HTTPException(
                status_code=403,
                detail=f"Доступ запрещен: задание #{task_id} принадлежит другому пользователю",
            )

        subj_name = task.subject.name if task.subject else "Неизвестный предмет"
        enhanced_attachments = []
        if task.attachments:
            for att in task.attachments:
                enhanced_attachments.append({
                    "id": att.id,
                    "name": att.file_name,
                    "download_url": f"/api/tasks/{task.id}/download?attachment_id={att.id}",
                })
        else:
            attachments = parse_task_attachments(task.details)
            for i, att in enumerate(attachments):
                enhanced_attachments.append({
                    "id": None,
                    "name": att["name"],
                    "url": att["url"],
                    "download_url": f"/api/tasks/{task.id}/download?idx={i}",
                })

        bb_course_url = BB_COURSE_MAP.get(
            subj_name,
            "https://bb.kai.ru/webapps/portal/execute/tabs/tabAction?tab_tab_group_id=_1_1"
        )

        return {
            "id": task.id,
            "owner_id": task.owner_id,
            "subject_id": task.subject_id,
            "subject_name": subj_name,
            "title": task.title,
            "task_type": task.task_type,
            "deadline": task.deadline.isoformat() if task.deadline else None,
            "status": task.status,
            "source": task.source,
            "details": task.details,
            "file_url": task.file_url,
            "file_name": task.file_name,
            "external_url": task.external_url,
            "attachments": enhanced_attachments,
            "bb_course_url": bb_course_url,
            "has_files": bool(task.file_url or (task.attachments and len(task.attachments) > 0) or enhanced_attachments),
        }


@api_router.get("/tasks/{task_id}/download")
async def download_task_file(
    task_id: int,
    request: Request,
    attachment_id: Optional[int] = Query(None, description="Task attachment record ID in database"),
    idx: int = Query(0, description="Attachment index fallback if task has multiple files"),
):
    """
    Secure task file download endpoint.
    Guarantees:
    - Authentication required (401 on missing/invalid/expired token).
    - Task ownership verified (403 on non-owner access).
    - Nonexistent task / attachment / missing file (404).
    - Defense against directory traversal: .., ..\\, %2e%2e, absolute paths, null bytes (400/403).
    - Sandboxed path resolution strictly within STORAGE_DIR.
    - Token in query parameter is strictly forbidden.
    """
    async with async_session() as session:
        task = await get_task_by_id(session, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Задание не найдено")

        # 1. Ownership check: Authenticated user without ownership -> 403 Forbidden
        user = get_current_user(request)
        if task.owner_id and task.owner_id != user.id and not user.is_admin:
            raise HTTPException(
                status_code=403,
                detail=f"Доступ запрещен: задание принадлежит пользователю '{task.owner_id}', у вас нет прав на скачивание",
            )

        # 2. Resolve attachment record via database lookup
        target_attachment: Optional[TaskAttachment] = None
        if attachment_id is not None:
            target_attachment = await get_task_attachment(session, attachment_id)
            if not target_attachment or target_attachment.task_id != task.id:
                raise HTTPException(status_code=404, detail="Вложение к задаче не найдено")
        elif task.attachments:
            if 0 <= idx < len(task.attachments):
                target_attachment = task.attachments[idx]
            else:
                target_attachment = task.attachments[0]

    # 3. Server-side sandboxed resolution for stored local attachments
    if target_attachment and target_attachment.file_path:
        raw_path = target_attachment.file_path.strip()
        filename = target_attachment.file_name or "attachment"

        # Traversal check: detect directory traversal indicators in raw and unquoted path
        unquoted = urllib.parse.unquote(raw_path)
        has_traversal_dotdot = ".." in raw_path or ".." in unquoted
        has_encoded_dots = "%2e" in raw_path.lower() or "%2e" in unquoted.lower()
        has_null = "\0" in raw_path or "\0" in unquoted
        is_abs = (
            os.path.isabs(raw_path)
            or raw_path.startswith("/")
            or raw_path.startswith("\\")
            or bool(re.match(r"^[a-zA-Z]:", raw_path))
        )

        if is_abs:
            raise HTTPException(
                status_code=400,
                detail="Абсолютные пути к файлам запрещены",
            )

        if has_traversal_dotdot or has_encoded_dots or has_null:
            raise HTTPException(
                status_code=400,
                detail="Обнаружена недопустимая попытка обхода пути (Path Traversal)",
            )

        storage_root = STORAGE_DIR.resolve()
        resolved_path = (STORAGE_DIR / raw_path).resolve()

        # Sandboxing check: target must be inside STORAGE_DIR
        try:
            resolved_path.relative_to(storage_root)
        except ValueError:
            raise HTTPException(
                status_code=403,
                detail="Доступ запрещен: выход за пределы защищенного хранилища",
            )

        if not resolved_path.is_file():
            raise HTTPException(status_code=404, detail="Запрошенный файл отсутствует на диске")

        media_type = target_attachment.content_type or mimetypes.guess_type(resolved_path.name)[0] or "application/octet-stream"
        quoted_name = urllib.parse.quote(filename)
        ascii_fallback = re.sub(r"[^\w\.\-]", "_", filename) or "file"
        headers = {
            "Content-Disposition": f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{quoted_name}',
            "Access-Control-Expose-Headers": "Content-Disposition",
        }
        return FileResponse(
            path=str(resolved_path),
            filename=ascii_fallback,
            media_type=media_type,
            headers=headers,
        )

    # 4. If remote Blackboard file or legacy file_url
    file_url = None
    target_name = None
    if target_attachment and target_attachment.file_url:
        file_url = target_attachment.file_url
        target_name = target_attachment.file_name
    elif task.file_url:
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
            detail="К этой задаче не прикреплен отдельный файл в Blackboard",
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
            detail=f"Не удалось скачать файл с Blackboard (HTTP {resp.status_code})",
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
async def toggle_task_status(task_id: int, request: Request):
    """Toggle task status between todo and done with strict ownership verification."""
    user = get_current_user(request)

    async with async_session() as session:
        task = await get_task_by_id(session, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # IDOR / BOLA Prevention: Verify ownership
        if task.owner_id and task.owner_id != user.id and not user.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Доступ запрещен: невозможно изменить статус чужого задания",
            )

        new_status = "done" if task.status == "todo" else "todo"
        updated = await update_task_status(session, task_id=task_id, status=new_status, owner_id=user.id if not user.is_admin else None)

    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update task")

    return {
        "id": updated.id,
        "owner_id": updated.owner_id,
        "subject_id": updated.subject_id,
        "subject_name": updated.subject.name if updated.subject else "",
        "title": updated.title,
        "task_type": updated.task_type,
        "status": updated.status,
        "attachments": parse_task_attachments(updated.details),
    }


@api_router.get("/schedule")
async def get_schedule(
    request: Request,
    day: Optional[int] = Query(None, description="Weekday 1..6 (1=Mon, 6=Sat)"),
    week: Optional[str] = Query(None, description="Week parity: even/odd or чет/нечет"),
):
    """Schedule for group 5108 (2nd subgroup) for a specific day with user-scoped pending task counts."""
    user = get_current_user(request)
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

    # Attach pending tasks count for each lesson scoped to current user
    async with async_session() as session:
        subjects = await get_subjects(session)
        todo_tasks = await get_tasks(session, status="todo", owner_id=user.id)

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
    request: Request,
    week: Optional[str] = Query(None, description="Week parity: even/odd or чет/нечет")
):
    """Full week schedule grid (Monday to Saturday) with user-scoped pending task counts."""
    user = get_current_user(request)
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
        todo_tasks = await get_tasks(session, status="todo", owner_id=user.id)

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
        record_successful_sync(source="blackboard")
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

    # 1. Retrieve registered academic disciplines
    async with async_session() as session:
        db_subjects = await get_subjects(session)
        subj_names = [s.name for s in db_subjects]

    if not subj_names:
        subj_names = ["Общие задачи"]

    try:
        parsed = gemini_svc.parse_natural_task(req.text, subj_names)
    except Exception as e:
        logger.error("Gemini parse_natural_task error: %s. Using heuristic fallback.", e)
        parsed = gemini_svc._rule_based_fallback(req.text, subj_names)

    subj_name = parsed.get("subject") or (subj_names[0] if subj_names else "Общие задачи")
    title = parsed.get("title") or req.text.strip()[:60]
    task_type = parsed.get("task_type") or "задание"
    deadline_raw = parsed.get("deadline_raw")
    deadline_iso = parsed.get("deadline_iso")
    requirements = parsed.get("requirements")
    auditorium = parsed.get("auditorium")
    materials_summary = parsed.get("materials_summary")

    aud_source = "message" if auditorium else "not_specified"

    # If auditorium wasn't explicitly extracted from text, attempt lookup from schedule
    if not auditorium:
        try:
            raw_sched = get_cached_raw_schedule()
            for day_key, lessons_raw in raw_sched.items():
                for item in lessons_raw:
                    l = Lesson.from_raw_dict(item)
                    if l.discipl_name and (subj_name.lower() in l.discipl_name.lower() or l.discipl_name.lower() in subj_name.lower()):
                        if l.aud_num and l.build_num:
                            auditorium = f"{l.aud_num} ({l.build_num} зд.)"
                        elif l.aud_num:
                            auditorium = l.aud_num
                        aud_source = "schedule"
                        break
                if auditorium:
                    break
        except Exception as e:
            logger.warning("Auditorium schedule lookup failed: %s", e)

    # 1. Subject match calculation
    text_low = req.text.lower()
    subj_low = subj_name.lower()
    subj_stem = subj_low[:-1] if len(subj_low) > 4 else subj_low
    if subj_low in text_low:
        subj_match_type = "exact"
        subj_confidence = 98
        subj_label = f"Точное совпадение с дисциплиной «{subj_name}»"
    elif subj_stem in text_low:
        subj_match_type = "inflected_match"
        subj_confidence = 95
        subj_label = f"Точное совпадение с дисциплиной «{subj_name}»"
    elif any(word[:4] in text_low for word in subj_low.split() if len(word) >= 4):
        subj_match_type = "keyword"
        subj_confidence = 85
        subj_label = f"Сопоставлено по ключевым словам с «{subj_name}»"
    else:
        subj_match_type = "fallback"
        subj_confidence = 60
        subj_label = f"Дисциплина определена по умолчанию: «{subj_name}»"

    # 2. Deadline match calculation
    if deadline_raw:
        if deadline_iso:
            try:
                dt = datetime.fromisoformat(deadline_iso)
                deadline_display = dt.strftime("%Y-%m-%d %H:%M MSK")
            except Exception:
                deadline_display = f"{deadline_iso} MSK"
            deadline_label = f"«{deadline_raw}» → расчет дедлайна по календарю (MSK)"
        else:
            deadline_display = deadline_raw
            deadline_label = f"Фраза: «{deadline_raw}» (точная дата требует уточнения)"
    else:
        deadline_display = "Не указан"
        deadline_label = "В сообщении не найдены указания на дедлайн"

    # 3. Auditorium match calculation
    if aud_source == "message":
        aud_label = "Извлечено непосредственно из текста сообщения"
    elif aud_source == "schedule":
        aud_label = f"Подставлено из актуального расписания KAI для предмета «{subj_name}»"
    else:
        aud_label = "Не указана в сообщении и не найдена в расписании"

    # 4. Source attribution
    source_primary = "Сообщение старосты / чат"
    enriched_by = ["Расписание KAI (группа 5108)"] if aud_source == "schedule" else []

    evidence = {
        "subject": {
            "name": subj_name,
            "match_type": subj_match_type,
            "confidence_percent": subj_confidence,
            "label": subj_label,
        },
        "deadline": {
            "raw_phrase": deadline_raw,
            "resolved_iso": deadline_iso,
            "resolved_display": deadline_display,
            "label": deadline_label,
        },
        "auditorium": {
            "value": auditorium or "Не указана",
            "source": aud_source,
            "source_label": aud_label,
        },
        "source": {
            "primary": source_primary,
            "enriched_by": enriched_by,
            "summary": f"{source_primary}" + (f" · {', '.join(enriched_by)}" if enriched_by else ""),
        },
    }

    return {
        "subject_name": subj_name,
        "title": title,
        "task_type": task_type,
        "deadline_raw": deadline_raw,
        "deadline_iso": deadline_iso,
        "requirements": requirements,
        "auditorium": auditorium,
        "materials_summary": materials_summary,
        "original_text": req.text.strip(),
        "reasoning": parsed.get("reasoning") or f"Определено на основе контекста сообщения старосты: «{req.text.strip()[:60]}...»",
        "evidence": evidence,
        "metadata": parsed.get("_metadata", {}),
    }


@api_router.post("/tasks")
async def create_new_task(req: CreateTaskRequest, request: Request):
    """Persist confirmed task to SQLite database for current authenticated user."""
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

    user = get_current_user(request)
    owner_id = user.id

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
            owner_id=owner_id,
        )

    return {
        "id": new_task.id,
        "owner_id": new_task.owner_id,
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
async def ai_summarize_task(task_id: int, request: Request):
    """
    Generate concise student lab cheat-sheet using Google Gemini AI with ownership verification,
    deterministic caching, error categorization, and graceful fallback handling.
    """
    user = get_current_user(request)

    async with async_session() as session:
        task = await get_task_by_id(session, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Задание не найдено")

        # IDOR / BOLA Prevention: Verify task ownership
        if task.owner_id and task.owner_id != user.id and not user.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Доступ запрещен: невозможно создать AI конспект для чужого задания",
            )

    gemini_svc = GeminiService()

    try:
        if not gemini_svc.is_available():
            raise AiServiceError(
                category=AiErrorCategory.AUTH_ERROR,
                message="Google Gemini API не настроен. Укажите GEMINI_API_KEY в файле .env",
                metadata={
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "duration_ms": 0,
                    "provider": "google-gemini",
                    "model": gemini_svc.model,
                    "success": False,
                    "failure_category": AiErrorCategory.AUTH_ERROR.value,
                    "cached": False,
                }
            )

        summary_data = gemini_svc.summarize_lab_work(
            title=task.title,
            details=task.details or "",
            cache_user_id=user.id,
        )
        if "_metadata" in summary_data and "metadata" not in summary_data:
            summary_data["metadata"] = summary_data["_metadata"]
        return summary_data

    except Exception as e:
        cat = classify_ai_error(e)
        ui_info = get_ai_error_ui_info(cat)
        meta = getattr(e, "metadata", None) or {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "duration_ms": 0,
            "provider": "google-gemini",
            "model": gemini_svc.model,
            "success": False,
            "failure_category": cat.value,
            "cached": False,
        }

        # Status code mapping
        status_code = 503
        if cat in (AiErrorCategory.RATE_LIMIT, AiErrorCategory.QUOTA_EXCEEDED):
            status_code = 429
        elif cat == AiErrorCategory.TIMEOUT:
            status_code = 504

        error_envelope = {
            "detail": ui_info["full_message"],
            "error": {
                "category": cat.value,
                "title": ui_info["title"],
                "reassurance": ui_info["reassurance"],
                "message": ui_info["full_message"],
                "detail": ui_info["detail"],
                "retryable": ui_info["retryable"],
                "retry_after": ui_info["retry_after"],
            },
            "metadata": meta,
        }
        logger.warning("Gemini summarize_lab_work classified error [%s]: %s", cat.value, e)
        return JSONResponse(status_code=status_code, content=error_envelope)


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
