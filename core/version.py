"""
Build, version, and git commit metadata provider for KAI Student OS.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent

APP_VERSION = "2.0.0"
RELEASE_STAGE = "beta"

_BUILD_INFO: Optional[Dict[str, Any]] = None


def resolve_git_info() -> Dict[str, Any]:
    """Resolve current git commit SHA, short SHA, branch, and commit timestamp."""
    global _BUILD_INFO
    if _BUILD_INFO is not None:
        return _BUILD_INFO

    commit_hash = os.environ.get("GIT_COMMIT", "").strip()
    branch = os.environ.get("GIT_BRANCH", "").strip()
    commit_date = os.environ.get("BUILD_DATE", "").strip()
    commit_subject = ""

    # Attempt git command lookup if in repository
    try:
        if (REPO_ROOT / ".git").exists():
            # 1. Full commit SHA
            res_sha = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            if res_sha.returncode == 0 and res_sha.stdout.strip():
                commit_hash = res_sha.stdout.strip()

            # 2. Branch name
            res_branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            if res_branch.returncode == 0 and res_branch.stdout.strip():
                branch = res_branch.stdout.strip()

            # 3. Commit date & subject
            res_log = subprocess.run(
                ["git", "log", "-1", "--format=%cd|%s", "--date=iso"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            if res_log.returncode == 0 and res_log.stdout.strip():
                parts = res_log.stdout.strip().split("|", 1)
                commit_date = parts[0]
                if len(parts) > 1:
                    commit_subject = parts[1]
    except Exception:
        pass

    # Fallback to .git_commit file if present
    git_file = REPO_ROOT / ".git_commit"
    if not commit_hash and git_file.exists():
        try:
            commit_hash = git_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    if not commit_hash:
        commit_hash = "unknown_commit"
    if not branch:
        branch = "main"

    short_hash = commit_hash[:7] if len(commit_hash) >= 7 else commit_hash

    _BUILD_INFO = {
        "version": APP_VERSION,
        "release_stage": RELEASE_STAGE,
        "git_commit": commit_hash,
        "git_commit_short": short_hash,
        "git_branch": branch,
        "commit_date": commit_date,
        "commit_subject": commit_subject,
    }
    return _BUILD_INFO


def get_version_payload() -> Dict[str, Any]:
    """Construct standard payload for GET /api/version."""
    info = resolve_git_info()
    return {
        "app": "KAI Student OS",
        "version": info["version"],
        "release_stage": info["release_stage"],
        "git_commit": info["git_commit"],
        "git_commit_short": info["git_commit_short"],
        "git_branch": info["git_branch"],
        "commit_date": info["commit_date"],
        "commit_subject": info["commit_subject"],
        "session_auth": {
            "type": "cookie",
            "cookie_name": "kai_app_auth_token",
            "httponly": True,
            "samesite": "lax",
            "secure": True,
        },
        "service_auth": {
            "header": "X-App-Token",
            "scope": "internal_only",
        },
    }
