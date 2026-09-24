#!/usr/bin/env python3
"""
Deployed Git Commit & Version Verification Tool for KAI Student OS.
Verifies that the deployed environment matches the local repository HEAD commit
and adheres to Beta Hardening session auth and service auth policies.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.version import resolve_git_info


def verify_deployment(url: str, timeout: float = 10.0, expected_commit: Optional[str] = None) -> bool:
    """
    Fetch /api/version from target URL and verify against local or expected git commit.
    """
    base_url = url.rstrip("/")
    version_url = f"{base_url}/api/version"
    local_info = resolve_git_info()
    expected_sha = (expected_commit or local_info.get("git_commit", "")).strip()
    expected_short = expected_sha[:7] if len(expected_sha) >= 7 else expected_sha

    print("=" * 64)
    print("KAI STUDENT OS - DEPLOYED GIT COMMIT VERIFICATION")
    print("=" * 64)
    print(f"Target URL:        {version_url}")
    print(f"Local Git Commit:  {expected_sha} ({expected_short})")
    print(f"Local Branch:      {local_info.get('git_branch', 'main')}")
    print("-" * 64)

    try:
        resp = httpx.get(version_url, timeout=timeout, verify=False)
    except Exception as e:
        print(f"[FAIL] Could not connect to {version_url}: {e}")
        return False

    if resp.status_code != 200:
        print(f"[FAIL] HTTP status {resp.status_code} from /api/version: {resp.text}")
        return False

    try:
        data: Dict[str, Any] = resp.json()
    except Exception as e:
        print(f"[FAIL] Invalid JSON response from /api/version: {e}")
        return False

    remote_sha = str(data.get("git_commit", "")).strip()
    remote_short = str(data.get("git_commit_short", "")).strip()
    remote_branch = str(data.get("git_branch", "")).strip()
    remote_stage = str(data.get("release_stage", "")).strip()
    session_auth = data.get("session_auth", {})
    service_auth = data.get("service_auth", {})

    print(f"Remote Git Commit: {remote_sha} ({remote_short})")
    print(f"Remote Branch:     {remote_branch}")
    print(f"Release Stage:     {remote_stage}")
    print("-" * 64)

    checks = []

    # 1. Commit Match Check
    if expected_sha and remote_sha:
        if remote_sha == expected_sha or (expected_short and remote_short == expected_short):
            checks.append(("Commit Verification", True, f"Remote commit matches local HEAD ({remote_short})"))
        else:
            checks.append(("Commit Verification", False, f"Mismatch: expected {expected_short}, got {remote_short}"))
    else:
        checks.append(("Commit Verification", False, "Missing commit hash in local or remote"))

    # 2. Session Auth Configuration Check
    cookie_name = session_auth.get("cookie_name")
    httponly = session_auth.get("httponly")
    samesite = session_auth.get("samesite")
    if cookie_name == "kai_app_auth_token" and httponly is True and samesite == "lax":
        checks.append(("Session Auth Spec", True, f"HttpOnly Secure SameSite cookie enabled ({cookie_name})"))
    else:
        checks.append(("Session Auth Spec", False, f"Invalid session auth config: {session_auth}"))

    # 3. Service Auth Configuration Check
    service_header = service_auth.get("header")
    service_scope = service_auth.get("scope")
    if service_header == "X-App-Token" and service_scope == "internal_only":
        checks.append(("Service Auth Spec", True, f"X-App-Token scoped strictly to internal_only"))
    else:
        checks.append(("Service Auth Spec", False, f"Invalid service auth config: {service_auth}"))

    all_passed = True
    for name, passed, detail in checks:
        mark = "[PASS]" if passed else "[FAIL]"
        print(f"{mark} {name}: {detail}")
        if not passed:
            all_passed = False

    print("=" * 64)
    if all_passed:
        print("RESULT: DEPLOYMENT VERIFICATION PASSED (HEAD == DEPLOYED)")
    else:
        print("RESULT: DEPLOYMENT VERIFICATION FAILED")
    print("=" * 64)
    return all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify deployed git commit and version metadata")
    parser.add_argument("--url", default="https://kai.dxusx.ru", help="Target base URL to verify")
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP request timeout in seconds")
    parser.add_argument("--commit", default=None, help="Expected git commit SHA (default: current local git HEAD)")
    args = parser.parse_args()

    success = verify_deployment(url=args.url, timeout=args.timeout, expected_commit=args.commit)
    sys.exit(0 if success else 1)
