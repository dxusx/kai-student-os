# KAI Student OS — AI Latency & Performance Breakdown Report

**Date:** 2026-09-21 21:33:41  
**Mode:** LOCAL (Mock AI Provider)  
**Timing Instrumentation:** High-precision monotonic clock (`time.perf_counter`)  
**Measurement Model:** `nested`  
**Aggregation Formula:** `total_wall_ms = frontend_prepare_ms + network_ms + backend_ms + render_ms`  
**Nested Constraint:** `backend_ms >= gemini_ms + validation_ms + db_ms`  
**Zero Double-Counting Assertion:** `total_wall_ms != 2 * (network_ms + backend_ms)`  

## Executive Performance Summary

- **Arithmetic Integrity Status:** ✅ 100% VALID (0 Measurement Errors)  
- **Provider Execution Mode:** MOCK ONLY (Local heuristic fallback)  

### Parent / Child Timing Hierarchy
```text
TOTAL WALL CLOCK (t15 - t0)
├── frontend_prepare_ms (t2 - t1)
├── network_ms (pure wire transport: round_trip - backend_ms)
├── backend_ms (t6 - t5)
│   ├── db_ms (academic subjects & schedule lookup: t12 - t11)
│   ├── gemini_ms (upstream inference or mock delay: t8 - t7)
│   ├── validation_ms (Pydantic schema validation & evidence: t10 - t9)
│   └── auth_overhead_ms (FastAPI routing & serialization)
└── render_ms (client-side DOM rendering & preview update: t15 - t14)
```

## Latency Measurements Breakdown

| Test ID | Scenario | Model | Frontend | Network (Wire) | Backend | Gemini Upstream | Validation | DB Lookup | Render | Total Wall Clock | Provider | Mock SLA (<500ms) | Real AI SLA (<3s) | Math Integrity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AI-001 | AI Task Parse Pipeline | nested | 0.0ms | 529.91ms | 794.74ms | 0.03 ms (MOCK ONLY) | 0.04ms | 2.73ms | 0.91ms | **1325.56ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-002 | AI Task Parse Pipeline | nested | 0.0ms | 540.84ms | 789.71ms | 0.03 ms (MOCK ONLY) | 0.02ms | 2.51ms | 0.98ms | **1331.53ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-003 | AI Task Parse Pipeline | nested | 0.0ms | 533.05ms | 784.65ms | 0.02 ms (MOCK ONLY) | 0.03ms | 3.06ms | 0.83ms | **1318.54ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-004 | AI Task Parse Pipeline | nested | 0.0ms | 521.71ms | 771.66ms | 0.03 ms (MOCK ONLY) | 0.04ms | 2.56ms | 0.86ms | **1294.24ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-005 | AI Task Parse Pipeline | nested | 0.0ms | 528.5ms | 783.99ms | 0.02 ms (MOCK ONLY) | 0.01ms | 2.77ms | 0.98ms | **1313.48ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-006 | AI Task Parse Pipeline | nested | 0.0ms | 107.38ms | 429.53ms | 15.0 ms (MOCK ONLY) | 1.0ms | 1.0ms | 0.71ms | **537.62ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-007 | AI Task Parse Pipeline | nested | 0.0ms | 527.53ms | 781.13ms | 0.01 ms (MOCK ONLY) | 0.02ms | 2.87ms | 0.85ms | **1309.52ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-008 | AI Task Parse Pipeline | nested | 0.0ms | 523.84ms | 793.25ms | 5.31 ms (MOCK ONLY) | 0.6ms | 3.21ms | 1.05ms | **1318.14ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-009 | AI Task Parse Pipeline | nested | 0.0ms | 530.88ms | 794.51ms | 0.03 ms (MOCK ONLY) | 0.02ms | 2.85ms | 0.88ms | **1326.27ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-010 | AI Task Parse Pipeline | nested | 0.0ms | 527.69ms | 779.25ms | 0.03 ms (MOCK ONLY) | 0.02ms | 2.78ms | 0.83ms | **1307.76ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-011 | AI Preview & Confirm | nested | 17.65ms | 364.66ms | 799.05ms | 0.02 ms (MOCK ONLY) | 0.04ms | 3.38ms | 18.94ms | **1200.32ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-012 | AI Preview & Confirm | nested | 17.46ms | 554.68ms | 815.53ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.66ms | 19.51ms | **1407.2ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-013 | AI Preview & Confirm | nested | 16.07ms | 547.2ms | 787.31ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.57ms | 18.32ms | **1368.92ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-014 | AI Preview & Confirm | nested | 15.99ms | 519.17ms | 798.59ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.8ms | 18.84ms | **1353.54ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-015 | AI Resilience & Errors | nested | 0.0ms | 0.01ms | 0.03ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-016 | AI Resilience & Errors | nested | 0.0ms | 0.01ms | 0.03ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-017 | AI Resilience & Errors | nested | 0.0ms | 0.01ms | 0.04ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-018 | AI Resilience & Errors | nested | 0.0ms | 0.01ms | 0.03ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-019 | AI Resilience & Errors | nested | 0.0ms | 0.01ms | 0.04ms | 0.0 ms (MOCK ONLY) | 0.03ms | 0.0ms | 0.0ms | **0.06ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-020 | AI Resilience & Errors | nested | 0.0ms | 0.01ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-021 | AI Resilience & Errors | nested | 0.0ms | 0.01ms | 0.04ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-022 | AI Resilience & Errors | nested | 0.0ms | 0.01ms | 0.04ms | 0.0 ms (MOCK ONLY) | 0.03ms | 0.0ms | 0.0ms | **0.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-023 | AI Lab Summary | nested | 0.0ms | 560.61ms | 781.37ms | 0.02 ms (MOCK ONLY) | 697.79ms | 5.43ms | 0.05ms | **1342.03ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-024 | Voice Input Fallback | nested | 0.03ms | 365.72ms | 365.72ms | 0.0 ms (MOCK ONLY) | 0.0ms | 0.0ms | 0.0ms | **731.46ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |

## Provider & SLA Verification

> [!NOTE]
> **REAL AI Latency:** `NOT VERIFIED (Running in LOCAL Mode without live GEMINI_API_KEY)`.
> In local mode, AI resilience and structured output tests execute against deterministic mock service handlers.
> Upstream Gemini latency is labeled as **MOCK ONLY**. Real Gemini upstream latency is measured during `--mode live` runs.
