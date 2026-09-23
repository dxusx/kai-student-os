# KAI Student OS — AI Latency & Performance Breakdown Report

**Date:** 2026-09-24 01:02:16  
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
| **Total Wall Clock** | 2.52ms | 5.28ms | 6.19ms | 10.93ms | 13.85ms | Verified against active mode |
| **Network Wire Transport** | 0.5ms | 2.94ms | 3.29ms | 5.44ms | 5.6ms | Verified against active mode |
| **Backend Processing** | 2.01ms | 2.27ms | 2.88ms | 5.76ms | 8.22ms | Verified against active mode |
| **Gemini Inference** | 0.01ms | 0.03ms | 0.55ms | 2.93ms | 5.29ms | **MOCK ONLY** in LOCAL mode |

## Latency Measurements Breakdown

| Test ID | Trace ID | Scenario | Model | Frontend | Gap | Network (Wire) | Backend | Gemini Upstream | Validation | DB Lookup | Render | Total Wall Clock | Provider | Mock SLA (<500ms) | Real AI SLA (<3s) | Math Integrity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AI-001 | `trace-ai-001-1790200880900` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 5.24ms | 2.09ms | 0.03 ms (MOCK ONLY) | 0.04ms | 2.0ms | 0.03ms | **7.36ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-002 | `trace-ai-002-1790200880989` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 3.46ms | 2.75ms | 0.04 ms (MOCK ONLY) | 0.02ms | 2.66ms | 0.03ms | **6.23ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-003 | `trace-ai-003-1790200881084` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 3.75ms | 2.42ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.35ms | 0.02ms | **6.19ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-004 | `trace-ai-004-1790200881175` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.94ms | 2.27ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.19ms | 0.02ms | **5.23ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-005 | `trace-ai-005-1790200881259` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.87ms | 2.16ms | 0.02 ms (MOCK ONLY) | 0.01ms | 2.12ms | 0.02ms | **5.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-006 | `trace-ai-006-1790200881344` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 0.5ms | 2.01ms | 0.03 ms (MOCK ONLY) | 1.0ms | 1.0ms | 0.01ms | **2.52ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-007 | `trace-ai-007-1790200881426` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.69ms | 2.21ms | 0.01 ms (MOCK ONLY) | 0.01ms | 2.17ms | 0.02ms | **4.92ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-008 | `trace-ai-008-1790200881521` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 5.6ms | 8.22ms | 5.29 ms (MOCK ONLY) | 0.62ms | 2.29ms | 0.02ms | **13.85ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-009 | `trace-ai-009-1790200881610` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.93ms | 2.28ms | 0.03 ms (MOCK ONLY) | 0.01ms | 2.22ms | 0.02ms | **5.23ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-010 | `trace-ai-010-1790200881705` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.92ms | 2.38ms | 0.02 ms (MOCK ONLY) | 0.01ms | 2.34ms | 0.02ms | **5.32ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-011 | `trace-ai-011-1790200884350` | AI Preview & Confirm | nested_partition | 14.44ms | 0.02ms | 194.78ms | 2.3ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.21ms | 16.67ms | **228.21ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-012 | `trace-ai-012-1790200887128` | AI Preview & Confirm | nested_partition | 14.26ms | 0.02ms | 227.47ms | 2.91ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.8ms | 17.89ms | **262.55ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-013 | `trace-ai-013-1790200889749` | AI Preview & Confirm | nested_partition | 16.88ms | 0.03ms | 206.91ms | 3.2ms | 0.03 ms (MOCK ONLY) | 0.05ms | 3.09ms | 17.9ms | **244.92ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-014 | `trace-ai-014-1790200892158` | AI Preview & Confirm | nested_partition | 14.2ms | 0.73ms | 214.05ms | 2.59ms | 0.03 ms (MOCK ONLY) | 0.04ms | 2.49ms | 17.4ms | **248.97ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-015 | `trace-ai-015-1790200892242` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-016 | `trace-ai-016-1790200892317` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-017 | `trace-ai-017-1790200892390` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-018 | `trace-ai-018-1790200892461` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-019 | `trace-ai-019-1790200892536` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-020 | `trace-ai-020-1790200892613` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.01ms | 0.01ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.02ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-021 | `trace-ai-021-1790200892694` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-022 | `trace-ai-022-1790200892781` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-023 | `trace-ai-023-1790200893339` | AI Lab Summary | nested_partition | 0.0ms | 0.0ms | 477.65ms | 5.17ms | 0.01 ms (MOCK ONLY) | 0.02ms | 5.15ms | 0.03ms | **482.85ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-024 | `trace-ai-024-1790200895374` | Voice Input Fallback | nested_partition | 0.03ms | 0.0ms | 199.21ms | 199.21ms | 0.0 ms (MOCK ONLY) | 0.0ms | 0.0ms | 0.0ms | **398.45ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |

## Provider & SLA Verification

> [!NOTE]
> **REAL AI Latency:** `NOT VERIFIED (Running in LOCAL Mode without live GEMINI_API_KEY)`.
> In local mode, AI resilience and structured output tests execute against deterministic mock service handlers.
> Upstream Gemini latency is labeled as **MOCK ONLY**. Real Gemini upstream latency is measured during `--mode live` runs.
