"""
Comprehensive Security Verification Suite for File Downloads.
Endpoints tested:
  GET /api/tasks/{id}/download

Vector Matrix:
1. No auth -> 401
2. Invalid auth -> 401
3. Query token rejection (?token=...) -> 401
4. Expired auth -> 401
5. Authenticated user without ownership (wrong user) -> 403
6. Authenticated owner -> 200 with matching file content
7. Nonexistent task -> 404
8. Nonexistent attachment ID -> 404
9. Missing file on disk -> 404
10. Path traversal attempt (../) -> 400 or 403
11. Path traversal attempt (..\\) -> 400 or 403
12. Encoded traversal (%2e%2e) & absolute paths -> 400 or 403
"""

import asyncio
import os
import sys
from pathlib import Path

# Ensure repo root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from api.app import app, STORAGE_DIR
from core.config import settings
from database.connection import init_db, async_session
from database.crud import (
    get_or_create_subject,
    create_task,
    create_task_attachment,
)


def get_client():
    asyncio.run(init_db())
    return TestClient(app)


def get_valid_token():
    return settings.app_auth_token or "kai5108_secret_passcode_2026"


def get_auth_headers(token=None):
    t = token or get_valid_token()
    return {
        "Authorization": f"Bearer {t}",
        "X-User-Id": "student_5108",
    }


