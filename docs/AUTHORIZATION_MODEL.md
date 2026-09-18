# KAI Student OS — Authorization & Data Isolation Model

## 1. Executive Summary

This document establishes the security architecture and authorization model for **KAI Student OS (КАИ Ассистент 5108)**. It addresses the fundamental distinction between **Application Gateway Authentication** and **User Identity Authentication**, eliminates Insecure Direct Object References (IDOR / BOLA), and enforces strict data isolation across all student-owned resources.

---

## 2. App Authentication vs. User Authentication

| Dimension | Application Gateway Authentication (`X-App-Token`) | True User Identity Authentication (`AuthenticatedUser`) |
| :--- | :--- | :--- |
| **Scope** | Client verification / API Gateway boundary | Student identity boundary (`current_user.id`) |
| **Token Type** | Symmetric shared application secret (`settings.app_auth_token`) | Cryptographically signed HMAC-SHA256 User Token (`sub`, `role`, `iat`, `exp`) |
| **Transmission** | `X-App-Token` header, fallback Bearer, or gateway cookie | `Authorization: Bearer <jwt>`, `X-User-Token`, or `kai_user_token` cookie |
| **Spoofing Defense** | Prevents untrusted external internet clients from hitting backend | Prevents students from impersonating each other via arbitrary headers |
| **Resource Binding** | None (application-level) | Binds all CRUD, downloads, AI summaries, and stats to `current_user.id` |

> [!IMPORTANT]
> **Core Architectural Rule**:
> `X-App-Token` proves that a request originates from an authorized client instance. It **never** represents a student's personal identity. User identity is derived **strictly** from cryptographically signed tokens whose digital signature cannot be forged without the private server key. Raw headers such as `X-User-Id` are **rejected / ignored** for identity resolution unless issued under trusted server orchestration.

```
Incoming Request
    │
    ├─► [1] Check Session Expiry (X-Session-Expired / 'expired' marker)
    │
    ├─► [2] Token Extraction (Authorization: Bearer, X-User-Token, cookies)
    │       * Query parameters (?token=...) strictly rejected
    │
    ├─► [3] Is Token a Signed User JWT (3 dot-separated parts)?
    │       ├─► YES: Cryptographically verify HMAC-SHA256 signature & exp
    │       │        └─► current_user = AuthenticatedUser(id, username, role)
    │       └─► NO: Validate against Gateway Secret (app_auth_token)
    │                └─► Fallback to default student or trusted gateway user
    │
    ▼
Identity Established: current_user.id
    │
    ├─► /api/tasks: filter tasks WHERE owner_id == current_user.id
    ├─► /api/tasks/{id}: verify task.owner_id == current_user.id (403 on IDOR)
    ├─► /api/tasks/{id}/download: verify task.owner_id == current_user.id (403 on IDOR)
    ├─► /api/tasks/{id}/toggle: verify task.owner_id == current_user.id (403 on IDOR)
    ├─► /api/stats: aggregate ONLY current_user.id tasks
    ├─► /api/subjects: compute progress ONLY from current_user.id tasks
    ├─► /api/schedule: compute pending badges ONLY from current_user.id tasks
    └─► /api/ai/summarize-task/{id}: verify ownership + user-scoped cache
```

---

## 3. Cryptographic User Token Architecture

User tokens follow a compact URL-safe JWT structure:
`header.payload.signature`

1. **Header**: `{"alg": "HS256", "typ": "JWT"}`
2. **Payload**:
   ```json
   {
     "sub": "user_alice",
     "username": "alice",
     "role": "student",
     "group_num": "5108",
     "subgroup": 2,
     "iat": 1773800000,
     "exp": 1774404800
   }
   ```
3. **Cryptographic Signature**:
   $$\text{Signature} = \text{HMAC-SHA256}(K, \text{Header}_{\text{b64}} \mathbin{\Vert} \text{Payload}_{\text{b64}})$$
   where $K = \text{SHA256}(\text{"kai\_identity\_salt::"} \mathbin{\Vert} \text{seed})$.

### Security Guarantees:
- **Tamper Detection**: Any modification to `sub` (e.g. changing `user_alice` to `user_bob`) produces a signature mismatch $\to$ `HTTP 401 Unauthorized` (`secrets.compare_digest` prevents timing attacks).
- **Expiration Enforcement**: Tokens expired beyond `exp` timestamp are immediately rejected with `HTTP 401 Unauthorized`.
- **Query Parameter Prevention**: Tokens passed via `?token=...` in query strings are rejected to prevent exposure in proxy logs, browser histories, and referrer headers.

