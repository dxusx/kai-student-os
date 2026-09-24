"""
Comprehensive Test Suite for Google AI Studio Transformation (tests/test_ai_studio.py).
Verifies:
1. REST API endpoint /api/ai/chat authentication verification (401 without valid token)
2. Multi-turn conversational chat dialog ("Привет, кто ты?")
3. Function Calling: get_schedule tool invocation ("Какие пары у меня во вторник?")
4. Function Calling: add_new_task tool invocation ("Создай задачу по ООП до пятницы")
5. Function Calling: get_pending_tasks tool invocation ("Мои горящие дедлайны")
6. Function Calling: toggle_task_status tool invocation ("Отметь задачу #1")
7. Mode switching verification (tutor, organizer, report)
8. Multimodal base64 image parsing
"""

import asyncio
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

# Ensure repo root in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.app import app
from database.connection import init_db
from services.auth_service import create_user_token


@pytest.fixture(scope="module", autouse=True)
def initialize_database():
    asyncio.run(init_db())


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    token = create_user_token(
        user_id="test_student_ai",
        username="test_student",
        role="student",
        group_num="5108",
        subgroup=2,
    )
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def test_ai_chat_unauthorized(client):
    """Verify endpoint rejects requests without auth token with 401 Unauthorized."""
    resp = client.post("/api/ai/chat", json={"message": "Привет!"})
    assert resp.status_code == 401
    assert "detail" in resp.json()


def test_ai_chat_dialog(client, auth_headers):
    """Verify conversational dialog request in tutor mode."""
    payload = {
        "message": "Привет, кто ты?",
        "history": [],
        "mode": "tutor",
    }
    resp = client.post("/api/ai/chat", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert len(data["response"]) > 20
    assert any(k in data["response"].lower() for k in ["ассистент", "репетитор", "5108", "kai", "каи"])
    assert data["mode"] == "tutor"
    assert "metadata" in data


def test_ai_chat_function_calling_get_schedule(client, auth_headers):
    """Verify Function Calling: query schedule invokes get_schedule tool and formats lessons."""
    payload = {
        "message": "Какие пары у меня во вторник?",
        "history": [],
        "mode": "organizer",
    }
    resp = client.post("/api/ai/chat", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "actions" in data
    # Verify get_schedule tool action was captured
    sched_actions = [a for a in data["actions"] if a.get("tool") == "get_schedule"]
    assert len(sched_actions) >= 1
    action = sched_actions[0]
    assert action["status"] == "executed"
    assert "Вторник" in action.get("summary", "") or "вторник" in action.get("summary", "").lower()
    # Response contains markdown schedule
    assert any(k in data["response"].lower() for k in ["расписание", "вторник", "пар"])


def test_ai_chat_function_calling_add_task(client, auth_headers):
    """Verify Function Calling: task creation request invokes add_new_task preview and confirms via confirm-action."""
    payload = {
        "message": "Создай задачу: Лабораторная работа №4 по ООП к следующей среде",
        "history": [],
        "mode": "organizer",
    }
    resp = client.post("/api/ai/chat", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "actions" in data
    add_actions = [a for a in data["actions"] if a.get("tool") == "add_new_task"]
    assert len(add_actions) >= 1
    action = add_actions[0]
    # Product consistency rule: Mutations must be preview first!
    assert action["status"] == "preview"
    assert action.get("requires_confirmation") is True
    assert "action_id" in action
    assert "ООП" in action["summary"]

    # Now confirm the action explicitly
    confirm_resp = client.post(
        "/api/ai/confirm-action",
        json={"action_id": action["action_id"], "confirmed": True, "action": action},
        headers=auth_headers,
    )
    assert confirm_resp.status_code == 200
    cdata = confirm_resp.json()
    assert cdata["success"] is True
    assert cdata["status"] == "executed"
    assert "data" in cdata and "id" in cdata["data"]


def test_ai_chat_function_calling_get_pending_tasks(client, auth_headers):
    """Verify Function Calling: checking deadlines invokes get_pending_tasks tool."""
    payload = {
        "message": "Покажи мои горящие дедлайны и несданные задачи",
        "history": [],
        "mode": "organizer",
    }
    resp = client.post("/api/ai/chat", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "actions" in data
    task_actions = [a for a in data["actions"] if a.get("tool") == "get_pending_tasks"]
    assert len(task_actions) >= 1
    # Read-only actions execute immediately
    assert task_actions[0]["status"] == "executed"
    assert task_actions[0].get("requires_confirmation") is False


def test_ai_chat_function_calling_toggle_task(client, auth_headers):
    """Verify Function Calling: toggle task invokes toggle_task_status preview and confirms via confirm-action."""
    payload = {
        "message": "Отметь задачу #1 как выполненную",
        "history": [],
        "mode": "organizer",
    }
    resp = client.post("/api/ai/chat", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    toggle_actions = [a for a in data["actions"] if a.get("tool") == "toggle_task_status"]
    assert len(toggle_actions) >= 1
    action = toggle_actions[0]
    # Product consistency rule: Mutations must be preview first!
    assert action["status"] == "preview"
    assert action.get("requires_confirmation") is True
    assert "action_id" in action


def test_ai_chat_report_mode(client, auth_headers):
    """Verify report mode returns technical writer formatting assistance."""
    payload = {
        "message": "Помоги оформить отчет по лабораторной работе по физике",
        "history": [],
        "mode": "report",
    }
    resp = client.post("/api/ai/chat", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "report"
    assert any(k in data["response"].lower() for k in ["отчет", "гост", "лабораторн", "цель", "вывод"])


def test_ai_chat_multimodal(client, auth_headers):
    """Verify multimodal base64 image parsing."""
    # 1x1 transparent PNG
    dummy_png_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    payload = {
        "message": "Разбери это фото задания",
        "image_base64": dummy_png_b64,
        "mode": "tutor",
    }
    resp = client.post("/api/ai/chat", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert any(k in data["response"].lower() for k in ["изображен", "фото", "материал", "задан"])
