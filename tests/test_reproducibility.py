"""
Unit and integration tests for QA reproducibility and verification requirements.
"""
from pathlib import Path
import os
import pytest
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_reproducibility_documentation_present():
    """Verify that docs/QA_REPRODUCIBILITY.md exists and contains audit details."""
    doc_path = REPO_ROOT / "docs" / "QA_REPRODUCIBILITY.md"
    assert doc_path.exists(), "docs/QA_REPRODUCIBILITY.md must exist"
    content = doc_path.read_text(encoding="utf-8")
    assert "Verification Table" in content
    assert "scripts/run_full_qa.py" in content
    assert "docs/FUNCTION_INVENTORY.md" in content
    assert "Clean Checkout" in content


def test_required_qa_files_exist():
    """Verify that all core QA and documentation files exist in the repository."""
    required_files = [
        "scripts/run_full_qa.py",
        "docs/FUNCTION_INVENTORY.md",
        "docs/FULL_QA_REPORT.md",
        "docs/FULL_QA_FIX_PLAN.md",
        "docs/UX_METRICS.md",
        "docs/REAL_DEVICE_CHECKLIST.md",
        "tests/test_download_security.py",
        "tests/test_authorization_isolation.py",
        "tests/test_ai_resilience.py",
        "tests/qa/test_sw_security.py",
        ".github/workflows/qa.yml",
    ]
    for rel_path in required_files:
        p = REPO_ROOT / rel_path
        assert p.exists(), f"Required file missing: {rel_path}"


def test_service_worker_does_not_cache_api_routes():
    """Verify that static/sw.js explicitly forbids caching of API and auth endpoints."""
    sw_path = REPO_ROOT / "static" / "sw.js"
    assert sw_path.exists(), "static/sw.js must exist"
    content = sw_path.read_text(encoding="utf-8")
    assert "/api/" in content
    assert "/auth/" in content
    assert "isStaticAsset" in content


def test_live_mode_flags_and_status_structure():
    """Verify that run_full_qa parses live parameters and respects missing credentials."""
    from scripts.run_full_qa import run_live_smoke_check

    # When env vars are unset, services should report BLOCKED or NOT VERIFIED, not PASS
    with patch.dict(os.environ, {}, clear=True):
        status = run_live_smoke_check(
            base_url="http://127.0.0.1:8899",
            token="test-token",
            allow_mutations=False
        )
        assert isinstance(status, dict)
        for service, outcome in status.items():
            assert outcome["status"] in ("BLOCKED", "NOT VERIFIED", "FAIL", "LIVE", "PASS")
            # Ensure none of the uncredentialed external services falsely report PASS
            if service in ("Blackboard", "Gemini", "Telegram"):
                assert outcome["status"] != "PASS"
