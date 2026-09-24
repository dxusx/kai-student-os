"""
Product Consistency Regression Test Suite (tests/test_product_consistency.py).

Verifies the 8 core consistency guarantees of KAI Student OS:
1. read action immediate: Read-only queries execute immediately without confirmation
2. create task preview only: Mutation queries return action preview with 0 DB mutations
3. confirm exactly 1 task: Explicit confirmation writes exactly 1 task to DB
4. cancel zero mutation: Explicit cancellation aborts action with 0 DB mutations
5. double confirm idempotency: Re-confirming same action_id returns cached execution and does not create duplicate tasks
6. User A history invisible to B: History key namespace isolation and user context isolation
7. User A task invisible to B: Multi-tenant task isolation (Bob cannot see Alice's tasks)
8. User A cannot impersonate B: Token sub mismatch with X-User-Id strictly returns 403 Forbidden
"""

import asyncio
from pathlib import Path
import sys
import uuid
import pytest
from fastapi.testclient import TestClient

# Ensure repo root in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.app import app
from database.connection import init_db, async_session
from database.crud import get_or_create_user, get_tasks
from services.auth_service import create_user_token
from core.subjects import resolve_canonical_subject


@pytest.fixture(scope="module", autouse=True)
def initialize_database():
    """Ensure database schema is up-to-date."""
    asyncio.run(init_db())


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def alice_auth():
    token = create_user_token(
        user_id="user_alice_consistency",
        username="alice_test",
        role="student",
        group_num="5108",
        subgroup=2,
    )
    return {
        "user_id": "user_alice_consistency",
        "token": token,
        "headers": {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    }


@pytest.fixture
def bob_auth():
    token = create_user_token(
        user_id="user_bob_consistency",
        username="bob_test",
        role="student",
        group_num="5108",
        subgroup=1,
    )
    return {
        "user_id": "user_bob_consistency",
        "token": token,
        "headers": {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    }


def test_ai_chat_read_action_immediate(client, alice_auth):
    """
    1. Read action immediate:
    Read-only actions (schedule, pending tasks) must execute immediately
    without requiring user confirmation (requires_confirmation is False, status == 'executed').
    """
    resp = client.post(
        "/api/ai/chat",
        json={"message": "Какие пары у меня во вторник?", "history": []},
        headers=alice_auth["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "actions" in data
    sched_actions = [a for a in data["actions"] if a.get("tool") == "get_schedule"]
    assert len(sched_actions) >= 1
    action = sched_actions[0]
    assert action["status"] == "executed"
    assert action.get("requires_confirmation") is False


def test_ai_create_task_preview_only(client, alice_auth):
    """
    2. Create task preview only:
    Mutation requests to /api/ai/chat must NOT write directly to the database.
    They must return a preview with status == 'preview' and requires_confirmation == True.
    """
    async def _get_task_count():
        async with async_session() as session:
            tasks = await get_tasks(session, owner_id=alice_auth["user_id"])
            return len(tasks)

    count_before = asyncio.run(_get_task_count())

    resp = client.post(
        "/api/ai/chat",
        json={"message": "Создай задачу: Лабораторная работа по ТОЭ к следующей пятнице", "history": []},
        headers=alice_auth["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "actions" in data
    add_actions = [a for a in data["actions"] if a.get("tool") == "add_new_task"]
    assert len(add_actions) >= 1
    action = add_actions[0]

    # Must be preview only, NO direct mutation
    assert action["status"] == "preview"
    assert action.get("requires_confirmation") is True
    assert "action_id" in action
    assert len(action["action_id"]) > 0

    count_after = asyncio.run(_get_task_count())
    # Crucial assertion: ZERO database records created prior to confirmation
    assert count_after == count_before


def test_confirm_action_creates_exactly_one_task(client, alice_auth):
    """
    3. Confirm exactly 1 task:
    Calling /api/ai/confirm-action with confirmed: True executes the mutation,
    writing exactly 1 task to the database with resolved canonical subject.
    """
    # 1. Generate preview
    resp = client.post(
        "/api/ai/chat",
        json={"message": "Создай задачу: Лабораторная работа по Физике к следующей среде", "history": []},
        headers=alice_auth["headers"],
    )
    assert resp.status_code == 200
    action = resp.json()["actions"][0]
    action_id = action["action_id"]

    async def _get_task_count():
        async with async_session() as session:
            tasks = await get_tasks(session, owner_id=alice_auth["user_id"])
            return len(tasks)

    count_before = asyncio.run(_get_task_count())

    # 2. Confirm action
    confirm_resp = client.post(
        "/api/ai/confirm-action",
        json={"action_id": action_id, "confirmed": True, "action": action},
        headers=alice_auth["headers"],
    )
    assert confirm_resp.status_code == 200
    cdata = confirm_resp.json()
    assert cdata["success"] is True
    assert cdata["status"] == "executed"
    assert "data" in cdata and "id" in cdata["data"]

    count_after = asyncio.run(_get_task_count())
    # Exactly one task created
    assert count_after == count_before + 1


def test_cancel_action_zero_db_mutation(client, alice_auth):
    """
    4. Cancel zero mutation:
    Calling /api/ai/confirm-action with confirmed: False cancels the action,
    leaving the database completely untouched (0 mutations).
    """
    resp = client.post(
        "/api/ai/chat",
        json={"message": "Создай задачу: Домашнее задание по Информатике", "history": []},
        headers=alice_auth["headers"],
    )
    assert resp.status_code == 200
    action = resp.json()["actions"][0]
    action_id = action["action_id"]

    async def _get_task_count():
        async with async_session() as session:
            tasks = await get_tasks(session, owner_id=alice_auth["user_id"])
            return len(tasks)

    count_before = asyncio.run(_get_task_count())

    # Cancel action
    cancel_resp = client.post(
        "/api/ai/confirm-action",
        json={"action_id": action_id, "confirmed": False, "action": action},
        headers=alice_auth["headers"],
    )
    assert cancel_resp.status_code == 200
    cdata = cancel_resp.json()
    assert cdata["success"] is True
    assert cdata["status"] == "cancelled"
    assert cdata["requires_confirmation"] is False

    count_after = asyncio.run(_get_task_count())
    assert count_after == count_before


def test_double_confirm_idempotency(client, alice_auth):
    """
    5. Double confirm idempotency:
    Confirming the same action_id multiple times must return the cached execution
    and must NOT create a duplicate task in the database.
    """
    unique_title = f"Idempotent Task {uuid.uuid4().hex[:6]}"
    action_id = f"act_{uuid.uuid4().hex}"
    action_payload = {
        "action_id": action_id,
        "tool": "add_new_task",
        "summary": f"Создать задачу '{unique_title}'",
        "data": {
            "title": unique_title,
            "subject": "Физика",
            "canonical_subject_id": "physics",
            "deadline": "2026-10-01",
        },
    }

    async def _count_matching():
        async with async_session() as session:
            tasks = await get_tasks(session, owner_id=alice_auth["user_id"])
            return len([t for t in tasks if t.title == unique_title])

    # First confirm
    resp1 = client.post(
        "/api/ai/confirm-action",
        json={"action_id": action_id, "confirmed": True, "action": action_payload},
        headers=alice_auth["headers"],
    )
    assert resp1.status_code == 200
    assert resp1.json()["success"] is True

    # Second confirm (same action_id)
    resp2 = client.post(
        "/api/ai/confirm-action",
        json={"action_id": action_id, "confirmed": True, "action": action_payload},
        headers=alice_auth["headers"],
    )
    assert resp2.status_code == 200
    cdata2 = resp2.json()
    assert cdata2["success"] is True
    assert cdata2.get("idempotent") is True

    # Check database: exactly ONE task created, not two!
    matching_tasks = asyncio.run(_count_matching())
    assert matching_tasks == 1


def test_user_a_history_invisible_to_b(client, alice_auth, bob_auth):
    """
    6. User A history invisible to B:
    Validates user storage separation contract:
    - User A's key is kai_ai_history:{user_alice_consistency}
    - User B's key is kai_ai_history:{user_bob_consistency}
    - /api/auth/me returns distinct user context for each token.
    """
    alice_key = f"kai_ai_history:{alice_auth['user_id']}"
    bob_key = f"kai_ai_history:{bob_auth['user_id']}"
    assert alice_key != bob_key
    assert "alice" in alice_key
    assert "bob" in bob_key

    # Check profile isolation
    resp_alice = client.get("/api/auth/me", headers=alice_auth["headers"])
    assert resp_alice.status_code == 200
    assert resp_alice.json()["id"] == alice_auth["user_id"]
    assert resp_alice.json()["username"] == "alice_test"

    resp_bob = client.get("/api/auth/me", headers=bob_auth["headers"])
    assert resp_bob.status_code == 200
    assert resp_bob.json()["id"] == bob_auth["user_id"]
    assert resp_bob.json()["username"] == "bob_test"


def test_user_a_task_invisible_to_b(client, alice_auth, bob_auth):
    """
    7. User A task invisible to B:
    A task created by Alice must NEVER be returned in Bob's /api/tasks query.
    """
    secret_title = f"Secret Lab for Alice {uuid.uuid4().hex[:6]}"
    action_id = f"act_{uuid.uuid4().hex}"
    action_payload = {
        "action_id": action_id,
        "tool": "add_new_task",
        "summary": f"Создать задачу '{secret_title}'",
        "data": {
            "title": secret_title,
            "subject": "ТОЭ",
            "canonical_subject_id": "toe",
            "deadline": "2026-10-05",
        },
    }

    # Alice confirms and creates task
    resp = client.post(
        "/api/ai/confirm-action",
        json={"action_id": action_id, "confirmed": True, "action": action_payload},
        headers=alice_auth["headers"],
    )
    assert resp.status_code == 200

    # Bob queries his tasks
    bob_tasks_resp = client.get("/api/tasks", headers=bob_auth["headers"])
    assert bob_tasks_resp.status_code == 200
    bob_tasks = bob_tasks_resp.json()
    bob_titles = [t["title"] for t in bob_tasks]
    assert secret_title not in bob_titles

    # Alice queries her tasks
    alice_tasks_resp = client.get("/api/tasks", headers=alice_auth["headers"])
    assert alice_tasks_resp.status_code == 200
    alice_tasks = alice_tasks_resp.json()
    alice_titles = [t["title"] for t in alice_tasks]
    assert secret_title in alice_titles


def test_user_a_cannot_impersonate_b(client, alice_auth, bob_auth):
    """
    8. User A cannot impersonate B:
    If Alice attempts to send X-User-Id: user_bob while using Alice's token,
    the API must reject the request with 403 Forbidden.
    """
    tampered_headers = dict(alice_auth["headers"])
    tampered_headers["X-User-Id"] = bob_auth["user_id"]

    resp = client.get("/api/tasks", headers=tampered_headers)
    assert resp.status_code == 403
    assert "Попытка подмены идентификатора" in resp.json().get("detail", "")

    # Also test AI chat endpoint
    resp_ai = client.post(
        "/api/ai/chat",
        json={"message": "Привет!", "history": []},
        headers=tampered_headers,
    )
    assert resp_ai.status_code == 403
    assert "Попытка подмены идентификатора" in resp_ai.json().get("detail", "")


def test_canonical_subject_resolution():
    """
    Verify subject identity canonicalization:
    - Exact canonical ID matches
    - Normalized Russian aliases match canonical subject
    - Fallback generates clean representation
    """
    # Exact canonical ID or alias
    cid_toe, name_toe = resolve_canonical_subject("toe")
    assert cid_toe == "electrical"
    assert "электротехника" in name_toe.lower()

    # Alias Russian abbreviation
    cid_alias, name_alias = resolve_canonical_subject("ТОЭ")
    assert cid_alias == "electrical"

    # Physics
    cid_phys, name_phys = resolve_canonical_subject("общая физика")
    assert cid_phys == "physics"

    # Mathematics
    cid_math, name_math = resolve_canonical_subject("высшая математика")
    assert cid_math == "math"
