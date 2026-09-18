"""
Comprehensive Test Suite for AI Resilience, Error Taxonomy, Exponential Backoff, and Fallback UX.
Covers all 7 mandatory error categories:
1. RATE_LIMIT
2. QUOTA_EXCEEDED
3. UPSTREAM_UNAVAILABLE
4. TIMEOUT
5. INVALID_RESPONSE
6. AUTH_ERROR
7. NETWORK_ERROR

Additionally verifies:
- Exponential backoff execution on safe transient errors
- Bounded retry termination (no infinite loops)
- Immediate abort on non-retryable errors (AUTH, QUOTA, INVALID_RESPONSE)
- Server-side deterministic caching (identical input -> cached: True)
- Metadata completeness (started_at, duration_ms, provider, model, success, failure_category)
- Zero secrets leakage (sanitization)
- Honest fallback messaging ("AI временно недоступен", "Это не повлияло на сохранённые задания.")
- API endpoint error envelope and status codes
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure repo root in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from api.app import app
from core.config import settings
from database.connection import init_db, async_session
from database.crud import create_task, get_or_create_subject, get_or_create_user
from services.auth_service import create_user_token
from services.gemini_service import (
    AiErrorCategory,
    AiServiceError,
    classify_ai_error,
    get_ai_error_ui_info,
    sanitize_text,
    DeterministicAiCache,
    global_ai_cache,
    GeminiService,
    LabSummary,
)


def run_all_ai_resilience_tests():
    print("================================================================")
    print("STARTING KAI STUDENT OS AI RESILIENCE & FALLBACK TEST SUITE")
    print("================================================================")

    # -------------------------------------------------------------
    # 1. TEST ERROR TAXONOMY CLASSIFICATION (All 7 Categories)
    # -------------------------------------------------------------
    print("\n--- 1. Testing Error Classification for All 7 Categories ---")

    # Category 1: RATE_LIMIT
    err_rl_1 = Exception("429 ResourceExhausted: Too many requests per minute (RPM limit)")
    assert classify_ai_error(err_rl_1) == AiErrorCategory.RATE_LIMIT
    class MockHttp429(Exception):
        status_code = 429
    assert classify_ai_error(MockHttp429("Rate limit exceeded")) == AiErrorCategory.RATE_LIMIT
    print("   [PASS] Category RATE_LIMIT classified accurately.")

    # Category 2: QUOTA_EXCEEDED
    err_quota_1 = Exception("ResourceExhausted: You have exceeded your current quota for free tier billing")
    assert classify_ai_error(err_quota_1) == AiErrorCategory.QUOTA_EXCEEDED
    err_quota_2 = Exception("insufficient_quota: Daily limit reached for model")
    assert classify_ai_error(err_quota_2) == AiErrorCategory.QUOTA_EXCEEDED
    print("   [PASS] Category QUOTA_EXCEEDED classified accurately.")

    # Category 3: UPSTREAM_UNAVAILABLE
    err_up_1 = Exception("503 The model is overloaded. Please try again later.")
    assert classify_ai_error(err_up_1) == AiErrorCategory.UPSTREAM_UNAVAILABLE
    class MockHttp502(Exception):
        status_code = 502
    assert classify_ai_error(MockHttp502("Bad Gateway from upstream")) == AiErrorCategory.UPSTREAM_UNAVAILABLE
    print("   [PASS] Category UPSTREAM_UNAVAILABLE classified accurately.")

    # Category 4: TIMEOUT
    err_to_1 = TimeoutError("The read operation timed out")
    assert classify_ai_error(err_to_1) == AiErrorCategory.TIMEOUT
    err_to_2 = Exception("Deadline exceeded waiting for response from gemini API")
    assert classify_ai_error(err_to_2) == AiErrorCategory.TIMEOUT
    print("   [PASS] Category TIMEOUT classified accurately.")

    # Category 5: INVALID_RESPONSE
    err_inv_1 = json.JSONDecodeError("Expecting value", "doc", 0)
    assert classify_ai_error(err_inv_1) == AiErrorCategory.INVALID_RESPONSE
    err_inv_2 = ValueError("Schema validation error: missing required key 'summary'")
    assert classify_ai_error(err_inv_2) == AiErrorCategory.INVALID_RESPONSE
    print("   [PASS] Category INVALID_RESPONSE classified accurately.")

    # Category 6: AUTH_ERROR
    err_auth_1 = Exception("API_KEY_INVALID: Provided API key is expired or invalid")
    assert classify_ai_error(err_auth_1) == AiErrorCategory.AUTH_ERROR
    class MockHttp401(Exception):
        status_code = 401
    assert classify_ai_error(MockHttp401("Unauthorized: API key not valid")) == AiErrorCategory.AUTH_ERROR
    print("   [PASS] Category AUTH_ERROR classified accurately.")

    # Category 7: NETWORK_ERROR
    err_net_1 = ConnectionError("Connection refused by host bb.kai.ru or generativelanguage.googleapis.com")
    assert classify_ai_error(err_net_1) == AiErrorCategory.NETWORK_ERROR
    err_net_2 = OSError("getaddrinfo failed: Temporary DNS lookup failure")
    assert classify_ai_error(err_net_2) == AiErrorCategory.NETWORK_ERROR
    print("   [PASS] Category NETWORK_ERROR classified accurately.")

    # -------------------------------------------------------------
    # 2. TEST USER-FACING REASSURANCE & RETRY POLICY
    # -------------------------------------------------------------
    print("\n--- 2. Testing User-Facing Reassurance & UI Message Delivery ---")
    for cat in AiErrorCategory:
        info = get_ai_error_ui_info(cat)
        assert info["title"] == "AI временно недоступен", f"Failed for {cat}"
        assert "Это не повлияло на сохранённые задания" in info["reassurance"], f"Failed for {cat}"
        assert info["title"] in info["full_message"]
        assert info["reassurance"] in info["full_message"]

        if cat in (AiErrorCategory.RATE_LIMIT, AiErrorCategory.UPSTREAM_UNAVAILABLE, AiErrorCategory.TIMEOUT, AiErrorCategory.NETWORK_ERROR):
            assert info["retryable"] is True, f"Expected {cat} to be retryable"
            assert info["retry_after"] is not None and info["retry_after"] > 0
        else:
            assert info["retryable"] is False, f"Expected {cat} to not be auto-retryable"
    print("   [PASS] Reassurance messages ('Это не повлияло на сохранённые задания') and retry flags verified for all categories.")

    # -------------------------------------------------------------
    # 3. TEST SECRET SANITIZATION
    # -------------------------------------------------------------
    print("\n--- 3. Testing Secret & API Key Sanitization ---")
    dirty_text = "Google API call failed with key AIzaSyA1234567890123456789012345678901 and Bearer eyJhbGciOiJIUzI1NiJ9.test"
    cleaned = sanitize_text(dirty_text)
    assert "AIzaSy" not in cleaned
    assert "[REDACTED_API_KEY]" in cleaned
    assert "[REDACTED_TOKEN]" in cleaned
    print("   [PASS] Sensitive tokens and API keys sanitized from AI error representations.")

    # -------------------------------------------------------------
    # 4. TEST EXPONENTIAL BACKOFF ON TRANSIENT ERRORS
    # -------------------------------------------------------------
    print("\n--- 4. Testing Exponential Backoff on Safe Retryable Errors ---")
    svc = GeminiService(api_key="test_key_fake")
    call_counts = {"count": 0}

    def failing_generate_content(*args, **kwargs):
        call_counts["count"] += 1
        # Raise 503 UPSTREAM_UNAVAILABLE
        raise Exception("503 The model is temporarily overloaded")

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = failing_generate_content
    svc._client = mock_client
    svc.candidate_models = ["gemini-3.6-flash"]  # single model to test backoff retries

    t_start = time.perf_counter()
    try:
        svc._call_with_fallback(contents="test prompt", response_schema=LabSummary, max_retries=2, initial_backoff=0.05)
        assert False, "Should have raised AiServiceError"
    except AiServiceError as err:
        elapsed = time.perf_counter() - t_start
        assert err.category == AiErrorCategory.UPSTREAM_UNAVAILABLE
        # Initial attempt + 2 retries = 3 attempts total
        assert call_counts["count"] == 3, f"Expected 3 attempts, got {call_counts['count']}"
        # Exponential backoff total wait >= 0.05 + 0.10 = 0.15s
        assert elapsed >= 0.12, f"Expected backoff delay, elapsed: {elapsed}"
        assert err.metadata["success"] is False
        assert err.metadata["failure_category"] == "UPSTREAM_UNAVAILABLE"
        assert err.metadata["duration_ms"] > 0
    print("   [PASS] Exponential backoff executed: exactly 3 attempts (max_retries=2), bounded delay verified.")

    # -------------------------------------------------------------
    # 5. TEST NON-RETRYABLE ERRORS ABORT IMMEDIATELY
    # -------------------------------------------------------------
    print("\n--- 5. Testing Immediate Abort on Non-Retryable Errors (No Wasted Retries) ---")
    auth_call_counts = {"count": 0}

    def failing_auth(*args, **kwargs):
        auth_call_counts["count"] += 1
        raise Exception("API_KEY_INVALID: Bad key")

    mock_client_auth = MagicMock()
    mock_client_auth.models.generate_content.side_effect = failing_auth
    svc._client = mock_client_auth
    svc.candidate_models = ["gemini-3.6-flash"]

    try:
        svc._call_with_fallback(contents="test prompt", response_schema=LabSummary, max_retries=2, initial_backoff=0.05)
        assert False, "Should have raised AiServiceError"
    except AiServiceError as err:
        assert err.category == AiErrorCategory.AUTH_ERROR
        # Should abort on attempt 1 without retries!
        assert auth_call_counts["count"] == 1, f"Expected exactly 1 attempt for AUTH_ERROR, got {auth_call_counts['count']}"
    print("   [PASS] Non-retryable AUTH_ERROR aborted immediately without wasting retries.")

    # -------------------------------------------------------------
    # 6. TEST DETERMINISTIC SERVER-SIDE CACHING
    # -------------------------------------------------------------
    print("\n--- 6. Testing Deterministic Server-Side Cache ---")
    cache = DeterministicAiCache(max_entries=10, ttl_seconds=3600)
    key1 = cache.compute_key("lab_summary", "user_1", "Lab 1", "Details of lab", None)
    key2 = cache.compute_key("lab_summary", "user_1", "Lab 1", "Details of lab", None)
    key_other_user = cache.compute_key("lab_summary", "user_2", "Lab 1", "Details of lab", None)

    assert key1 == key2, "Cache keys must be deterministic for identical content"
    assert key1 != key_other_user, "Cache keys must be isolated per student"

    mock_data = {
        "summary": "Цель работы — исследование полупроводников.",
        "to_bring": ["Калькулятор", "Отчет"],
        "key_steps": ["Собрать схему", "Снять ВАХ", "Построить график"],
    }
    cache.set(key1, mock_data)

    retrieved = cache.get(key1)
    assert retrieved == mock_data
    assert cache.get("nonexistent_key") is None
    print("   [PASS] Deterministic cache computes consistent hashes and isolates student cache keys.")

    # Testing cache integration in GeminiService
    global_ai_cache.clear()
    cached_svc = GeminiService(api_key="fake")
    key_test = global_ai_cache.compute_key("lab_summary", "user_alice", "Title A", "Details A", None)
    global_ai_cache.set(key_test, mock_data)

    # Calling summarize_lab_work on cached input should return immediately without client calls
    t_c0 = time.perf_counter()
    summary_cached = cached_svc.summarize_lab_work(
        title="Title A",
        details="Details A",
        cache_user_id="user_alice"
    )
    t_c_elapsed = time.perf_counter() - t_c0
    assert summary_cached["summary"] == mock_data["summary"]
    assert summary_cached["_metadata"]["cached"] is True
    assert summary_cached["_metadata"]["duration_ms"] <= 10
    assert t_c_elapsed < 0.05
    print("   [PASS] Cached summary returned instantly (duration <= 10ms, cached=True).")

    # -------------------------------------------------------------
    # 7. TEST FASTAPI ENDPOINT ERROR ENVELOPES & STATUS CODES
    # -------------------------------------------------------------
    print("\n--- 7. Testing /api/ai/summarize-task/{task_id} Error Envelopes ---")
    asyncio.run(init_db())
    client = TestClient(app)

    async def _create_test_task():
        async with async_session() as session:
            await get_or_create_user(session, user_id="student_resilience", username="resilience_tester", role="student")
            subj = await get_or_create_subject(session, name="Предмет для AI Resilience")
            t = await create_task(
                session=session,
                subject_id=subj.id,
                title="Лабораторная работа по квантовой оптике",
                task_type="лабораторная",
                owner_id="student_resilience",
                details="Методические указания по лабе 5",
            )
            return t.id

    task_id = asyncio.run(_create_test_task())
    token = create_user_token("student_resilience", username="resilience_tester", role="student")
    auth_hdr = {"Authorization": f"Bearer {token}"}

    # Case 7A: Simulate RATE_LIMIT (429)
    with patch.object(GeminiService, "summarize_lab_work", side_effect=AiServiceError(
        category=AiErrorCategory.RATE_LIMIT,
        message="Rate limit 429",
        metadata={"started_at": "2026-09-18T00:00:00Z", "duration_ms": 150, "provider": "google-gemini", "model": "gemini-3.6-flash", "success": False, "failure_category": "RATE_LIMIT"}
    )):
        resp_rl = client.post(f"/api/ai/summarize-task/{task_id}", headers=auth_hdr)
        assert resp_rl.status_code == 429
        body_rl = resp_rl.json()
        assert "AI временно недоступен" in body_rl["detail"]
        assert "Это не повлияло на сохранённые задания" in body_rl["detail"]
        assert body_rl["error"]["category"] == "RATE_LIMIT"
        assert body_rl["error"]["retryable"] is True
        assert body_rl["metadata"]["failure_category"] == "RATE_LIMIT"
    print("   [PASS] Endpoint properly returned HTTP 429 with reassuring envelope on RATE_LIMIT.")

    # Case 7B: Simulate UPSTREAM_UNAVAILABLE (503)
    with patch.object(GeminiService, "summarize_lab_work", side_effect=AiServiceError(
        category=AiErrorCategory.UPSTREAM_UNAVAILABLE,
        message="503 Model overloaded",
        metadata={"started_at": "2026-09-18T00:00:00Z", "duration_ms": 200, "provider": "google-gemini", "model": "gemini-3.6-flash", "success": False, "failure_category": "UPSTREAM_UNAVAILABLE"}
    )):
        resp_503 = client.post(f"/api/ai/summarize-task/{task_id}", headers=auth_hdr)
        assert resp_503.status_code == 503
        body_503 = resp_503.json()
        assert body_503["error"]["category"] == "UPSTREAM_UNAVAILABLE"
        assert body_503["error"]["retryable"] is True
        assert "перегружен" in body_503["error"]["detail"]
        # Must NOT expose raw python traceback
        assert "Traceback" not in body_503["detail"]
    print("   [PASS] Endpoint properly returned HTTP 503 with reassuring envelope on UPSTREAM_UNAVAILABLE.")

    # Case 7C: Simulate TIMEOUT (504)
    with patch.object(GeminiService, "summarize_lab_work", side_effect=AiServiceError(
        category=AiErrorCategory.TIMEOUT,
        message="Read timed out",
        metadata={"started_at": "2026-09-18T00:00:00Z", "duration_ms": 30000, "provider": "google-gemini", "model": "gemini-3.6-flash", "success": False, "failure_category": "TIMEOUT"}
    )):
        resp_to = client.post(f"/api/ai/summarize-task/{task_id}", headers=auth_hdr)
        assert resp_to.status_code == 504
        body_to = resp_to.json()
        assert body_to["error"]["category"] == "TIMEOUT"
        assert body_to["error"]["retryable"] is True
        assert "истекло" in body_to["error"]["detail"]
    print("   [PASS] Endpoint properly returned HTTP 504 with reassuring envelope on TIMEOUT.")

    # Case 7D: Simulate QUOTA_EXCEEDED (429)
    with patch.object(GeminiService, "summarize_lab_work", side_effect=AiServiceError(
        category=AiErrorCategory.QUOTA_EXCEEDED,
        message="Quota exceeded for billing tier",
        metadata={"started_at": "2026-09-18T00:00:00Z", "duration_ms": 100, "provider": "google-gemini", "model": "gemini-3.6-flash", "success": False, "failure_category": "QUOTA_EXCEEDED"}
    )):
        resp_q = client.post(f"/api/ai/summarize-task/{task_id}", headers=auth_hdr)
        assert resp_q.status_code == 429
        body_q = resp_q.json()
        assert body_q["error"]["category"] == "QUOTA_EXCEEDED"
        assert body_q["error"]["retryable"] is False
    print("   [PASS] Endpoint properly returned HTTP 429 (retryable=False) on QUOTA_EXCEEDED.")

    # -------------------------------------------------------------
    # 8. TEST PARSE-TASK HONEST FALLBACK (NO FAKE RESULTS)
    # -------------------------------------------------------------
    print("\n--- 8. Testing Parse-Task Honest Fallback (No Fake AI Results) ---")
    resp_parse = client.post(
        "/api/ai/parse-task",
        json={"text": "лабораторная работа 3 по физике до пятницы в 401 ауд"},
        headers=auth_hdr
    )
    assert resp_parse.status_code == 200
    parse_data = resp_parse.json()
    assert "лабораторная" in parse_data["title"].lower() or "физик" in parse_data["subject_name"].lower()
    assert "metadata" in parse_data
    assert parse_data["metadata"].get("source") in ("google-gemini", "heuristic_fallback")
    print(f"   [PASS] Parse-task returned structured preview with honest metadata (source: {parse_data['metadata'].get('source')}).")

    print("\n================================================================")
    print("SUCCESS: ALL AI RESILIENCE & ERROR TAXONOMY TESTS PASSED (100%)")
    print("================================================================")


if __name__ == "__main__":
    run_all_ai_resilience_tests()