---

## 4. Student-Owned Resource Scoping & IDOR Defense Matrix

| Resource / Action | Endpoint | Scoping & Authorization Check | Non-Owner Result |
| :--- | :--- | :--- | :--- |
| **List Tasks** | `GET /api/tasks` | `owner_id == current_user.id` | Returns only caller's tasks (0 cross-user leak) |
| **Get Task Detail** | `GET /api/tasks/{id}` | `task.owner_id == current_user.id` or `is_admin` | `403 Forbidden` |
| **Toggle Task** | `POST /api/tasks/{id}/toggle` | `task.owner_id == current_user.id` or `is_admin` | `403 Forbidden` (Status unchanged) |
| **Download File** | `GET /api/tasks/{id}/download` | `task.owner_id == current_user.id` or `is_admin` | `403 Forbidden` (File content denied) |
| **Semester Stats** | `GET /api/stats` | Aggregated strictly for `owner_id == current_user.id` | Returns caller's stats only |
| **Subject Progress**| `GET /api/subjects` | Task counts calculated strictly for `current_user.id` | Returns caller's progress percentages |
| **Schedule Badges** | `GET /api/schedule` | Discipline debt badges counted strictly for `current_user.id` | Caller's debts only |
| **AI Lab Summary**  | `POST /api/ai/summarize-task/{id}` | Verified `task.owner_id == current_user.id`; cache key `f"{current_user.id}:{task_id}"` | `403 Forbidden` |
| **Token Issuance**  | `POST /api/auth/token` | Gateway/Admin authorized; binds new user record in DB | Issued signed token |
| **User Profile**    | `GET /api/auth/me` | Decodes verified `AuthenticatedUser` claims | Caller profile |

---

## 5. Verification & Test Evidence

Test verification was executed on live database fixtures using the dedicated authorization and security test suites.

### 5.1 Authorization & Isolation Suite (`tests/test_authorization_isolation.py`)
```bash
.venv\Scripts\python.exe tests/test_authorization_isolation.py
```
**Results (18 of 18 passed - 100%):**
1. `/api/auth/me` profile decoding $\to$ **PASS** (Alice & Bob identities verified)
2. User A: read own task $\to$ **PASS** (`HTTP 200 OK`)
3. User B: read User A task $\to$ **PASS** (`HTTP 403 Forbidden` - IDOR blocked)
4. User B: download User A attachment $\to$ **PASS** (`HTTP 403 Forbidden` - File access blocked)
5. User A: download own attachment $\to$ **PASS** (`HTTP 200 OK` - Content verified)
6. User B: toggle User A task status $\to$ **PASS** (`HTTP 403 Forbidden` - Status untouched)
7. User A: toggle own task status $\to$ **PASS** (`HTTP 200 OK` - Status updated & reverted)
8. User B: AI summarize User A task $\to$ **PASS** (`HTTP 403 Forbidden` - AI cross-tenant blocked)
9. User B: stats isolation $\to$ **PASS** (Bob sees exactly 1 task, Alice tasks hidden)
10. User A: stats isolation $\to$ **PASS** (Alice sees exactly 2 tasks)
11. User B: task listing scoping $\to$ **PASS** (Bob sees 1 task, 0% Alice data)
12. User A: task listing scoping $\to$ **PASS** (Alice sees 2 tasks, 0% Bob data)
13. Tampered token signature $\to$ **PASS** (`HTTP 401 Unauthorized` - Forgery detected)
14. Expired user token $\to$ **PASS** (`HTTP 401 Unauthorized` - Expiration enforced)
15. Nonexistent task ID $\to$ **PASS** (`HTTP 404 Not Found`)
16. Administrative role override $\to$ **PASS** (`HTTP 200 OK` for admin role)
17. Schedule personalization $\to$ **PASS** (Pending debts scoped to authenticated user)
18. Token issuance lifecycle $\to$ **PASS** (`POST /api/auth/token` + `/api/auth/me`)

### 5.2 Download Hardening Suite (`tests/test_download_security.py`)
```bash
.venv\Scripts\python.exe tests/test_download_security.py
```
**Results (13 of 13 passed - 100%):**
- Auth verification, query token rejection, ownership check, path traversal (`../`, `..\\`, `%2e%2e`), absolute paths, and sandboxing all validated.

### 5.3 System Regression Suites
- `test_security.py` $\to$ **PASS**
- `tests/test_api.py` $\to$ **PASS**
- `tests/test_database.py` $\to$ **PASS**
