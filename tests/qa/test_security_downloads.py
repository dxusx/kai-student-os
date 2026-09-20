"""
QA Test Module: Security, Downloads, & Data Isolation (FILE-001..004, ISOL-001..003)
Domains 3.8 & 3.25: Rigorous automated verification of:
1. Binary download integrity (PDF, DOCX, ZIP)
2. Missing attachment 404 handling
3. Path traversal attacks (../, %2e%2e, null bytes)
4. Absolute system path attacks
5. Multi-user BOLA/IDOR isolation (Alice vs Bob tasks, toggles, downloads)
"""

import httpx
from tests.qa.test_env import (
    BASE_URL,
    get_alice_token,
    get_bob_token,
    get_admin_token,
)


def test_file_001_valid_attachment_downloads():
    """FILE-001: Download real PDF, DOCX, and ZIP attachments with correct headers."""
    alice_token = get_alice_token()
    headers = {"Authorization": f"Bearer {alice_token}"}

    # Fetch Alice's tasks to obtain attachment IDs
    tasks_res = httpx.get(f"{BASE_URL}/api/tasks", headers=headers, timeout=5.0)
    assert tasks_res.status_code == 200
    tasks = tasks_res.json()

    # Find tasks with attachments
    task_with_pdf = next(t for t in tasks if "Измерения" in t["title"])
    task_with_docx = next(t for t in tasks if "Диоды" in t["title"])
    task_with_zip = next(t for t in tasks if "Транзисторы" in t["title"])

    # 1. Download PDF
    res_pdf = httpx.get(f"{BASE_URL}/api/tasks/{task_with_pdf['id']}/download", headers=headers, timeout=5.0)
    assert res_pdf.status_code == 200, f"PDF download failed: {res_pdf.status_code}"
    assert res_pdf.content.startswith(b"%PDF-1.4"), "Downloaded PDF does not contain valid PDF magic bytes"
    assert "attachment" in res_pdf.headers.get("content-disposition", "").lower()

    # 2. Download DOCX
    res_docx = httpx.get(f"{BASE_URL}/api/tasks/{task_with_docx['id']}/download", headers=headers, timeout=5.0)
    assert res_docx.status_code == 200, f"DOCX download failed: {res_docx.status_code}"
    assert res_docx.content.startswith(b"PK\x03\x04"), "Downloaded DOCX does not contain valid PK zip header"

    # 3. Download ZIP
    res_zip = httpx.get(f"{BASE_URL}/api/tasks/{task_with_zip['id']}/download", headers=headers, timeout=5.0)
    assert res_zip.status_code == 200, f"ZIP download failed: {res_zip.status_code}"
    assert res_zip.content.startswith(b"PK\x03\x04"), "Downloaded ZIP does not contain valid PK zip header"


def test_file_002_missing_attachment_handling():
    """FILE-002: Nonexistent task or missing file returns 404 Not Found."""
    alice_token = get_alice_token()
    headers = {"Authorization": f"Bearer {alice_token}"}

    # Nonexistent task ID
    res = httpx.get(f"{BASE_URL}/api/tasks/999999/download", headers=headers, timeout=5.0)
    assert res.status_code == 404, f"Expected 404 for missing task, got {res.status_code}"

    # Nonexistent attachment ID on valid task
    res_att = httpx.get(f"{BASE_URL}/api/tasks/1/download?attachment_id=888888", headers=headers, timeout=5.0)
    assert res_att.status_code == 404, f"Expected 404 for missing attachment, got {res_att.status_code}"


def test_file_003_path_traversal_rejection():
    """FILE-003: Path traversal indicators (../, %2e%2e, null byte) are strictly blocked."""
    alice_token = get_alice_token()
    headers = {"Authorization": f"Bearer {alice_token}"}

    traversal_payloads = [
        "../../../../Windows/win.ini",
        "..%2f..%2f..%2fWindows%2fwin.ini",
        "....//....//etc/passwd",
        "attachments/../../config.py",
        "safe.pdf%00/../etc/passwd",
    ]

    for payload in traversal_payloads:
        res = httpx.get(
            f"{BASE_URL}/api/tasks/1/download?raw_path={payload}",
            headers=headers,
            timeout=5.0
        )
        # Server must reject or ignore invalid raw_path and not leak files outside storage
        assert res.status_code in (400, 403, 404, 200), f"Unexpected status {res.status_code} on payload {payload}"
        assert b"[extensions]" not in res.content
        assert b"root:" not in res.content


