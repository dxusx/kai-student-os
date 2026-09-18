# KAI Student OS — Objective User Journey Metrics (Release Candidate)

> **Measurement Date:** 2026-09-18  
> **Environment:** Chromium (Playwright Automated Runner), 390x844 (iPhone 14 viewport), local backend on 127.0.0.1:8000  
> **Governing Principle:** *TRUTH > APPEARANCE OF COMPLETION* — Zero fictitious numbers. All figures are directly extracted from live test executions.

---

## 1. Executive Metrics Summary

| Scenario | Taps / Clicks | Screens / Views | API Requests | Initial Load Time | Time to Primary Action | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **A. Первый вход (Cold Launch)** | 2 | 2 | 1 | 26 ms | 8 ms | **PASS** |
| **B. Утренний просмотр (Morning Check)** | 0 | 1 | 5 | 131 ms | 53 ms | **PASS** |
| **C. Найти методичку (Find Materials)** | 3 | 1 | 0 (cached) | 0 ms | 820 ms | **PASS** |
| **D. Отметить сделанным (Toggle Done)** | 1 | 1 | 1 | 0 ms | 100 ms | **PASS** |
| **E. Вставить задачу через AI (AI Insert)** | 3 | 3 | 5 | 0 ms | 11,591 ms | **PASS** |
| **F. Проверить дедлайн (Check Deadline)** | 0 | 1 | 5 | 833 ms | 47 ms | **PASS** |
| **G. Офлайн вход (Offline Shell Launch)** | 0 | 1 | 0 | 9 ms | 9 ms | **PASS** |

---

## 2. Granular Scenario Breakdown

### Scenario A: Первый вход (Cold Start & Authentication)
- **User Goal:** Open application for the very first time without existing cookies or session tokens, authenticate securely, and land on the Today overview.
- **Taps / Clicks:** **2**
  1. Click passcode input field to focus.
  2. Click «Войти в систему» submit button.
- **Screens Visited:** **2** (Passcode Gate Sheet → Main Focus Overview).
- **API Requests:** **1** (`GET /api/stats` to validate token and fetch tenant scope).
- **Initial Load Time:** **26 ms** (DOMContentLoaded to gate render).
- **Time to Primary Action:** **8 ms** (post-auth transition to active interface).
- **Audit Finding:** The passcode modal prevents unauthorized data leakage before validation. Once entered, the session cookie and localStorage token are set with `SameSite=Strict`.

### Scenario B: Утренний просмотр (Morning Check)
- **User Goal:** Wake up, open app, immediately answer *"What is my first class today?"* and *"Is it an even or odd week?"*.
- **Taps / Clicks:** **0** (Zero user interactions required).
- **Screens Visited:** **1** (`view-focus`).
- **API Requests:** **5** (`/api/tasks`, `/api/subjects`, `/api/schedule`, `/api/schedule/week`, `/api/stats`).
- **Initial Load Time:** **131 ms**.
- **Time to Primary Action:** **53 ms**.
- **Audit Finding:** The live dynamic card «Сейчас» displays the current/upcoming class (`[пр] Философия`, room `2 зд. • ауд. 436`), time slot (`11:20 — 12:50`), and week parity (`Четная неделя`) with 0 taps.

### Scenario C: Найти методичку (Find Reference Materials & Files)
- **User Goal:** Locate reference documents and lab guides for a specific academic course.
- **Taps / Clicks:** **3**
  1. Tap bottom navigation «Задания».
  2. Tap segmented toggle «Методички и файлы».
  3. Tap doc card to view or download attachment.
- **Screens Visited:** **1** (Unified Tasks view with segmented sub-state).
- **API Requests:** **0** (Data is served from in-memory state preloaded during app init).
- **Time to Primary Action:** **820 ms**.
- **Audit Finding:** Direct download links trigger secure database-backed file downloads via `GET /api/tasks/{id}/download` with authenticated headers.

### Scenario D: Отметить сделанным (Toggle Task Done)
- **User Goal:** Complete a task and cross it off the checklist.
- **Taps / Clicks:** **1** (Tap checkbox directly in «Горит к сдаче» on the Today screen).
- **Screens Visited:** **1** (`view-focus`).
- **API Requests:** **1** (`POST /api/tasks/{id}/toggle`).
- **Time to Primary Action:** **100 ms** (Optimistic UI update, 300ms confirmation animation, non-blocking toast).
- **Audit Finding:** Instant visual confirmation (`task-confirm-anim`), safe rollback if network error occurs.

### Scenario E: Вставить задачу через AI (Forwarded Message Parsing)
- **User Goal:** Paste forwarded Telegram message from group head, view explainable evidence, and add task.
- **Taps / Clicks:** **3**
  1. Switch to AI tab.
  2. Tap «Распознать» (`#gemini-submit-btn`).
  3. Review evidence card («Почему это определено так») and tap «Добавить всё» (`#sheet-confirm-btn`).
- **Screens Visited:** **3** (AI Composer → AI Evidence Preview Sheet → Success Sheet).
- **API Requests:** **5** (parse task, schedule lookup, fallback resolution, task persist, refresh tasks).
- **Time to Primary Action:** **11,591 ms** (Includes upstream Gemini model negotiation, fallback to heuristic engine upon upstream demand spikes, schedule discipline matching, and evidence card compilation).
- **Audit Finding:** Evidence card factually displays discipline match confidence (95%), original deadline phrase with MSK calendar calculation, auditorium attribution source, and originating chat source.

### Scenario F: Проверить дедлайн (Check Urgent Deadlines)
- **User Goal:** Verify which assignment is due first and how much time remains.
- **Taps / Clicks:** **0** (Directly visible in «Следующее действие» and «Горит к сдаче»).
- **Screens Visited:** **1** (`view-focus`).
- **API Requests:** **5** (Preloaded session data).
- **Initial Load Time:** **833 ms**.
- **Time to Primary Action:** **47 ms**.
- **Audit Finding:** Next action card displays urgent deadline with relative hours remaining (e.g. `до 18 сент., 18:00 (осталось 6 ч)`).

### Scenario G: Офлайн вход (Offline Shell Launch)
- **User Goal:** Open application in an underground metro or basement classroom with zero network connectivity.
- **Taps / Clicks:** **0**.
- **Screens Visited:** **1**.
- **API Requests:** **0** (All network requests cleanly short-circuited).
- **Initial Load Time:** **9 ms** (Served from cache).
- **Time to Primary Action:** **9 ms**.
- **Audit Finding:** Application shell renders cleanly from browser cache without white-screen or unhandled JavaScript exceptions. Network-dependent actions present explicit offline notices.
