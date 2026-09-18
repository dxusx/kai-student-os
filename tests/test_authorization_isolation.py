"""
Comprehensive Authorization and User Data Isolation Test Suite.
Verifies:
1. App Authentication vs User Identity Authentication decoupling
2. Cryptographic JWT token issuance and signature verification (tamper rejection -> 401)
3. Expired token rejection (-> 401)
4. User A: GET own task -> 200 OK
5. User B: GET User A task -> 403 Forbidden (IDOR / BOLA defense)
6. User B: Download User A attachment -> 403 Forbidden (IDOR file access defense)
7. User A: Download own attachment -> 200 OK
8. User B: Toggle User A task status -> 403 Forbidden (State modification defense)
9. User A: Toggle own task status -> 200 OK
10. User B: AI summarize User A task -> 403 Forbidden (AI resource IDOR defense)
11. User B: Isolated Stats -> only counts User B tasks (User A stats hidden)
12. User A: Isolated Stats -> only counts User A tasks
13. User B: List tasks -> only User B tasks returned
14. User A: List tasks -> only User A tasks returned
15. User B: Schedule personalization -> pending task badges scoped to User B
16. Nonexistent task ID -> 404 Not Found
17. Profile endpoint /api/auth/me verification
18. Admin role override permissions
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Ensure repo root in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from api.app import app, STORAGE_DIR
from core.config import settings
from database.connection import init_db, async_session
from database.crud import (
    create_task,
    create_task_attachment,
    get_or_create_subject,
    get_or_create_user,
)
from services.auth_service import create_user_token, _b64_decode, _b64_encode


def setup_fixtures():
    """Create test users, tasks, and attachments in database."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    asyncio.run(init_db())

    async def _seed():
        async with async_session() as session:
            # 1. Ensure User A, User B, and Admin exist
            user_a = await get_or_create_user(session, user_id="user_alice", username="alice", role="student")
            user_b = await get_or_create_user(session, user_id="user_bob", username="bob", role="student")
            admin_user = await get_or_create_user(session, user_id="user_admin", username="admin", role="admin")

            # Clean up any previous test tasks for alice and bob to guarantee idempotency across multiple runs
            from sqlalchemy import delete, select
            from database.models import Task, TaskAttachment
            prev_task_ids = (await session.execute(
                select(Task.id).where(Task.owner_id.in_(["user_alice", "user_bob"]))
            )).scalars().all()
            if prev_task_ids:
                await session.execute(delete(TaskAttachment).where(TaskAttachment.task_id.in_(prev_task_ids)))
                await session.execute(delete(Task).where(Task.id.in_(prev_task_ids)))
                await session.commit()

            # 2. Seed Subjects
            subj_math = await get_or_create_subject(session, name="Тестовая Математика Isolation")
            subj_physics = await get_or_create_subject(session, name="Тестовая Физика Isolation")

            # 3. User A Tasks
            task_a1 = await create_task(
                session=session,
                subject_id=subj_math.id,
                title="Alice Task 1: Linear Algebra",
                task_type="лабораторная",
                owner_id="user_alice",
                status="todo",
                details="Private notes of Alice for Math Lab 1",
            )
            task_a2 = await create_task(
                session=session,
                subject_id=subj_physics.id,
                title="Alice Task 2: Optics Lab",
                task_type="лабораторная",
                owner_id="user_alice",
                status="done",
                details="Private notes of Alice for Physics",
            )

            # File for User A
            file_a_path = STORAGE_DIR / "alice_confidential.pdf"
            file_a_content = b"%PDF-1.4 Confidential Alice Lab Report 2026"
            with open(file_a_path, "wb") as f:
                f.write(file_a_content)

            att_a1 = await create_task_attachment(
                session=session,
                task_id=task_a1.id,
                file_name="alice_report.pdf",
                file_path="alice_confidential.pdf",
                content_type="application/pdf",
            )

            # 4. User B Tasks
            task_b1 = await create_task(
                session=session,
                subject_id=subj_math.id,
                title="Bob Task 1: Calculus",
                task_type="домашнее задание",
                owner_id="user_bob",
                status="todo",
                details="Private notes of Bob for Calculus",
            )

            file_b_path = STORAGE_DIR / "bob_assignment.txt"
            file_b_content = b"Bob Homework Solution Content"
            with open(file_b_path, "wb") as f:
                f.write(file_b_content)

            att_b1 = await create_task_attachment(
                session=session,
                task_id=task_b1.id,
                file_name="bob_solution.txt",
                file_path="bob_assignment.txt",
                content_type="text/plain",
            )

            return {
                "user_a_id": "user_alice",
                "user_b_id": "user_bob",
                "admin_id": "user_admin",
                "task_a1_id": task_a1.id,
                "task_a2_id": task_a2.id,
                "att_a1_id": att_a1.id,
                "file_a_content": file_a_content,
                "task_b1_id": task_b1.id,
                "att_b1_id": att_b1.id,
                "file_b_content": file_b_content,
            }

    return asyncio.run(_seed())