def setup_fixtures(token=None):
    """Seed sample test tasks and attachments for security testing."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Create a legitimate test file
    safe_file_name = "test_lab_guide_2026.pdf"
    safe_file_path = STORAGE_DIR / safe_file_name
    safe_file_content = b"%PDF-1.4 KAI Student OS Secure Test File Content 2026"
    safe_file_path.write_bytes(safe_file_content)

    async def _seed():
        async with async_session() as session:
            subject = await get_or_create_subject(session, name="Безопасность ИС")

            # Task A: Owned by student_5108, has valid local attachment
            task_owner = await create_task(
                session=session,
                subject_id=subject.id,
                title="Лабораторная работа по криптографии",
                owner_id="student_5108",
            )
            att_valid = await create_task_attachment(
                session=session,
                task_id=task_owner.id,
                file_name=safe_file_name,
                file_path=safe_file_name,
                content_type="application/pdf",
                file_size=len(safe_file_content),
            )

            # Task B: Owned by student_5108, attachment points to nonexistent file
            task_missing_file = await create_task(
                session=session,
                subject_id=subject.id,
                title="Задание с удаленным файлом",
                owner_id="student_5108",
            )
            att_missing = await create_task_attachment(
                session=session,
                task_id=task_missing_file.id,
                file_name="missing_notes.pdf",
                file_path="nonexistent_subfolder/missing_notes.pdf",
                content_type="application/pdf",
            )

            # Task C: Owned by student_other (for 403 test)
            task_other_user = await create_task(
                session=session,
                subject_id=subject.id,
                title="Приватное задание другого студента",
                owner_id="student_other_999",
            )
            att_other = await create_task_attachment(
                session=session,
                task_id=task_other_user.id,
                file_name="secret_notes.pdf",
                file_path=safe_file_name,  # file exists on disk, but student_5108 has no ownership
                content_type="application/pdf",
            )

            # Task D: Malicious traversal task - dotdot slash (../)
            task_traversal_slash = await create_task(
                session=session,
                subject_id=subject.id,
                title="Атака Directory Traversal Slash",
                owner_id="student_5108",
            )
            att_traversal_slash = await create_task_attachment(
                session=session,
                task_id=task_traversal_slash.id,
                file_name="exploit_slash.txt",
                file_path="../api/app.py",
                content_type="text/plain",
            )

            # Task E: Malicious traversal task - dotdot backslash (..\)
            task_traversal_bslash = await create_task(
                session=session,
                subject_id=subject.id,
                title="Атака Directory Traversal Backslash",
                owner_id="student_5108",
            )
            att_traversal_bslash = await create_task_attachment(
                session=session,
                task_id=task_traversal_bslash.id,
                file_name="exploit_bslash.txt",
                file_path=r"..\..\Windows\System32\drivers\etc\hosts",
                content_type="text/plain",
            )

            # Task F: Encoded traversal (%2e%2e)
            task_traversal_encoded = await create_task(
                session=session,
                subject_id=subject.id,
                title="Атака Encoded Traversal",
                owner_id="student_5108",
            )
            att_traversal_encoded = await create_task_attachment(
                session=session,
                task_id=task_traversal_encoded.id,
                file_name="exploit_encoded.txt",
                file_path="%2e%2e%2f%2e%2e%2fboot.ini",
                content_type="text/plain",
            )

            # Task G: Absolute path
            task_absolute = await create_task(
                session=session,
                subject_id=subject.id,
                title="Атака Absolute Path",
                owner_id="student_5108",
            )
            att_absolute = await create_task_attachment(
                session=session,
                task_id=task_absolute.id,
                file_name="exploit_abs.txt",
                file_path="C:\\Windows\\win.ini" if os.name == "nt" else "/etc/passwd",
                content_type="text/plain",
            )

            return {
                "safe_file_content": safe_file_content,
                "task_owner_id": task_owner.id,
                "att_valid_id": att_valid.id,
                "task_missing_file_id": task_missing_file.id,
                "att_missing_id": att_missing.id,
                "task_other_user_id": task_other_user.id,
                "att_other_id": att_other.id,
                "task_traversal_slash_id": task_traversal_slash.id,
                "att_traversal_slash_id": att_traversal_slash.id,
                "task_traversal_bslash_id": task_traversal_bslash.id,
                "att_traversal_bslash_id": att_traversal_bslash.id,
                "task_traversal_encoded_id": task_traversal_encoded.id,
                "att_traversal_encoded_id": att_traversal_encoded.id,
                "task_absolute_id": task_absolute.id,
                "att_absolute_id": att_absolute.id,
            }

    return asyncio.run(_seed())


# -------------------------------------------------------------
# 1. No Auth -> 401
# -------------------------------------------------------------
def test_download_no_auth_returns_401(client, fixtures):
    resp = client.get(f"/api/tasks/{fixtures['task_owner_id']}/download")
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
    assert "WWW-Authenticate" in resp.headers


# -------------------------------------------------------------
# 2. Invalid Auth -> 401
# -------------------------------------------------------------
def test_download_invalid_auth_returns_401(client, fixtures):
    bad_headers = {"Authorization": "Bearer invalid_secret_token_9999"}
    resp = client.get(f"/api/tasks/{fixtures['task_owner_id']}/download", headers=bad_headers)
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"


# -------------------------------------------------------------
# 3. Query Token Rejection (?token=...) -> 401
# -------------------------------------------------------------
def test_download_query_token_strictly_rejected_returns_401(client, fixtures, valid_token):
    """
    Verify ?token= is NOT accepted for authentication.
    Requests relying on query token without Authorization header must receive 401.
    """
    resp = client.get(f"/api/tasks/{fixtures['task_owner_id']}/download?token={valid_token}")
    assert resp.status_code == 401, f"Expected 401 for ?token= auth, got {resp.status_code}"


# -------------------------------------------------------------
# 4. Expired Auth -> 401
# -------------------------------------------------------------
def test_download_expired_auth_returns_401(client, fixtures, valid_token):
    # Case 4a: Explicit X-Session-Expired header
    expired_headers = {
        "Authorization": f"Bearer {valid_token}",
        "X-Session-Expired": "true",
    }
    resp = client.get(f"/api/tasks/{fixtures['task_owner_id']}/download", headers=expired_headers)
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
    assert "истек" in resp.json().get("detail", "").lower()

    # Case 4b: Expired token marker
    resp_exp_token = client.get(
        f"/api/tasks/{fixtures['task_owner_id']}/download",
        headers={"Authorization": "Bearer expired_session_token_123"},
    )
    assert resp_exp_token.status_code == 401


# -------------------------------------------------------------
# 5. Authenticated User Without Ownership -> 403
# -------------------------------------------------------------
def test_download_without_ownership_returns_403(client, fixtures, valid_token):
    """
    Verify that an authenticated user who does not own the task receives 403 Forbidden.
    Task belongs to student_other_999, caller is student_5108.
    """
    headers = {
        "Authorization": f"Bearer {valid_token}",
        "X-User-Id": "student_5108",
    }
    resp = client.get(f"/api/tasks/{fixtures['task_other_user_id']}/download", headers=headers)
    assert resp.status_code == 403, f"Expected 403 Forbidden, got {resp.status_code}: {resp.text}"
    assert "Доступ запрещен" in resp.json().get("detail", "")


# -------------------------------------------------------------
# 6. Authenticated Owner -> 200 with File Content
# -------------------------------------------------------------
def test_download_owner_returns_200(client, fixtures, auth_headers):
    resp = client.get(
        f"/api/tasks/{fixtures['task_owner_id']}/download?attachment_id={fixtures['att_valid_id']}",
        headers=auth_headers,
    )
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}: {resp.text}"
    assert resp.content == fixtures["safe_file_content"]
    assert "Content-Disposition" in resp.headers
    assert "test_lab_guide_2026" in resp.headers["Content-Disposition"]


# -------------------------------------------------------------
# 7. Nonexistent Task -> 404
# -------------------------------------------------------------
def test_download_nonexistent_task_returns_404(client, auth_headers):
    resp = client.get("/api/tasks/9999999/download", headers=auth_headers)
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


# -------------------------------------------------------------
# 8. Nonexistent Attachment ID -> 404
# -------------------------------------------------------------
def test_download_nonexistent_attachment_returns_404(client, fixtures, auth_headers):
    resp = client.get(
        f"/api/tasks/{fixtures['task_owner_id']}/download?attachment_id=9999999",
        headers=auth_headers,
    )
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


# -------------------------------------------------------------
# 9. Missing File on Disk -> 404
# -------------------------------------------------------------
def test_download_missing_file_on_disk_returns_404(client, fixtures, auth_headers):
    resp = client.get(
        f"/api/tasks/{fixtures['task_missing_file_id']}/download?attachment_id={fixtures['att_missing_id']}",
        headers=auth_headers,
    )
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
    assert "отсутствует на диске" in resp.json().get("detail", "")


# -------------------------------------------------------------
# 10. Path Traversal Attempt (../) -> 400 or 403
# -------------------------------------------------------------
def test_download_path_traversal_dotdot_slash_returns_400_or_403(client, fixtures, auth_headers):
    resp = client.get(
        f"/api/tasks/{fixtures['task_traversal_slash_id']}/download?attachment_id={fixtures['att_traversal_slash_id']}",
        headers=auth_headers,
    )
    assert resp.status_code in (400, 403), f"Expected 400 or 403 for ../ traversal, got {resp.status_code}"


# -------------------------------------------------------------
# 11. Path Traversal Attempt (..\\) -> 400 or 403
# -------------------------------------------------------------
def test_download_path_traversal_dotdot_backslash_returns_400_or_403(client, fixtures, auth_headers):
    resp = client.get(
        f"/api/tasks/{fixtures['task_traversal_bslash_id']}/download?attachment_id={fixtures['att_traversal_bslash_id']}",
        headers=auth_headers,
    )
    assert resp.status_code in (400, 403), f"Expected 400 or 403 for ..\\ traversal, got {resp.status_code}"


# -------------------------------------------------------------
# 12. Encoded Traversal (%2e%2e) & Absolute Paths -> 400 or 403
# -------------------------------------------------------------
def test_download_path_traversal_encoded_and_absolute_returns_400_or_403(client, fixtures, auth_headers):
    # 12a: Encoded %2e%2e
    resp_encoded = client.get(
        f"/api/tasks/{fixtures['task_traversal_encoded_id']}/download?attachment_id={fixtures['att_traversal_encoded_id']}",
        headers=auth_headers,
    )
    assert resp_encoded.status_code in (400, 403), f"Expected 400/403 for %2e%2e, got {resp_encoded.status_code}"

    # 12b: Absolute path
    resp_abs = client.get(
        f"/api/tasks/{fixtures['task_absolute_id']}/download?attachment_id={fixtures['att_absolute_id']}",
        headers=auth_headers,
    )
    assert resp_abs.status_code in (400, 403), f"Expected 400/403 for absolute path, got {resp_abs.status_code}"


# -------------------------------------------------------------
# 13. Authenticated Session Cookie -> 200
# -------------------------------------------------------------
def test_download_via_session_cookie_returns_200(client, fixtures, valid_token):
    """Verify session cookie allows authenticated download."""
    client.cookies.set("kai_app_auth_token", valid_token)
    resp = client.get(
        f"/api/tasks/{fixtures['task_owner_id']}/download?attachment_id={fixtures['att_valid_id']}",
        headers={"X-User-Id": "student_5108"},
    )
    assert resp.status_code == 200
    assert resp.content == fixtures["safe_file_content"]
    client.cookies.clear()


if __name__ == "__main__":
    c = TestClient(app)
    tok = settings.app_auth_token or "kai5108_secret_passcode_2026"
    auth_h = {"Authorization": f"Bearer {tok}", "X-User-Id": "student_5108"}
    fix = setup_fixtures(tok)

    print("Running Download Security Test Suite...")
    print("1. Testing download with no auth (401)...")
    test_download_no_auth_returns_401(c, fix)
    print("2. Testing download with invalid auth (401)...")
    test_download_invalid_auth_returns_401(c, fix)
    print("3. Testing download query token strictly rejected (401)...")
    test_download_query_token_strictly_rejected_returns_401(c, fix, tok)
    print("4. Testing download expired auth (401)...")
    test_download_expired_auth_returns_401(c, fix, tok)
    print("5. Testing download without ownership (403)...")
    test_download_without_ownership_returns_403(c, fix, tok)
    print("6. Testing download by owner (200)...")
    test_download_owner_returns_200(c, fix, auth_h)
    print("7. Testing download nonexistent task (404)...")
    test_download_nonexistent_task_returns_404(c, auth_h)
    print("8. Testing download nonexistent attachment (404)...")
    test_download_nonexistent_attachment_returns_404(c, fix, auth_h)
    print("9. Testing download missing file on disk (404)...")
    test_download_missing_file_on_disk_returns_404(c, fix, auth_h)
    print("10. Testing download path traversal dotdot slash (400/403)...")
    test_download_path_traversal_dotdot_slash_returns_400_or_403(c, fix, auth_h)
    print("11. Testing download path traversal dotdot backslash (400/403)...")
    test_download_path_traversal_dotdot_backslash_returns_400_or_403(c, fix, auth_h)
    print("12. Testing download encoded traversal & absolute path (400/403)...")
    test_download_path_traversal_encoded_and_absolute_returns_400_or_403(c, fix, auth_h)
    print("13. Testing download via authenticated session cookie (200)...")
    test_download_via_session_cookie_returns_200(c, fix, tok)
    print("\n[SUCCESS] ALL 13 DOWNLOAD HARDENING SECURITY TESTS PASSED SUCCESSFULLY!")
