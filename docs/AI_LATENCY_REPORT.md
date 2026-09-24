# KAI Student OS — AI Latency & Performance Breakdown Report

**Date:** 2026-09-25 00:20:37  
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
| **Total Wall Clock** | 2.53ms | 4.71ms | 5.54ms | 10.15ms | 12.26ms | Verified against active mode |
| **Network Wire Transport** | 0.5ms | 2.68ms | 2.93ms | 5.04ms | 5.4ms | Verified against active mode |
| **Backend Processing** | 1.92ms | 2.02ms | 2.58ms | 5.16ms | 7.64ms | Verified against active mode |
| **Gemini Inference** | 0.01ms | 0.02ms | 0.53ms | 2.82ms | 5.1ms | **MOCK ONLY** in LOCAL mode |

## Latency Measurements Breakdown

| Test ID | Trace ID | Scenario | Model | Frontend | Gap | Network (Wire) | Backend | Gemini Upstream | Validation | DB Lookup | Render | Total Wall Clock | Provider | Mock SLA (<500ms) | Real AI SLA (<3s) | Math Integrity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AI-001 | `trace-ai-001-1790284782791` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 5.4ms | 2.14ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.05ms | 0.03ms | **7.57ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-002 | `trace-ai-002-1790284782870` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.79ms | 2.09ms | 0.03 ms (MOCK ONLY) | 0.01ms | 2.02ms | 0.03ms | **4.91ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-003 | `trace-ai-003-1790284782947` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.66ms | 2.0ms | 0.02 ms (MOCK ONLY) | 0.03ms | 1.94ms | 0.02ms | **4.68ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-004 | `trace-ai-004-1790284783022` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.74ms | 2.04ms | 0.02 ms (MOCK ONLY) | 0.03ms | 1.98ms | 0.02ms | **4.8ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-005 | `trace-ai-005-1790284783097` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.66ms | 1.96ms | 0.02 ms (MOCK ONLY) | 0.01ms | 1.92ms | 0.02ms | **4.64ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-006 | `trace-ai-006-1790284783171` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 0.5ms | 2.02ms | 0.03 ms (MOCK ONLY) | 1.0ms | 1.0ms | 0.01ms | **2.53ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-007 | `trace-ai-007-1790284783247` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.68ms | 2.02ms | 0.02 ms (MOCK ONLY) | 0.01ms | 1.98ms | 0.02ms | **4.72ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-008 | `trace-ai-008-1790284783329` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 4.6ms | 7.64ms | 5.1 ms (MOCK ONLY) | 0.55ms | 1.96ms | 0.02ms | **12.26ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-009 | `trace-ai-009-1790284783403` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.68ms | 2.01ms | 0.03 ms (MOCK ONLY) | 0.01ms | 1.96ms | 0.02ms | **4.71ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-010 | `trace-ai-010-1790284783480` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.61ms | 1.92ms | 0.01 ms (MOCK ONLY) | 0.01ms | 1.88ms | 0.02ms | **4.55ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-011 | `trace-ai-011-1790284785987` | AI Preview & Confirm | nested_partition | 12.74ms | 0.02ms | 273.79ms | 2.52ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.42ms | 16.2ms | **305.27ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-012 | `trace-ai-012-1790284788588` | AI Preview & Confirm | nested_partition | 13.52ms | 0.02ms | 300.88ms | 2.57ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.48ms | 17.18ms | **334.17ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-013 | `trace-ai-013-1790284791099` | AI Preview & Confirm | nested_partition | 13.07ms | 0.02ms | 190.56ms | 2.51ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.42ms | 17.37ms | **223.52ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-014 | `trace-ai-014-1790284794046` | AI Preview & Confirm | nested_partition | 13.19ms | 0.63ms | 289.7ms | 2.42ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.33ms | 16.89ms | **322.83ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-015 | `trace-ai-015-1790284794126` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-016 | `trace-ai-016-1790284794195` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-017 | `trace-ai-017-1790284794265` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-018 | `trace-ai-018-1790284794337` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-019 | `trace-ai-019-1790284794407` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-020 | `trace-ai-020-1790284794476` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.01ms | 0.01ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-021 | `trace-ai-021-1790284794546` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-022 | `trace-ai-022-1790284794620` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-023 | `trace-ai-023-1790284795175` | AI Lab Summary | nested_partition | 0.0ms | 0.0ms | 479.52ms | 5.26ms | 0.01 ms (MOCK ONLY) | 0.03ms | 5.22ms | 0.03ms | **484.81ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-024 | `trace-ai-024-1790284797280` | Voice Input Fallback | nested_partition | 0.03ms | 0.0ms | 222.74ms | 222.74ms | 0.0 ms (MOCK ONLY) | 0.0ms | 0.0ms | 0.0ms | **445.51ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |

## Provider & SLA Verification

> [!NOTE]
> **REAL AI Latency:** `NOT VERIFIED (Running in LOCAL Mode without live GEMINI_API_KEY)`.
> In local mode, AI resilience and structured output tests execute against deterministic mock service handlers.
> Upstream Gemini latency is labeled as **MOCK ONLY**. Real Gemini upstream latency is measured during `--mode live` runs.