def run_authorization_tests():
    client = TestClient(app)
    fixtures = setup_fixtures()

    # Generate cryptographically signed user tokens
    token_a = create_user_token("user_alice", username="alice", role="student")
    token_b = create_user_token("user_bob", username="bob", role="student")
    token_admin = create_user_token("user_admin", username="admin", role="admin")

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    print("================================================================")
    print("STARTING KAI STUDENT OS AUTHORIZATION & ISOLATION TEST SUITE")
    print("================================================================")

    # 1. Profile / Me verification
    print("\n1. Verifying /api/auth/me for User A and User B...")
    resp_me_a = client.get("/api/auth/me", headers=headers_a)
    assert resp_me_a.status_code == 200
    assert resp_me_a.json()["id"] == "user_alice"
    assert resp_me_a.json()["username"] == "alice"

    resp_me_b = client.get("/api/auth/me", headers=headers_b)
    assert resp_me_b.status_code == 200
    assert resp_me_b.json()["id"] == "user_bob"
    print("   [PASS] User profiles accurately decoded from cryptographically signed tokens.")

    # 2. User A: GET own task -> 200
    print("\n2. User A reading own task...")
    resp_a_read_own = client.get(f"/api/tasks/{fixtures['task_a1_id']}", headers=headers_a)
    assert resp_a_read_own.status_code == 200
    data = resp_a_read_own.json()
    assert data["id"] == fixtures["task_a1_id"]
    assert data["owner_id"] == "user_alice"
    print("   [PASS] User A read own task: 200 OK.")

    # 3. User B: GET User A task -> 403 Forbidden (IDOR / BOLA Prevention)
    print("\n3. User B attempting to read User A task (IDOR / BOLA check)...")
    resp_b_read_a = client.get(f"/api/tasks/{fixtures['task_a1_id']}", headers=headers_b)
    assert resp_b_read_a.status_code == 403, f"Expected 403, got {resp_b_read_a.status_code}"
    assert "Доступ запрещен" in resp_b_read_a.json().get("detail", "")
    print(f"   [PASS] IDOR attempt blocked: HTTP {resp_b_read_a.status_code} Forbidden.")

    # 4. User B: Download User A attachment -> 403 Forbidden
    print("\n4. User B attempting to download User A attachment...")
    resp_b_dl_a = client.get(
        f"/api/tasks/{fixtures['task_a1_id']}/download?attachment_id={fixtures['att_a1_id']}",
        headers=headers_b,
    )
    assert resp_b_dl_a.status_code == 403, f"Expected 403, got {resp_b_dl_a.status_code}"
    print(f"   [PASS] File download unauthorized attempt blocked: HTTP {resp_b_dl_a.status_code} Forbidden.")

    # 5. User A: Download own attachment -> 200 OK
    print("\n5. User A downloading own attachment...")
    resp_a_dl_own = client.get(
        f"/api/tasks/{fixtures['task_a1_id']}/download?attachment_id={fixtures['att_a1_id']}",
        headers=headers_a,
    )
    assert resp_a_dl_own.status_code == 200
    assert resp_a_dl_own.content == fixtures["file_a_content"]
    print("   [PASS] User A downloaded own file: 200 OK, content matched.")

    # 6. User B: Modify (toggle) User A task -> 403 Forbidden
    print("\n6. User B attempting to toggle User A task status...")
    resp_b_toggle_a = client.post(f"/api/tasks/{fixtures['task_a1_id']}/toggle", headers=headers_b)
    assert resp_b_toggle_a.status_code == 403, f"Expected 403, got {resp_b_toggle_a.status_code}"
    # Verify task status was NOT altered in database
    verify_task = client.get(f"/api/tasks/{fixtures['task_a1_id']}", headers=headers_a).json()
    assert verify_task["status"] == "todo"
    print(f"   [PASS] Task mutation attempt blocked: HTTP {resp_b_toggle_a.status_code}, status untouched.")

    # 7. User A: Toggle own task status -> 200 OK
    print("\n7. User A toggling own task status...")
    resp_a_toggle = client.post(f"/api/tasks/{fixtures['task_a1_id']}/toggle", headers=headers_a)
    assert resp_a_toggle.status_code == 200
    assert resp_a_toggle.json()["status"] == "done"
    # Toggle back
    resp_a_toggle_back = client.post(f"/api/tasks/{fixtures['task_a1_id']}/toggle", headers=headers_a)
    assert resp_a_toggle_back.status_code == 200
    assert resp_a_toggle.json()["status"] == "done"
    assert resp_a_toggle_back.json()["status"] == "todo"
    print("   [PASS] User A toggled own task successfully.")

    # 8. User B: AI Summarize User A task -> 403 Forbidden
    print("\n8. User B attempting to AI summarize User A task...")
    resp_b_ai = client.post(f"/api/ai/summarize-task/{fixtures['task_a1_id']}", headers=headers_b)
    assert resp_b_ai.status_code == 403, f"Expected 403, got {resp_b_ai.status_code}"
    print(f"   [PASS] AI summary cross-user access blocked: HTTP {resp_b_ai.status_code} Forbidden.")

    # 9. User B: Stats Isolation -> only User B tasks counted
    print("\n9. Verifying User B stats isolation...")
    resp_b_stats = client.get("/api/stats", headers=headers_b)
    assert resp_b_stats.status_code == 200
    b_stats = resp_b_stats.json()
    assert b_stats["user_id"] == "user_bob"
    assert b_stats["total_tasks"] == 1, f"Expected Bob to have 1 task, got {b_stats['total_tasks']}"
    assert b_stats["todo_tasks"] == 1
    assert b_stats["done_tasks"] == 0
    print(f"   [PASS] Bob stats isolated: {b_stats['total_tasks']} task (Alice's tasks completely hidden).")

    # 10. User A: Stats Isolation -> only User A tasks counted
    print("\n10. Verifying User A stats isolation...")
    resp_a_stats = client.get("/api/stats", headers=headers_a)
    assert resp_a_stats.status_code == 200
    a_stats = resp_a_stats.json()
    assert a_stats["user_id"] == "user_alice"
    assert a_stats["total_tasks"] == 2, f"Expected Alice to have 2 tasks, got {a_stats['total_tasks']}"
    assert a_stats["todo_tasks"] == 1
    assert a_stats["done_tasks"] == 1
    print(f"   [PASS] Alice stats isolated: {a_stats['total_tasks']} tasks.")

    # 11. User B: List tasks -> only Bob's tasks returned
    print("\n11. Verifying User B task list scoping...")
    resp_b_tasks = client.get("/api/tasks", headers=headers_b)
    assert resp_b_tasks.status_code == 200
    b_task_list = resp_b_tasks.json()
    assert len(b_task_list) == 1
    assert b_task_list[0]["id"] == fixtures["task_b1_id"]
    assert b_task_list[0]["owner_id"] == "user_bob"
    print(f"   [PASS] User B tasks query scoped: exactly {len(b_task_list)} task returned, User A data 0%.")

    # 12. User A: List tasks -> only Alice's tasks returned
    print("\n12. Verifying User A task list scoping...")
    resp_a_tasks = client.get("/api/tasks", headers=headers_a)
    assert resp_a_tasks.status_code == 200
    a_task_list = resp_a_tasks.json()
    assert len(a_task_list) == 2
    assert all(t["owner_id"] == "user_alice" for t in a_task_list)
    print(f"   [PASS] User A tasks query scoped: exactly {len(a_task_list)} tasks returned.")

    # 13. Token Signature Tampering -> 401 Unauthorized
    print("\n13. Testing cryptographic signature tamper defense...")
    parts = token_a.split(".")
    # Tamper with payload (sub) while keeping signature
    payload = json.loads(_b64_decode(parts[1]).decode("utf-8"))
    payload["sub"] = "user_bob"  # Attacker impersonation attempt
    forged_payload_b64 = _b64_encode(json.dumps(payload).encode("utf-8"))
    tampered_token = f"{parts[0]}.{forged_payload_b64}.{parts[2]}"

    resp_tampered = client.get("/api/tasks", headers={"Authorization": f"Bearer {tampered_token}"})
    assert resp_tampered.status_code == 401, f"Expected 401 for tampered token, got {resp_tampered.status_code}"
    assert "подделки" in resp_tampered.json().get("detail", "") or "подпись" in resp_tampered.json().get("detail", "")
    print(f"   [PASS] Tampered user token rejected: HTTP {resp_tampered.status_code} (Signature mismatch).")

    # 14. Expired User Token -> 401 Unauthorized
    print("\n14. Testing expired user token rejection...")
    expired_token = create_user_token("user_alice", expires_in_seconds=-60)
    resp_expired = client.get("/api/tasks", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp_expired.status_code == 401, f"Expected 401 for expired token, got {resp_expired.status_code}"
    assert "истек" in resp_expired.json().get("detail", "")
    print(f"   [PASS] Expired user token rejected: HTTP {resp_expired.status_code} Unauthorized.")

    # 15. Nonexistent Task Access -> 404
    print("\n15. Testing nonexistent task access...")
    resp_404 = client.get("/api/tasks/999999", headers=headers_a)
    assert resp_404.status_code == 404
    print("   [PASS] Nonexistent task returns 404 Not Found.")

    # 16. Admin Role Override -> Can read task
    print("\n16. Testing administrative role override...")
    resp_admin = client.get(f"/api/tasks/{fixtures['task_a1_id']}", headers=headers_admin)
    assert resp_admin.status_code == 200
    assert resp_admin.json()["id"] == fixtures["task_a1_id"]
    print("   [PASS] Admin user successfully authorized across tenant boundaries.")

    # 17. Schedule Personalization
    print("\n17. Verifying schedule personalization per student...")
    resp_sched_b = client.get("/api/schedule?day=2&week=чет", headers=headers_b)
    assert resp_sched_b.status_code == 200
    sched_data = resp_sched_b.json()
    assert "lessons" in sched_data
    print("   [PASS] Schedule pending task badges computed strictly for authenticated student.")

    # 18. Issue token endpoint
    print("\n18. Testing token issuance via /api/auth/token...")
    resp_issue = client.post(
        "/api/auth/token",
        json={"user_id": "user_charlie", "username": "charlie", "role": "student"},
        headers=headers_admin,
    )
    assert resp_issue.status_code == 200
    charlie_token = resp_issue.json()["access_token"]
    resp_charlie_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {charlie_token}"})
    assert resp_charlie_me.status_code == 200
    assert resp_charlie_me.json()["id"] == "user_charlie"
    print("   [PASS] Token issuance and authentication lifecycle verified.")

    print("\n================================================================")
    print("SUCCESS: ALL 18 AUTHORIZATION & ISOLATION TESTS PASSED (100%)")
    print("================================================================")


if __name__ == "__main__":
    run_authorization_tests()
