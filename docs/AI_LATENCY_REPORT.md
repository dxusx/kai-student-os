# KAI Student OS — AI Latency & Performance Breakdown Report

**Date:** 2026-09-22 01:30:40  
**Mode:** LOCAL (Mock AI Provider)  
**Timing Instrumentation:** High-precision monotonic clock (`time.perf_counter`)  
**Measurement Model:** `nested_partition` (Exact non-overlapping wall clock decomposition)  
**Aggregation Formula:** `total_wall_ms = frontend_prepare_ms + dispatch_gap_ms + network_ms + backend_ms + render_ms`  
**Raw Backend Constraint:** `backend_ms <= client_round_trip_ms`  
**Raw Child Constraint:** `backend_ms >= gemini_ms + validation_ms + db_ms`  
**Zero Double-Counting Enforcement:** Pure wire transport subtraction `network_ms = client_round_trip_ms - backend_ms`  

## Executive Performance Summary

- **Arithmetic Integrity Status:** ✅ 100% VALID (0 Measurement Errors)  
- **Provider Execution Mode:** MOCK ONLY (Local heuristic fallback)  
- **Real AI SLA Status:** NOT VERIFIED (Running in Mock Mode)  

### Parent / Child Timing Hierarchy
```text
TOTAL WALL CLOCK (t15 - t0)
├── frontend_prepare_ms (t2 - t0)
├── dispatch_gap_ms (t3 - t2)
├── network_ms (pure wire transport: client_round_trip - backend_ms)
├── backend_ms (raw server execution: t6 - t5)
│   ├── db_ms (academic subjects & schedule lookup)
│   ├── gemini_ms (upstream inference or mock delay)
│   ├── validation_ms (Pydantic schema validation & evidence)
│   └── auth_overhead_ms (FastAPI routing & serialization)
└── render_ms (client-side DOM rendering & preview update: t15 - t14)
```

## Latency Distribution (AI-001 .. AI-010 Parsing Matrix)

| Metric | Min (ms) | Median / p50 (ms) | Mean (ms) | p95 (ms) | Max (ms) | Provider / SLA Notes |
|---|---|---|---|---|---|---|
| **Total Wall Clock** | 2.37ms | 4.75ms | 5.57ms | 10.34ms | 12.06ms | Verified against active mode |
| **Network Wire Transport** | 0.47ms | 2.67ms | 2.93ms | 5.27ms | 6.06ms | Verified against active mode |
| **Backend Processing** | 1.89ms | 2.05ms | 2.62ms | 5.25ms | 7.73ms | Verified against active mode |
| **Gemini Inference** | 0.01ms | 0.02ms | 0.53ms | 2.85ms | 5.15ms | **MOCK ONLY** in LOCAL mode |

## Latency Measurements Breakdown

| Test ID | Trace ID | Scenario | Model | Frontend | Gap | Network (Wire) | Backend | Gemini Upstream | Validation | DB Lookup | Render | Total Wall Clock | Provider | Mock SLA (<500ms) | Real AI SLA (<3s) | Math Integrity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AI-001 | `trace-ai-001-1790029789308` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 6.06ms | 2.15ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.08ms | 0.03ms | **8.24ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-002 | `trace-ai-002-1790029789385` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.65ms | 2.07ms | 0.02 ms (MOCK ONLY) | 0.01ms | 2.02ms | 0.02ms | **4.74ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-003 | `trace-ai-003-1790029789460` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.58ms | 2.22ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.16ms | 0.02ms | **4.81ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-004 | `trace-ai-004-1790029789536` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.58ms | 2.05ms | 0.02 ms (MOCK ONLY) | 0.03ms | 1.99ms | 0.02ms | **4.65ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-005 | `trace-ai-005-1790029789613` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.6ms | 1.94ms | 0.02 ms (MOCK ONLY) | 0.01ms | 1.9ms | 0.02ms | **4.56ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-006 | `trace-ai-006-1790029789687` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 0.47ms | 1.89ms | 0.03 ms (MOCK ONLY) | 1.0ms | 1.0ms | 0.01ms | **2.37ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-007 | `trace-ai-007-1790029789761` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.68ms | 2.04ms | 0.01 ms (MOCK ONLY) | 0.01ms | 2.0ms | 0.02ms | **4.74ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-008 | `trace-ai-008-1790029789846` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 4.31ms | 7.73ms | 5.15 ms (MOCK ONLY) | 0.56ms | 2.0ms | 0.02ms | **12.06ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-009 | `trace-ai-009-1790029789921` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.69ms | 2.04ms | 0.03 ms (MOCK ONLY) | 0.01ms | 1.99ms | 0.02ms | **4.75ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-010 | `trace-ai-010-1790029789996` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.68ms | 2.06ms | 0.01 ms (MOCK ONLY) | 0.01ms | 2.03ms | 0.02ms | **4.76ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-011 | `trace-ai-011-1790029792550` | AI Preview & Confirm | nested_partition | 13.8ms | 0.02ms | 282.24ms | 2.25ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.16ms | 17.11ms | **315.42ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-012 | `trace-ai-012-1790029795062` | AI Preview & Confirm | nested_partition | 14.32ms | 0.02ms | 273.08ms | 2.24ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.14ms | 17.79ms | **307.44ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-013 | `trace-ai-013-1790029797540` | AI Preview & Confirm | nested_partition | 15.27ms | 0.02ms | 284.94ms | 2.59ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.5ms | 18.12ms | **320.94ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-014 | `trace-ai-014-1790029800324` | AI Preview & Confirm | nested_partition | 14.87ms | 0.72ms | 239.48ms | 2.6ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.52ms | 17.4ms | **275.07ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-015 | `trace-ai-015-1790029800397` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-016 | `trace-ai-016-1790029800468` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.01ms | 0.01ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-017 | `trace-ai-017-1790029800543` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-018 | `trace-ai-018-1790029800615` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-019 | `trace-ai-019-1790029800690` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.03ms | 0.03ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.06ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-020 | `trace-ai-020-1790029800765` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.01ms | 0.01ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.02ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-021 | `trace-ai-021-1790029800837` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-022 | `trace-ai-022-1790029800909` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-023 | `trace-ai-023-1790029801479` | AI Lab Summary | nested_partition | 0.0ms | 0.0ms | 493.63ms | 5.24ms | 0.01 ms (MOCK ONLY) | 0.02ms | 5.21ms | 0.03ms | **498.9ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-024 | `trace-ai-024-1790029803323` | Voice Input Fallback | nested_partition | 0.03ms | 0.0ms | 198.43ms | 198.43ms | 0.0 ms (MOCK ONLY) | 0.0ms | 0.0ms | 0.0ms | **396.89ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |

## Provider & SLA Verification

> [!NOTE]
> **REAL AI Latency:** `NOT VERIFIED (Running in LOCAL Mode without live GEMINI_API_KEY)`.
> In local mode, AI resilience and structured output tests execute against deterministic mock service handlers.
> Upstream Gemini latency is labeled as **MOCK ONLY**. Real Gemini upstream latency is measured during `--mode live` runs.