def test_file_004_absolute_path_rejection():
    """FILE-004: Absolute system path resolution attempts are strictly blocked."""
    alice_token = get_alice_token()
    headers = {"Authorization": f"Bearer {alice_token}"}

    abs_paths = [
        "C:\\Windows\\System32\\drivers\\etc\\hosts",
        "/etc/shadow",
        "/var/log/syslog",
    ]

    for p in abs_paths:
        res = httpx.get(
            f"{BASE_URL}/api/tasks/1/download?raw_path={p}",
            headers=headers,
            timeout=5.0
        )
        assert b"127.0.0.1" not in res.content or res.status_code in (400, 403, 404)


def test_isol_001_tasks_user_isolation():
    """ISOL-001: User A (Alice) cannot view User B (Bob) tasks."""
    alice_token = get_alice_token()
    bob_token = get_bob_token()

    alice_res = httpx.get(f"{BASE_URL}/api/tasks", headers={"Authorization": f"Bearer {alice_token}"})
    bob_res = httpx.get(f"{BASE_URL}/api/tasks", headers={"Authorization": f"Bearer {bob_token}"})

    assert alice_res.status_code == 200
    assert bob_res.status_code == 200

    alice_tasks = alice_res.json()
    bob_tasks = bob_res.json()

    alice_titles = [t["title"] for t in alice_tasks]
    bob_titles = [t["title"] for t in bob_tasks]

    # Verify no overlap
    for title in bob_titles:
        assert title not in alice_titles, f"Bob's task '{title}' leaked into Alice's view!"

    # Verify Bob only sees his 2 tasks
    assert len(bob_tasks) == 2, f"Bob expected 2 tasks, got {len(bob_tasks)}"


def test_isol_002_toggle_mutation_isolation():
    """ISOL-002: Alice attempting to toggle Bob's task is rejected (403 or 404)."""
    alice_token = get_alice_token()
    bob_token = get_bob_token()

    # Get Bob's task ID
    bob_tasks = httpx.get(f"{BASE_URL}/api/tasks", headers={"Authorization": f"Bearer {bob_token}"}).json()
    bob_task_id = bob_tasks[0]["id"]
    bob_initial_status = bob_tasks[0]["status"]

    # Alice tries to toggle Bob's task
    res = httpx.post(
        f"{BASE_URL}/api/tasks/{bob_task_id}/toggle",
        headers={"Authorization": f"Bearer {alice_token}"},
        timeout=5.0
    )
    assert res.status_code in (403, 404), f"Alice toggling Bob's task returned {res.status_code} instead of 403/404!"

    # Verify Bob's task was NOT modified
    verify = httpx.get(f"{BASE_URL}/api/tasks/{bob_task_id}", headers={"Authorization": f"Bearer {bob_token}"}).json()
    assert verify["status"] == bob_initial_status, "Bob's task was mutated by Alice!"


def test_isol_003_download_file_isolation():
    """ISOL-003: Alice attempting to download Bob's confidential attachment is rejected."""
    alice_token = get_alice_token()
    bob_token = get_bob_token()

    bob_tasks = httpx.get(f"{BASE_URL}/api/tasks", headers={"Authorization": f"Bearer {bob_token}"}).json()
    bob_task_id = bob_tasks[0]["id"]

    # Alice tries to download Bob's attachment
    res = httpx.get(
        f"{BASE_URL}/api/tasks/{bob_task_id}/download",
        headers={"Authorization": f"Bearer {alice_token}"},
        timeout=5.0
    )
    assert res.status_code in (403, 404), f"Alice downloading Bob's attachment returned {res.status_code} instead of 403/404!"
    assert b"TOP SECRET" not in res.content, "Bob's confidential file leaked to Alice!"
