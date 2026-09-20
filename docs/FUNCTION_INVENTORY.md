# KAI Student OS — Complete Function Inventory

This inventory documents all verifiable capabilities, endpoints, user interface controls, background processes, security guarantees, and edge cases across KAI Student OS.

Governing Axiom: **EXECUTE → ASSERT → REPORT**
Initial Status: `NOT_RUN` (unless `MANUAL_ONLY` for non-headless physical hardware requirements).

| ID | Area | Feature | Entry point | API/service | Mutation? | Expected result | Automatable? | External dependency? | Test status |
|---|---|---|---|---|---|---|---|---|---|
| AUTH-001 | Web Auth | Health check endpoint | HTTP GET `/api/health` | FastAPI health endpoint | No | HTTP 200 `{"status": "ok"}` + timestamp | Yes | None | PASS |
| AUTH-002 | Web Auth | Valid login & JWT issuance | UI Login Form / POST `/api/auth/token` | `POST /api/auth/token` (`auth_service`) | No | HTTP 200 with JWT `access_token`, localStorage set, UI transitions to app | Yes | None | PASS |
| AUTH-003 | Web Auth | Invalid credentials rejection | UI Login Form / POST `/api/auth/token` | `POST /api/auth/token` | No | HTTP 401 Unauthorized, UI shows localized error message | Yes | None | PASS |
| AUTH-004 | Web Auth | Expired/malformed token handling | Request with invalid Bearer token | `GET /api/auth/me` | No | HTTP 401 Unauthorized, clears token, opens login modal | Yes | None | PASS |
| AUTH-005 | Web Auth | Token persistence on reload | Browser page reload with token in localStorage | `GET /api/auth/me` | No | User stays logged in, UI loads dashboard without login modal | Yes | None | PASS |
| AUTH-006 | Web Auth | Logout clearing state | UI Logout button | `app.js` logout handler | No | localStorage JWT cleared, in-memory state reset, login modal displayed | Yes | None | PASS |
| AUTH-007 | Web Auth | Multi-tab logout sync | BroadcastChannel / storage event | `app.js` auth listener | No | Other open tabs detect token removal and revert to logged-out view | Yes | None | PASS |
| DASH-001 | Home/Today | Dashboard stats summary | Tab Today load | `GET /api/stats` | No | Total, completed, overdue, upcoming task counts match DB state | Yes | None | PASS |
| DASH-002 | Home/Today | Current & next schedule pair banner | Tab Today load | `GET /api/schedule` | No | Shows active pair or next upcoming class with room and teacher | Yes | None | PASS |
| DASH-003 | Home/Today | Today's urgent/upcoming tasks list | Tab Today load | `GET /api/tasks` | No | Lists tasks with near deadlines, sorted chronologically | Yes | None | PASS |
| DASH-004 | Home/Today | Empty state when no tasks | Tab Today with 0 pending tasks | `GET /api/tasks` | No | Renders friendly empty state illustration and message | Yes | None | PASS |
| FRSH-001 | Freshness | Fresh state (<= 15 min) | Topbar sync indicator | `app.js` freshness ticker | No | Badge: `● Обновлено X мин назад` with green dot | Yes | None | PASS |
| FRSH-002 | Freshness | Recent state (16 - 60 min) | Topbar sync indicator | `app.js` freshness ticker | No | Badge: `● Обновлено X мин назад` with subdued dot | Yes | None | PASS |
| FRSH-003 | Freshness | Stale state (> 60 min) | Topbar sync indicator | `app.js` freshness ticker | No | Badge: `⚠ Обновлено X ч назад` with warning icon | Yes | None | PASS |
| FRSH-004 | Freshness | Unknown state (no timestamp) | Topbar sync indicator | `app.js` freshness ticker | No | Badge: `Время синхронизации неизвестно` | Yes | None | PASS |
| FRSH-005 | Freshness | Auto-recalculation timer (60s) | In-app background timer | `setInterval` in `app.js` | No | Timestamp updates without manual page refresh | Yes | None | PASS |
| NAV-001 | Navigation | Switch to Today tab | Bottom nav / sidebar Today tab | Client-side routing in `app.js` | No | Today view visible, other views hidden, active indicator set | Yes | None | PASS |
| NAV-002 | Navigation | Switch to Tasks tab | Bottom nav / sidebar Tasks tab | Client-side routing in `app.js` | No | Tasks view visible, tasks loaded | Yes | None | PASS |
| NAV-003 | Navigation | Switch to Schedule tab | Bottom nav / sidebar Schedule tab | Client-side routing in `app.js` | No | Schedule view visible, schedule loaded | Yes | None | PASS |
| NAV-004 | Navigation | Switch to AI Composer | Bottom nav / quick FAB | Client-side modal/view handler | No | AI Assistant modal/view opens with input ready | Yes | None | PASS |
| NAV-005 | Navigation | Deep-linking / active state sync | Tab clicks | URL hash / history state | No | Active navigation item matches visible screen | Yes | None | PASS |
| TASK-001 | Tasks | Render task cards list | Tasks tab load | `GET /api/tasks` | No | All user tasks rendered with title, subject, deadline tag, and checkbox | Yes | None | PASS |
| TASK-002 | Tasks | Filter: All | Filter pill 'All' | Client-side filter | No | Shows all tasks regardless of status | Yes | None | PASS |
| TASK-003 | Tasks | Filter: Todo | Filter pill 'To Do' | Client-side filter | No | Shows only tasks where `is_completed == false` | Yes | None | PASS |
| TASK-004 | Tasks | Filter: Done | Filter pill 'Done' | Client-side filter | No | Shows only tasks where `is_completed == true` | Yes | None | PASS |
| TASK-005 | Tasks | Filter: Materials | Filter pill 'Materials' | Client-side filter | No | Shows only tasks that contain downloadable file attachments | Yes | None | PASS |
| TASK-006 | Tasks | Filter: Urgent | Filter pill 'Urgent' | Client-side filter | No | Shows only tasks due within 48 hours | Yes | None | PASS |
| TASK-007 | Tasks | Filter by Subject | Subject dropdown / chip click | Client-side filter | No | Only tasks matching selected subject are displayed | Yes | None | PASS |
| TASK-008 | Tasks | Search query filtering | Search input `#task-search` | Client-side filter | No | Filters tasks in real time by title, description, or subject | Yes | None | PASS |
| TASK-009 | Tasks | Search no results empty state | Search input with unmatched term | Client-side filter | No | Friendly 'No tasks found' message | Yes | None | PASS |
| TASK-010 | Tasks | Toggle task completion | Task checkbox click | `POST /api/tasks/{task_id}/toggle` | Yes | DB `is_completed` toggled, UI updates, toast feedback shown | Yes | None | PASS |
| TASK-011 | Tasks | Rapid multi-toggle debouncing | Fast repeated clicks on checkbox | `POST /api/tasks/{task_id}/toggle` | Yes | UI updates optimistically, final state matches DB, no race conditions | Yes | None | PASS |
| TASK-012 | Tasks | Task Detail Modal open | Click task card body | `GET /api/tasks/{task_id}` | No | Detail sheet opens showing full title, description, deadline, attachments | Yes | None | PASS |
| TASK-013 | Tasks | Task Detail close via backdrop | Click modal backdrop or ESC key | UI event listener | No | Modal closes smoothly, focus restored | Yes | None | PASS |
| FILE-001 | Files | Download valid task attachment | Click download link on task card/modal | `GET /api/tasks/{task_id}/download` | No | HTTP 200, Content-Disposition header with filename, correct binary payload | Yes | None | PASS |
| FILE-002 | Files | Missing attachment file handling | Download link for non-existent file | `GET /api/tasks/{task_id}/download` | No | HTTP 404 Not Found, UI shows error toast | Yes | None | PASS |
| FILE-003 | Security | Path traversal exploit rejection (`../`) | Malicious file path parameter | `GET /api/tasks/{task_id}/download` | No | HTTP 400 or 403 Forbidden, server refuses to access outside data dir | Yes | None | PASS |
| FILE-004 | Security | Absolute path exploit rejection (`C:\Windows`) | Absolute system path in file record | `GET /api/tasks/{task_id}/download` | No | HTTP 400 or 403 Forbidden, no system file leakage | Yes | None | PASS |
| SCHED-001 | Schedule | Daily schedule rendering | Schedule tab load | `GET /api/schedule` | No | Pairs rendered chronologically with time, type, room, lecturer | Yes | None | PASS |
| SCHED-002 | Schedule | Weekly schedule rendering | Week toggle / tab | `GET /api/schedule/week` | No | Grid/list of days Monday to Saturday with respective classes | Yes | None | PASS |
| SCHED-003 | Schedule | Day selector navigation | Day pill clicks (Mon-Sat) | Client-side day selector | No | Displays classes for selected day | Yes | None | PASS |
| SCHED-004 | Schedule | Sunday empty schedule handling | Sunday selection | Client-side logic | No | Displays 'No classes on Sunday' day off message | Yes | None | PASS |
| SCHED-005 | Schedule | Subject click to task filtering | Click subject badge on schedule card | `app.js` navigation helper | No | Redirects to Tasks tab filtered by that subject | Yes | None | PASS |
| AI-001 | AI Pipeline | Parse standard Elder message | Paste text into AI input -> Parse | `POST /api/ai/parse-task` (`gemini_service`) | No | Returns structured JSON (title, subject, deadline, desc); DOES NOT create DB task | Yes | Gemini API (mockable) | PASS |
| AI-002 | AI Pipeline | Parse slang / messy student text | AI parse input | `POST /api/ai/parse-task` | No | Successfully extracts deadline, subject, and assignment specifics | Yes | Gemini API (mockable) | PASS |
| AI-003 | AI Pipeline | Parse multi-task message | AI parse input | `POST /api/ai/parse-task` | No | Extracts individual distinct tasks | Yes | Gemini API (mockable) | PASS |
| AI-004 | AI Pipeline | Parse relative date ("к след. вторнику") | AI parse input | `POST /api/ai/parse-task` | No | Resolves relative date against current calendar | Yes | Gemini API (mockable) | PASS |
| AI-005 | AI Pipeline | Parse input with no deadline | AI parse input | `POST /api/ai/parse-task` | No | Correctly sets deadline to null/empty without crashing | Yes | Gemini API (mockable) | PASS |
| AI-006 | AI Pipeline | Parse empty / whitespace input | Submit empty AI input | Client-side validation / API | No | UI validation prevents submission or API returns 400 | Yes | None | PASS |
| AI-007 | AI Pipeline | Parse gibberish / nonsensical text | Submit random text to AI | `POST /api/ai/parse-task` | No | Gracefully handles without 500 error, returns clear message | Yes | Gemini API (mockable) | PASS |
| AI-008 | AI Pipeline | Parse enormous text (> 50k chars) | Submit large text payload | `POST /api/ai/parse-task` | No | Handled gracefully, truncated or 413, no unhandled exception | Yes | Gemini API (mockable) | PASS |
| AI-009 | AI Pipeline | Parse code snippet / traceback | Submit code text to AI | `POST /api/ai/parse-task` | No | Detects programming context, extracts assignment task | Yes | Gemini API (mockable) | PASS |
| AI-010 | AI Pipeline | Parse date rollover (next year/month) | AI parse input | `POST /api/ai/parse-task` | No | Calculates valid ISO timestamp across month/year boundary | Yes | Gemini API (mockable) | PASS |
| AI-011 | AI Pipeline | Preview card presentation | Successful parse result | Client-side render | No | Editable preview card shown with title, subject, date, description | Yes | None | PASS |
| AI-012 | AI Pipeline | Edit preview fields before saving | User edits inputs in preview card | UI form inputs | No | Updated values reflected in final submission payload | Yes | None | PASS |
| AI-013 | AI Pipeline | Confirm & Save AI parsed task | Click 'Save / Confirm' button | `POST /api/tasks` | Yes | Task saved in DB, appears in Tasks tab, success toast shown | Yes | None | PASS |
| AI-014 | AI Pipeline | Cancel / Dismiss preview | Click 'Cancel' button | UI handler | No | Preview dismissed, input cleared, no DB task created | Yes | None | PASS |
| AI-015 | AI Resilience | Gemini 429 RATE_LIMIT handling | Rate limit trigger | `gemini_service` retry/backoff | No | Backoff retry executes; if exhausted, UI shows friendly retry banner | Yes | Gemini API (mockable) | PASS |
| AI-016 | AI Resilience | Gemini 429 QUOTA_EXCEEDED handling | Quota limit trigger | `gemini_service` | No | UI indicates quota exhausted, does NOT retry infinitely | Yes | Gemini API (mockable) | PASS |
| AI-017 | AI Resilience | Gemini 503 UPSTREAM_UNAVAILABLE | Gemini service down | `gemini_service` | No | UI displays "AI временно недоступен. Это не повлияло на сохранённые задания." + Retry | Yes | Gemini API (mockable) | PASS |
| AI-018 | AI Resilience | Gemini Request TIMEOUT | Connection stall | `gemini_service` | No | Timeout handled cleanly, error taxonomy TIMEOUT returned, retry available | Yes | Gemini API (mockable) | PASS |
| AI-019 | AI Resilience | Gemini INVALID_RESPONSE (malformed JSON) | Model outputs non-JSON markdown | `gemini_service` parser | No | Fallback parser attempts extraction or cleanly returns INVALID_RESPONSE | Yes | Gemini API (mockable) | PASS |
| AI-020 | AI Resilience | Gemini AUTH_ERROR (bad API key) | Invalid GEMINI_API_KEY | `gemini_service` | No | UI shows clear configuration error, no infinite loop | Yes | Gemini API (mockable) | PASS |
| AI-021 | AI Resilience | Gemini NETWORK_ERROR (DNS/socket drop) | Disconnect upstream socket | `gemini_service` | No | Returns NETWORK_ERROR, UI offers Retry button | Yes | Gemini API (mockable) | PASS |
| AI-022 | AI Resilience | Deterministic response caching | Identical input sent twice | `gemini_service` cache | No | Second call served from cache, avoids upstream API call | Yes | Gemini API (mockable) | PASS |
| AI-023 | AI Features | Summarize lab/task assignment | Click 'Summarize' on Task Detail | `POST /api/ai/summarize-task/{task_id}` | No | Returns concise lab guidance, goals, steps, deadlines | Yes | Gemini API (mockable) | PASS |
| AI-024 | AI Features | Voice input Web Speech fallback | Click microphone button `#ai-voice-btn` | Browser `SpeechRecognition` API | No | Speech-to-text populates textarea, or shows fallback when unsupported | Yes | Browser Speech API | PASS |
| BB-001 | Blackboard | Manual Blackboard sync trigger | Click 'Sync Blackboard' button | `POST /api/sync-bb` | Yes | Initiates sync job, returns 200, updates `last_successful_sync` | Yes | Blackboard portal (mockable) | PASS |
| BB-002 | Blackboard | In-progress sync debounce | Click sync button while already syncing | `POST /api/sync-bb` | No | Rejects or returns status indicating sync in progress, prevents race | Yes | None | PASS |
| BB-003 | Blackboard | Auth failure handling during sync | Bad Blackboard credentials | `services.bb_scraper` | No | Logs clear error, returns 401/502 with friendly UI message | Yes | Blackboard portal (mockable) | PASS |
| BB-004 | Blackboard | Task extraction & attachment persistence | Sync runs on courses with files | `services.bb_scraper` | Yes | Tasks created in DB, files downloaded to `data/attachments/` | Yes | Blackboard portal (mockable) | PASS |
| PWA-001 | PWA / Offline | Manifest validity | Fetch `/manifest.json` | Static file handler | No | Valid JSON, name, short_name, icons, start_url, display standalone | Yes | None | PASS |
| PWA-002 | PWA / Offline | Service worker registration | Page load | `navigator.serviceWorker.register` | No | Service worker registers successfully in supported browsers | Yes | None | PASS |
| PWA-003 | PWA / Offline | Static asset caching | Service worker install/fetch | `sw.js` cache | No | Static shell (`index.html`, `app.js`, `style.css`, icons) cached | Yes | None | PASS |
| PWA-004 | PWA / Offline | Offline page shell display | Disconnect network & reload | CacheStorage | No | App shell renders from cache without browser network error page | Yes | None | PASS |
| PWA-005 | PWA / Offline | Multi-user CacheStorage isolation | User A logs out, User B logs in | Service Worker / CacheStorage | No | User B cannot view User A's cached private tasks or tokens | Yes | None | PASS |
| UI-001 | Theme | Theme switch: Light to Dark | Click theme toggle button | `app.js` theme controller | No | `data-theme="dark"` set on `<html>`, dark colors applied, saved to localStorage | Yes | None | PASS |
| UI-002 | Theme | Theme switch: Dark to Light | Click theme toggle button | `app.js` theme controller | No | `data-theme="light"` set on `<html>`, light colors applied, saved to localStorage | Yes | None | PASS |
| UI-003 | Theme | Theme preference persistence | Set theme, reload page | `app.js` initialization | No | Previously chosen theme restored immediately without flickering | Yes | None | PASS |
| RESP-001 | Responsive | Viewport: Desktop 1440x900 | Browser resize to 1440x900 | CSS Layout | No | Horizontal layout, sidebar visible, no horizontal scroll, no broken cards | Yes | None | PASS |
| RESP-002 | Responsive | Viewport: Tablet Landscape 1024x768 | Browser resize to 1024x768 | CSS Layout | No | Fluid layout, cards adapt cleanly, no text overflow | Yes | None | PASS |
| RESP-003 | Responsive | Viewport: Tablet Portrait 768x1024 | Browser resize to 768x1024 | CSS Layout | No | Adaptive column layout, navigation accessible | Yes | None | PASS |
| RESP-004 | Responsive | Viewport: Mobile Large 430x932 | Browser resize to 430x932 | CSS Layout | No | Single column, bottom navigation bar, tap targets >= 44px | Yes | None | PASS |
| RESP-005 | Responsive | Viewport: Mobile Standard 390x844 | Browser resize to 390x844 | CSS Layout | No | Single column, compact headers, touch-friendly touch targets | Yes | None | PASS |
| RESP-006 | Responsive | Viewport: Mobile Small 360x740 | Browser resize to 360x740 | CSS Layout | No | No horizontal overflow, text remains legible, buttons clickable | Yes | None | PASS |
| A11Y-001 | Accessibility | Keyboard navigation tab order | Focus cycling via TAB key | Native browser focus | No | Focusable controls receive focus in logical reading order | Yes | None | PASS |
| A11Y-002 | Accessibility | Modal focus trap & ESC key | Open modal, press TAB / ESC | `app.js` modal listener | No | Focus remains inside modal until ESC closes it, focus restored | Yes | None | PASS |
| A11Y-003 | Accessibility | ARIA attributes & labels | DOM inspection | HTML semantic structure | No | Buttons have accessible labels, modals have `role="dialog"`, inputs labeled | Yes | None | PASS |
| ISOL-001 | Security | User data isolation: Tasks | User A queries `/api/tasks` | `api.app` & `database.crud` | No | User A cannot see or access User B's tasks | Yes | None | PASS |
| ISOL-002 | Security | User data isolation: Toggle mutation | User A toggles User B's `task_id` | `POST /api/tasks/{task_id}/toggle` | No | Returns 404 or 403, User B's task status remains unchanged | Yes | None | PASS |
| ISOL-003 | Security | User data isolation: File download | User A downloads User B's attachment | `GET /api/tasks/{task_id}/download` | No | Returns 404 or 403, file content is not delivered to unauthorized user | Yes | None | PASS |
| BOT-001 | Telegram Bot | `/start` command | Send `/start` to bot | `bot.handlers.base` | No | Sends welcome message, instructions, and main menu keyboard | Yes | Telegram API (mockable) | PASS |
| BOT-002 | Telegram Bot | `/help` command | Send `/help` to bot | `bot.handlers.base` | No | Sends usage help and list of available commands | Yes | Telegram API (mockable) | PASS |
| BOT-003 | Telegram Bot | `/today` command | Send `/today` to bot | `bot.handlers.schedule` | No | Returns today's classes and pending tasks | Yes | Telegram API (mockable) | PASS |
| BOT-004 | Telegram Bot | `/schedule` command | Send `/schedule` to bot | `bot.handlers.schedule` | No | Returns weekly schedule with day selector keyboard | Yes | Telegram API (mockable) | PASS |
| BOT-005 | Telegram Bot | `/tasks` command | Send `/tasks` to bot | `bot.handlers.tasks` | No | Returns active tasks with inline toggle buttons | Yes | Telegram API (mockable) | PASS |
| BOT-006 | Telegram Bot | Task inline toggle callback | Click inline checkbox button | `bot.handlers.tasks` | Yes | Toggles task completion in DB, edits Telegram message to reflect new state | Yes | Telegram API (mockable) | PASS |
| SCHD-001 | Scheduler | Morning briefing job | Cron trigger at 07:00 | `scheduler.jobs.send_morning_briefing` | No | Queries today's schedule & pending tasks, sends summary message | Yes | Telegram API (mockable) | PASS |
| SCHD-002 | Scheduler | Deadline alert job | Hourly periodic check | `scheduler.jobs.check_upcoming_deadlines` | No | Finds tasks due in < 24h, sends alert notification | Yes | Telegram API (mockable) | PASS |
| SCHD-003 | Scheduler | Blackboard periodic sync job | Configured interval | `scheduler.jobs.sync_blackboard_job` | Yes | Runs scraper, updates tasks and schedules in DB | Yes | Blackboard portal (mockable) | PASS |
| DB-001 | Database | SQLite WAL mode enabled | DB connection startup | `database.connection` | No | PRAGMA journal_mode is `wal` for high concurrent read performance | Yes | None | PASS |
| DB-002 | Database | Foreign key constraints enforced | DB connection startup | `database.connection` | No | PRAGMA foreign_keys is `ON`, orphaned records prevented | Yes | None | PASS |
| DB-003 | Database | Transaction integrity on failure | Failed mutation simulation | `database.crud` | No | Rollback occurs cleanly on error, no partial or corrupt state | Yes | None | PASS |
