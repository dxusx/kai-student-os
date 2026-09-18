"""
Authentication & User Identity Service for KAI Student OS.
Decouples Application Gateway Authentication (X-App-Token) from User Identity Authentication.

Provides:
- AuthenticatedUser dataclass
- Cryptographically signed user identity tokens (JWT with HMAC-SHA256)
- Token creation, verification, and decoding
- Tamper detection and expiration enforcement
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from fastapi import HTTPException

from core.config import settings


@dataclass(frozen=True)
class AuthenticatedUser:
    """Represents a verified student or administrative user identity."""
    id: str
    username: str
    role: str = "student"
    group_num: str = "5108"
    subgroup: int = 2

    @property
    def is_admin(self) -> bool:
        return self.role in ("admin", "superuser")

    @property
    def is_student(self) -> bool:
        return self.role == "student"

    def __str__(self) -> str:
        return self.id

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, AuthenticatedUser):
            return self.id == other.id
        if isinstance(other, str):
            return self.id == other
        return False

    def __hash__(self) -> int:
        return hash(self.id)


def _b64_encode(data: bytes) -> str:
    """URL-safe base64 encode without padding."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64_decode(data_str: str) -> bytes:
    """URL-safe base64 decode with padding restoration."""
    rem = len(data_str) % 4
    if rem > 0:
        data_str += "=" * (4 - rem)
    return base64.urlsafe_b64decode(data_str)


def _get_signing_key() -> bytes:
    """Obtain cryptographic secret key for signing user tokens."""
    seed = settings.app_auth_token or "kai_student_os_secure_key_2026_default"
    # Derive fixed 256-bit key
    return hashlib.sha256(f"kai_identity_salt::{seed}".encode("utf-8")).digest()


def create_user_token(
    user_id: str,
    username: Optional[str] = None,
    role: str = "student",
    group_num: str = "5108",
    subgroup: int = 2,
    expires_in_seconds: int = 86400 * 7,  # 7 days
) -> str:
    """
    Issue a cryptographically signed user identity token (JWT HMAC-SHA256).
    Binds current_user.id, role, and academic profile securely.
    """
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user_id).strip(),
        "username": (username or user_id).strip(),
        "role": role.strip(),
        "group_num": group_num.strip(),
        "subgroup": int(subgroup),
        "iat": now,
        "exp": now + expires_in_seconds,
    }

    header_bytes = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    encoded_header = _b64_encode(header_bytes)
    encoded_payload = _b64_encode(payload_bytes)

    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    sig = hmac.new(_get_signing_key(), signing_input, hashlib.sha256).digest()
    encoded_sig = _b64_encode(sig)

    return f"{encoded_header}.{encoded_payload}.{encoded_sig}"


def decode_user_token(token_str: str) -> AuthenticatedUser:
    """
    Validate signature, expiration, and format of a user identity token.
    Returns AuthenticatedUser or raises HTTPException(401).
    """
    clean_token = token_str.strip()
    if not clean_token:
        raise HTTPException(
            status_code=401,
            detail="Неавторизованный доступ: токен пользователя отсутствует",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = clean_token.split(".")
    if len(parts) != 3:
        raise HTTPException(
            status_code=401,
            detail="Неавторизованный доступ: некорректный формат токена пользователя",
            headers={"WWW-Authenticate": "Bearer"},
        )

    encoded_header, encoded_payload, encoded_sig = parts

    # 1. Verify cryptographic HMAC signature
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    expected_sig = hmac.new(_get_signing_key(), signing_input, hashlib.sha256).digest()

    try:
        provided_sig = _b64_decode(encoded_sig)
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Неавторизованный доступ: недействительная подпись токена",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not secrets.compare_digest(provided_sig, expected_sig):
        raise HTTPException(
            status_code=401,
            detail="Неавторизованный доступ: цифровая подпись токена не совпадает (попытка подделки)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Parse and validate payload
    try:
        payload_data = json.loads(_b64_decode(encoded_payload).decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Неавторизованный доступ: поврежденные данные токена",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Check expiration
    now = int(time.time())
    exp = payload_data.get("exp", 0)
    if exp < now:
        raise HTTPException(
            status_code=401,
            detail="Срок действия авторизационного токена пользователя истек",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token", error_description="The user token expired"'},
        )

    user_id = payload_data.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Неавторизованный доступ: токен не содержит идентификатора пользователя (sub)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthenticatedUser(
        id=str(user_id),
        username=str(payload_data.get("username", user_id)),
        role=str(payload_data.get("role", "student")),
        group_num=str(payload_data.get("group_num", "5108")),
        subgroup=int(payload_data.get("subgroup", 2)),
    )


def get_system_default_user() -> AuthenticatedUser:
    """Standard default student user for backward-compatible system operations."""
    return AuthenticatedUser(
        id="student_5108",
        username="student_5108",
        role="student",
        group_num="5108",
        subgroup=2,
    )
