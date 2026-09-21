# KAI Student OS — AI Latency Measurement Methodology & Timing Integrity

## 1. Overview & Core Philosophy

This document defines the formal timing instrumentation methodology for AI task parsing, previewing, and summarization in **KAI Student OS**.
The core principle governing latency metrics is:

$$\text{TRUTH} > \text{APPEARANCE OF COMPLETION}$$

No synthetic approximations, no DateTime subtraction, and zero double-counting.
Timing metrics strictly reflect real elapsed durations measured using the operating system's monotonic clock.

---

## 2. Clock Source

- **Python Runtime (Backend & QA Runner):**
  Uses `time.perf_counter()`.
  - **Resolution:** Nanosecond / sub-microsecond precision.
  - **Monotonicity:** Strictly non-decreasing. Unaffected by NTP time synchronizations or system wall-clock adjustments.
  - **Rule:** `datetime.now()` subtraction is strictly prohibited for latency measurement.
- **Browser Runtime (Playwright & Web Client):**
  Uses `window.performance.now()`.
  - High-resolution `DOMHighResTimeStamp` measured from time origin.
  - Sub-millisecond floating point precision.

---

## 3. Discrete Lifecycle Timestamps ($t_0 \dots t_{15}$)

For every individual AI request, 16 distinct monotonic checkpoints are captured:

| Timestamp | Event Name | Scope | Description |
|---|---|---|---|
| $t_0$ | `request_start` | Client | User action initiated (click / function invocation) |
| $t_1$ | `frontend_prepare_start` | Client | Serialization and parameter sanitization begins |
| $t_2$ | `frontend_prepare_end` | Client | Payload ready, token attached |
| $t_3$ | `fetch_start` | Client / Network | Network socket transmits HTTP request to `/api/ai/*` |
| $t_5$ | `backend_start` | Backend Server | FastAPI route handler receives request and parses body |
| $t_{11}$ | `db_start` | Backend Server | DB query begins (registered academic subjects or schedule lookup) |
| $t_{12}$ | `db_end` | Backend Server | DB query completes |
| $t_7$ | `gemini_start` | Backend Server | Upstream Google Gemini API call or local mock starts |
| $t_8$ | `gemini_end` | Backend Server | Model inference returns raw JSON |
| $t_9$ | `validation_start` | Backend Server | Pydantic schema validation and evidence calculation begins |
| $t_{10}$ | `validation_end` | Backend Server | Evidence structured and response envelope ready |
| $t_6$ | `backend_end` | Backend Server | FastAPI finishes serialization; headers attached |
| $t_{13}$ | `response_start` | Network | Response streaming begins across network socket |
| $t_4$ / $t_{14}$ | `fetch_end` / `response_received` | Client | Client receives full HTTP response body |
| $t_{15}$ | `render_end` | Client | UI DOM elements rendered or client schema validation complete |

---

## 4. Parent / Child Nested Timing Architecture

Timings are structured using a **nested hierarchical timing model**, strictly separating top-level non-overlapping parent phases from child sub-phases.

```text
TOTAL WALL CLOCK (t15 - t0)
├── frontend_prepare_ms (t2 - t1)
├── network_ms (pure wire transport: round_trip - backend_ms)
├── backend_ms (t6 - t5)
│   ├── db_ms (subject/schedule lookup: t12 - t11)
│   ├── gemini_ms (upstream model or mock delay: t8 - t7)
│   ├── validation_ms (Pydantic schema validation & evidence: t10 - t9)
│   └── auth_overhead_ms (FastAPI routing & serialization overhead)
└── render_ms (client DOM rendering / validation: t15 - t14)
```

### 4.1 Non-Overlapping Top-Level Phases
1. **Frontend Preparation:**
   $$\text{frontend\_prepare\_ms} = \max(0, (t_2 - t_1) \times 1000)$$
2. **Backend Execution:**
   $$\text{backend\_ms} = \max(0, (t_6 - t_5) \times 1000)$$
3. **Pure Network Wire Transit:**
   $$\text{client\_round\_trip\_ms} = \max(0, (t_{14} - t_3) \times 1000)$$
   $$\text{network\_ms} = \max(0, \text{client\_round\_trip\_ms} - \text{backend\_ms})$$
4. **Client Rendering / Consumption:**
   $$\text{render\_ms} = \max(0, (t_{15} - t_{14}) \times 1000)$$

### 4.2 Aggregation Formula
The reported total wall-clock duration is strictly equal to the non-overlapping parent sum:

$$\text{total\_wall\_ms} = \text{frontend\_prepare\_ms} + \text{network\_ms} + \text{backend\_ms} + \text{render\_ms}$$

Notice that substituting $\text{network\_ms}$:
$$\text{total\_wall\_ms} = \text{frontend\_prepare\_ms} + (\text{client\_round\_trip\_ms} - \text{backend\_ms}) + \text{backend\_ms} + \text{render\_ms}$$
$$\text{total\_wall\_ms} = \text{frontend\_prepare\_ms} + \text{client\_round\_trip\_ms} + \text{render\_ms}$$

This guarantees exact mathematical identity without double-counting.

### 4.3 Nested Backend Hierarchy Constraint
Sub-phases of the server are nested inside `backend_ms`:
$$\text{gemini\_ms} + \text{validation\_ms} + \text{db\_ms} \le \text{backend\_ms}$$
Child durations are never summed into `total_wall_ms` a second time.

---

## 5. Arithmetic Assertions & Integrity Gate

The QA runner automatically asserts mathematical integrity for every recorded latency record:

1. **Non-Overlapping Parent Sum Equality:**
   $$|\text{total\_wall\_ms} - (\text{frontend\_prepare\_ms} + \text{network\_ms} + \text{backend\_ms} + \text{render\_ms})| \le \max(0.5, 0.05 \times \text{total\_wall\_ms})$$
2. **Child Nesting Constraint:**
   $$(\text{gemini\_ms} + \text{validation\_ms} + \text{db\_ms}) \le \text{backend\_ms} \times 1.05 + 0.2$$
3. **Absence of Double-Counting:**
   $$\text{total\_wall\_ms} \ne 2 \times (\text{network\_ms} + \text{backend\_ms})$$

If any test violates these assertions, the test status is marked as:

$$\text{MEASUREMENT\_ERROR}$$

The build fails immediately and cannot receive a `PASS` status.

---

## 6. MOCK vs. REAL AI Provider Separation

To prevent deceptive latency claims, provider environments are strictly segregated:

### 6.1 Local Mode (Mock AI)
- **Execution Target:** Local SQLite on port 8899 without live `GEMINI_API_KEY`.
- **Gemini Metric Label:** Explicitly tagged as `MOCK ONLY` (e.g., `15.0 ms (MOCK ONLY)`).
- **Mock SLA Target:** $< 500\text{ ms}$.
- **Real AI Status:** `NOT VERIFIED (Running in LOCAL Mode without live GEMINI_API_KEY)`.
- **Rule:** Never extrapolate real model latency from mock executions.

### 6.2 Live Mode (Real Gemini API)
- **Execution Target:** Live or production backend with authenticated Google Gemini API key.
- **Real SLA Target:** $< 3000\text{ ms}$ (3.0s end-to-end SLA).
- **Status:** Verified with real network and model inference breakdown.
