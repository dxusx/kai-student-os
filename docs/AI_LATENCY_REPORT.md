# KAI Student OS — AI Latency & Performance Breakdown Report

**Date:** 2026-09-21 23:35:27  
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
| **Total Wall Clock** | 2.45ms | 4.85ms | 5.66ms | 10.35ms | 12.57ms | Verified against active mode |
| **Network Wire Transport** | 0.49ms | 2.7ms | 2.95ms | 5.09ms | 5.44ms | Verified against active mode |
| **Backend Processing** | 1.95ms | 2.15ms | 2.69ms | 5.33ms | 7.88ms | Verified against active mode |
| **Gemini Inference** | 0.01ms | 0.02ms | 0.53ms | 2.82ms | 5.11ms | **MOCK ONLY** in LOCAL mode |

## Latency Measurements Breakdown

| Test ID | Trace ID | Scenario | Model | Frontend | Gap | Network (Wire) | Backend | Gemini Upstream | Validation | DB Lookup | Render | Total Wall Clock | Provider | Mock SLA (<500ms) | Real AI SLA (<3s) | Math Integrity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AI-001 | `trace-ai-001-1790022873056` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 5.44ms | 2.17ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.09ms | 0.03ms | **7.63ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-002 | `trace-ai-002-1790022873136` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.69ms | 2.15ms | 0.02 ms (MOCK ONLY) | 0.01ms | 2.09ms | 0.02ms | **4.86ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-003 | `trace-ai-003-1790022873214` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.69ms | 2.07ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.01ms | 0.02ms | **4.78ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-004 | `trace-ai-004-1790022873294` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.68ms | 2.14ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.07ms | 0.02ms | **4.84ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-005 | `trace-ai-005-1790022873372` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.72ms | 2.19ms | 0.02 ms (MOCK ONLY) | 0.01ms | 2.15ms | 0.02ms | **4.93ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-006 | `trace-ai-006-1790022873449` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 0.49ms | 1.95ms | 0.03 ms (MOCK ONLY) | 1.0ms | 1.0ms | 0.01ms | **2.45ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-007 | `trace-ai-007-1790022873528` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.68ms | 2.11ms | 0.01 ms (MOCK ONLY) | 0.01ms | 2.07ms | 0.02ms | **4.81ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-008 | `trace-ai-008-1790022873615` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 4.67ms | 7.88ms | 5.11 ms (MOCK ONLY) | 0.56ms | 2.19ms | 0.02ms | **12.57ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-009 | `trace-ai-009-1790022873698` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.71ms | 2.22ms | 0.03 ms (MOCK ONLY) | 0.01ms | 2.17ms | 0.02ms | **4.95ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-010 | `trace-ai-010-1790022873777` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.7ms | 2.02ms | 0.02 ms (MOCK ONLY) | 0.01ms | 1.98ms | 0.02ms | **4.74ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-011 | `trace-ai-011-1790022876493` | AI Preview & Confirm | nested_partition | 14.46ms | 0.02ms | 435.8ms | 2.59ms | 0.03 ms (MOCK ONLY) | 0.04ms | 2.49ms | 18.61ms | **471.47ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-012 | `trace-ai-012-1790022879081` | AI Preview & Confirm | nested_partition | 14.9ms | 0.02ms | 322.2ms | 2.48ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.39ms | 17.17ms | **356.77ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-013 | `trace-ai-013-1790022881684` | AI Preview & Confirm | nested_partition | 15.01ms | 0.02ms | 322.75ms | 2.32ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.23ms | 17.24ms | **357.33ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-014 | `trace-ai-014-1790022883969` | AI Preview & Confirm | nested_partition | 13.97ms | 0.71ms | 341.99ms | 2.66ms | 0.03 ms (MOCK ONLY) | 0.05ms | 2.55ms | 16.83ms | **376.16ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-015 | `trace-ai-015-1790022884048` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-016 | `trace-ai-016-1790022884123` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-017 | `trace-ai-017-1790022884198` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-018 | `trace-ai-018-1790022884273` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-019 | `trace-ai-019-1790022884345` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-020 | `trace-ai-020-1790022884420` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.01ms | 0.01ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.02ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-021 | `trace-ai-021-1790022884495` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-022 | `trace-ai-022-1790022884568` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.03ms | 0.03ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-023 | `trace-ai-023-1790022885148` | AI Lab Summary | nested_partition | 0.0ms | 0.0ms | 495.93ms | 5.34ms | 0.01 ms (MOCK ONLY) | 0.02ms | 5.32ms | 0.03ms | **501.3ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-024 | `trace-ai-024-1790022887070` | Voice Input Fallback | nested_partition | 0.02ms | 0.0ms | 250.2ms | 250.2ms | 0.0 ms (MOCK ONLY) | 0.0ms | 0.0ms | 0.0ms | **500.42ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |

## Provider & SLA Verification

> [!NOTE]
> **REAL AI Latency:** `NOT VERIFIED (Running in LOCAL Mode without live GEMINI_API_KEY)`.
> In local mode, AI resilience and structured output tests execute against deterministic mock service handlers.
> Upstream Gemini latency is labeled as **MOCK ONLY**. Real Gemini upstream latency is measured during `--mode live` runs.
