# KAI Student OS — AI Latency & Performance Breakdown Report

**Date:** 2026-09-24 00:31:47  
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
| **Total Wall Clock** | 2.44ms | 4.94ms | 5.79ms | 10.41ms | 12.76ms | Verified against active mode |
| **Network Wire Transport** | 0.49ms | 2.73ms | 3.07ms | 5.18ms | 5.39ms | Verified against active mode |
| **Backend Processing** | 1.94ms | 2.12ms | 2.69ms | 5.45ms | 7.82ms | Verified against active mode |
| **Gemini Inference** | 0.01ms | 0.02ms | 0.54ms | 2.85ms | 5.16ms | **MOCK ONLY** in LOCAL mode |

## Latency Measurements Breakdown

| Test ID | Trace ID | Scenario | Model | Frontend | Gap | Network (Wire) | Backend | Gemini Upstream | Validation | DB Lookup | Render | Total Wall Clock | Provider | Mock SLA (<500ms) | Real AI SLA (<3s) | Math Integrity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AI-001 | `trace-ai-001-1790199051236` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 5.39ms | 2.13ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.05ms | 0.03ms | **7.54ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-002 | `trace-ai-002-1790199051314` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.72ms | 1.94ms | 0.03 ms (MOCK ONLY) | 0.01ms | 1.89ms | 0.02ms | **4.68ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-003 | `trace-ai-003-1790199051396` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.97ms | 2.56ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.49ms | 0.02ms | **5.55ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-004 | `trace-ai-004-1790199051478` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.65ms | 2.34ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.27ms | 0.02ms | **5.01ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-005 | `trace-ai-005-1790199051557` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.61ms | 1.98ms | 0.02 ms (MOCK ONLY) | 0.01ms | 1.94ms | 0.02ms | **4.61ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-006 | `trace-ai-006-1790199051632` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 0.49ms | 1.94ms | 0.03 ms (MOCK ONLY) | 1.0ms | 1.0ms | 0.01ms | **2.44ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-007 | `trace-ai-007-1790199051714` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 3.53ms | 2.12ms | 0.01 ms (MOCK ONLY) | 0.01ms | 2.08ms | 0.02ms | **5.67ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-008 | `trace-ai-008-1790199051799` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 4.92ms | 7.82ms | 5.16 ms (MOCK ONLY) | 0.56ms | 2.07ms | 0.02ms | **12.76ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-009 | `trace-ai-009-1790199051881` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.72ms | 2.12ms | 0.03 ms (MOCK ONLY) | 0.01ms | 2.07ms | 0.02ms | **4.86ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-010 | `trace-ai-010-1790199051962` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.73ms | 2.0ms | 0.01 ms (MOCK ONLY) | 0.01ms | 1.96ms | 0.02ms | **4.75ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-011 | `trace-ai-011-1790199054616` | AI Preview & Confirm | nested_partition | 15.87ms | 0.02ms | 264.33ms | 2.87ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.77ms | 17.53ms | **300.63ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-012 | `trace-ai-012-1790199057549` | AI Preview & Confirm | nested_partition | 14.59ms | 0.02ms | 451.06ms | 2.62ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.52ms | 16.88ms | **485.18ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-013 | `trace-ai-013-1790199060115` | AI Preview & Confirm | nested_partition | 14.09ms | 0.02ms | 291.32ms | 3.47ms | 0.02 ms (MOCK ONLY) | 0.03ms | 3.37ms | 17.48ms | **326.38ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-014 | `trace-ai-014-1790199063243` | AI Preview & Confirm | nested_partition | 13.81ms | 0.76ms | 275.31ms | 2.57ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.48ms | 16.57ms | **309.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-015 | `trace-ai-015-1790199063319` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-016 | `trace-ai-016-1790199063394` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-017 | `trace-ai-017-1790199063470` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-018 | `trace-ai-018-1790199063543` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-019 | `trace-ai-019-1790199063618` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.03ms | 0.03ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-020 | `trace-ai-020-1790199063689` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.01ms | 0.01ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.02ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-021 | `trace-ai-021-1790199063765` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-022 | `trace-ai-022-1790199063836` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.03ms | 0.03ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-023 | `trace-ai-023-1790199064398` | AI Lab Summary | nested_partition | 0.0ms | 0.0ms | 481.74ms | 5.58ms | 0.01 ms (MOCK ONLY) | 0.02ms | 5.54ms | 0.04ms | **487.36ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-024 | `trace-ai-024-1790199066452` | Voice Input Fallback | nested_partition | 0.02ms | 0.0ms | 229.93ms | 229.93ms | 0.0 ms (MOCK ONLY) | 0.0ms | 0.0ms | 0.0ms | **459.87ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |

## Provider & SLA Verification

> [!NOTE]
> **REAL AI Latency:** `NOT VERIFIED (Running in LOCAL Mode without live GEMINI_API_KEY)`.
> In local mode, AI resilience and structured output tests execute against deterministic mock service handlers.
> Upstream Gemini latency is labeled as **MOCK ONLY**. Real Gemini upstream latency is measured during `--mode live` runs.
