# KAI Student OS — QA Reproducibility & Audit Guide

This document guarantees that all QA test suites, verification scripts, reports, and evidence are 100% reproducible from a fresh clone of the GitHub repository.

---

## 1. Repository State Verification Table

Audit of all files required for quality assurance, automated test execution, and metrics reporting:

| File Path | Exists Locally | Exists in Git | Committed | Pushed | Role & Description |
|---|---|---|---|---|---|
| `scripts/run_full_qa.py` | Yes | Yes | Yes | Yes | Master automated QA runner (Playwright + Unit + Reports) |
| `docs/FUNCTION_INVENTORY.md` | Yes | Yes | Yes | Yes | Complete 63-point functional matrix with status |
| `docs/FULL_QA_REPORT.md` | Yes | Yes | Yes | Yes | Automated execution report across 103 items |
| `docs/FULL_QA_FIX_PLAN.md` | Yes | Yes | Yes | Yes | Prioritized remediation & security hardening plan |
| `docs/UX_METRICS.md` | Yes | Yes | Yes | Yes | Quantitative UX audit & performance benchmarks |
| `docs/REAL_DEVICE_CHECKLIST.md` | Yes | Yes | Yes | Yes | Physical device & browser viewport validation |
| `tests/test_download_security.py` | Yes | Yes | Yes | Yes | 13-point security test for file downloads & path traversal |
| `tests/test_authorization_isolation.py` | Yes | Yes | Yes | Yes | 18-point multi-tenant isolation & JWT security tests |
| `tests/test_ai_resilience.py` | Yes | Yes | Yes | Yes | AI pipeline resilience, timeout, and error fallback tests |
| `scratch/qa_journey_runner.py` | Yes | Yes | Yes | Yes | Automated 13-step student user journey emulator |
| `scratch/measure_ux_metrics.py` | Yes | Yes | Yes | Yes | FCP, LCP, CLS, FID and DOM complexity measurement tool |
| `scratch/run_viewport_qa.py` | Yes | Yes | Yes | Yes | Multi-viewport screenshot & responsive test runner |

*Note: Scratch utilities were preserved in `scratch/` to allow full reproduction of previous UX and journey audit runs.*

---

## 2. Clean Checkout Reproduction Protocol

To reproduce the complete test suite on a completely fresh machine or environment:

### Step 1: Clone Repository
```bash
git clone https://github.com/mrvitaliy555/kai-student-os.git
cd kai-student-os
```

### Step 2: Create & Activate Virtual Environment
```bash
python -m venv .venv

# On Linux / macOS:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### Step 3: Install All Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
```

### Step 4: Run the Pytest Unit & Security Test Suites
```bash
pytest tests/ -v
```
Verifies database integrity, CRUD operations, authorization isolation, download security, AI resilience, parser logic, and scheduler crons.

### Step 5: Run the Master End-to-End QA Runner
```bash
python scripts/run_full_qa.py --mode local
```

Parameters:
- `--mode local`: Uses isolated sandbox database (`data/test_qa/kai_qa.db`) and deterministic mock services. Zero external network calls required.
- `--headless` (default): Runs Chromium in headless mode.
- `--headed`: Runs Chromium with visible browser window.
- `--feature <filter>`: Runs a subset of tests matching a specific feature or domain.
- `--keep-test-data`: Retains `data/test_qa/` artifacts after the run.

---

## 3. Service Worker Security & Offline Multi-User Isolation

### Architectural Protection
1. **CacheStorage Partitioning (`static/sw.js`):**
   - **Static Assets ONLY:** `/`, `/index.html`, `/login.html`, `/manifest.json`, CSS, JS, fonts, and images are cached for offline application shell loading.
   - **Authenticated APIs NEVER Cached:** Requests to `/api/*`, `/auth/*`, and `/files/*` strictly bypass `CacheStorage`. The Service Worker enforces network-only routing for all API endpoints.

2. **User-Keyed Offline Storage (`static/app.js`):**
   - Offline data caching uses `IndexedDB` (`kai_offline_store`).
   - Every cached record is keyed by the user identity: `${userKey}:tasks`, `${userKey}:schedule`.
   - When a user logs out (`clearAuthToken()`), memory state is cleared immediately.
   - If User B subsequently opens the application in offline mode, User B's lookup key (`user_bob:*`) yields no data or only Bob's own previously cached data, guaranteeing that User B **never receives User A's data**.

### Automated Verification
The test `tests/qa/test_sw_security.py` (and test ID `PWA-005` in `run_full_qa.py`) validates this:
1. Logs in as User A (Alice).
2. Requests protected `/api/tasks`.
3. Asserts `CacheStorage` has 0 `/api/` entries.
4. Logs out User A.
5. Logs in as User B (Bob).
6. Disconnects network (`set_offline(True)`).
7. Requests `/api/tasks`.
8. Asserts that none of Alice's tasks are exposed to Bob.
9. Confirms `IndexedDB` records use partitioned user keys.

---

## 4. Live Smoke Mode (`--mode live`)

For staging/production smoke testing against real services:
```bash
python scripts/run_full_qa.py --mode live
```

### Environment Variables Supported:
- `E2E_BASE_URL`: Base URL of the live deployment (e.g. `http://localhost:8000` or production domain).
- `E2E_AUTH_TOKEN`: Bearer token for authorized requests.
- `BB_LOGIN` & `BB_PASSWORD`: Credentials for live Blackboard authentication.
- `GEMINI_API_KEY`: API key for Google Gemini model calls.
- `BOT_TOKEN`: Telegram bot token for health verification.

### Safety & Integrity Rules:
- **No Hardcoded Secrets:** No tokens or passwords are committed to the codebase or displayed in logs.
- **Production Mutation Protection:** In `--mode live`, state-mutating requests (such as task creation, deletion, or toggles) are skipped and marked as `NOT VERIFIED` unless the explicit `--allow-production-mutation` flag is provided.
- **Clear Status Reporting:** For each external service, the runner displays one of:
  - `PASS`: Service reached, authenticated, and functioning properly.
  - `BLOCKED`: Required credentials not provided in the environment (never marked as PASS).
  - `NOT VERIFIED`: Service unreachable or non-critical test skipped.
  - `FAIL`: Service returned an error during live invocation.

---

## 5. GitHub Actions Continuous Integration

The workflow is defined at [`.github/workflows/qa.yml`](file:///e:/kai_assistant/.github/workflows/qa.yml):
- **Triggers:** Every `push` and `pull_request` to `main` and `master`.
- **Environment:** Ubuntu Linux with Python 3.11 and Playwright Chromium.
- **Execution:** Runs the complete suite of pytest unit/security tests followed by `python scripts/run_full_qa.py --mode local`.
- **Artifacts:** Automatically uploads `artifacts/qa/` (screenshots) and generated test reports.

---

## 6. Git Safety Audit

A rigorous check of git-tracked files (`git ls-files`) confirms that no sensitive files are present in version control:
- No `.env` or `.env.*` files (only `.env.example`).
- No SQLite database files (`*.db`, `*.sqlite`, `*.sqlite3`).
- No session files (`bb_session.json`).
- No private tokens or keys.
- All persistent runtime state is confined to `data/` (ignored by `.gitignore`).
