# KAI Student OS — AI Latency & Performance Breakdown Report

**Date:** 2026-09-23 00:09:02  
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
| **Total Wall Clock** | 2.57ms | 4.7ms | 5.57ms | 10.3ms | 12.05ms | Verified against active mode |
| **Network Wire Transport** | 0.51ms | 2.72ms | 2.91ms | 4.91ms | 5.31ms | Verified against active mode |
| **Backend Processing** | 1.92ms | 2.02ms | 2.64ms | 5.45ms | 7.6ms | Verified against active mode |
| **Gemini Inference** | 0.01ms | 0.02ms | 0.53ms | 2.81ms | 5.09ms | **MOCK ONLY** in LOCAL mode |

## Latency Measurements Breakdown

| Test ID | Trace ID | Scenario | Model | Frontend | Gap | Network (Wire) | Backend | Gemini Upstream | Validation | DB Lookup | Render | Total Wall Clock | Provider | Mock SLA (<500ms) | Real AI SLA (<3s) | Math Integrity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AI-001 | `trace-ai-001-1790111293555` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 5.31ms | 2.83ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.75ms | 0.03ms | **8.17ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-002 | `trace-ai-002-1790111293631` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.79ms | 2.11ms | 0.02 ms (MOCK ONLY) | 0.01ms | 2.05ms | 0.02ms | **4.92ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-003 | `trace-ai-003-1790111293706` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.64ms | 2.05ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.0ms | 0.02ms | **4.71ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-004 | `trace-ai-004-1790111293782` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.56ms | 2.0ms | 0.02 ms (MOCK ONLY) | 0.03ms | 1.94ms | 0.02ms | **4.58ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-005 | `trace-ai-005-1790111293860` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.68ms | 1.92ms | 0.02 ms (MOCK ONLY) | 0.01ms | 1.88ms | 0.02ms | **4.62ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-006 | `trace-ai-006-1790111293932` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 0.51ms | 2.04ms | 0.03 ms (MOCK ONLY) | 1.0ms | 1.0ms | 0.01ms | **2.57ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-007 | `trace-ai-007-1790111294007` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.75ms | 1.94ms | 0.01 ms (MOCK ONLY) | 0.01ms | 1.9ms | 0.02ms | **4.71ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-008 | `trace-ai-008-1790111294092` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 4.43ms | 7.6ms | 5.09 ms (MOCK ONLY) | 0.56ms | 1.93ms | 0.02ms | **12.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-009 | `trace-ai-009-1790111294166` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.72ms | 1.95ms | 0.03 ms (MOCK ONLY) | 0.01ms | 1.9ms | 0.02ms | **4.69ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-010 | `trace-ai-010-1790111294241` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.72ms | 1.93ms | 0.01 ms (MOCK ONLY) | 0.01ms | 1.89ms | 0.02ms | **4.67ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-011 | `trace-ai-011-1790111296787` | AI Preview & Confirm | nested_partition | 14.02ms | 0.02ms | 393.49ms | 2.32ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.23ms | 16.01ms | **425.86ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-012 | `trace-ai-012-1790111299142` | AI Preview & Confirm | nested_partition | 13.61ms | 0.02ms | 212.75ms | 2.48ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.39ms | 15.4ms | **244.26ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-013 | `trace-ai-013-1790111301576` | AI Preview & Confirm | nested_partition | 14.44ms | 0.02ms | 222.07ms | 2.46ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.36ms | 16.5ms | **255.49ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-014 | `trace-ai-014-1790111303784` | AI Preview & Confirm | nested_partition | 12.57ms | 0.62ms | 212.79ms | 2.39ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.3ms | 16.44ms | **244.81ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-015 | `trace-ai-015-1790111303856` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-016 | `trace-ai-016-1790111303927` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-017 | `trace-ai-017-1790111303997` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-018 | `trace-ai-018-1790111304066` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-019 | `trace-ai-019-1790111304135` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-020 | `trace-ai-020-1790111304203` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.01ms | 0.01ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-021 | `trace-ai-021-1790111304273` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-022 | `trace-ai-022-1790111304342` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-023 | `trace-ai-023-1790111304922` | AI Lab Summary | nested_partition | 0.0ms | 0.0ms | 506.26ms | 5.1ms | 0.01 ms (MOCK ONLY) | 0.02ms | 5.07ms | 0.03ms | **511.39ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-024 | `trace-ai-024-1790111306702` | Voice Input Fallback | nested_partition | 0.03ms | 0.0ms | 193.11ms | 193.11ms | 0.0 ms (MOCK ONLY) | 0.0ms | 0.0ms | 0.0ms | **386.24ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |

## Provider & SLA Verification

> [!NOTE]
> **REAL AI Latency:** `NOT VERIFIED (Running in LOCAL Mode without live GEMINI_API_KEY)`.
> In local mode, AI resilience and structured output tests execute against deterministic mock service handlers.
> Upstream Gemini latency is labeled as **MOCK ONLY**. Real Gemini upstream latency is measured during `--mode live` runs.
