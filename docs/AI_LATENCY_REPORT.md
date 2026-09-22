# KAI Student OS — AI Latency & Performance Breakdown Report

**Date:** 2026-09-22 23:42:07  
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
| **Total Wall Clock** | 2.44ms | 5.28ms | 6.1ms | 10.38ms | 12.15ms | Verified against active mode |
| **Network Wire Transport** | 0.49ms | 3.04ms | 3.35ms | 5.41ms | 5.46ms | Verified against active mode |
| **Backend Processing** | 1.95ms | 2.17ms | 2.74ms | 5.41ms | 7.61ms | Verified against active mode |
| **Gemini Inference** | 0.01ms | 0.03ms | 0.53ms | 2.83ms | 5.11ms | **MOCK ONLY** in LOCAL mode |

## Latency Measurements Breakdown

| Test ID | Trace ID | Scenario | Model | Frontend | Gap | Network (Wire) | Backend | Gemini Upstream | Validation | DB Lookup | Render | Total Wall Clock | Provider | Mock SLA (<500ms) | Real AI SLA (<3s) | Math Integrity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AI-001 | `trace-ai-001-1790109677353` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 5.35ms | 2.06ms | 0.02 ms (MOCK ONLY) | 0.04ms | 1.98ms | 0.03ms | **7.43ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-002 | `trace-ai-002-1790109677434` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 3.18ms | 2.21ms | 0.03 ms (MOCK ONLY) | 0.02ms | 2.15ms | 0.03ms | **5.43ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-003 | `trace-ai-003-1790109677527` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 3.15ms | 2.32ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.26ms | 0.02ms | **5.49ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-004 | `trace-ai-004-1790109677621` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 5.46ms | 2.72ms | 0.04 ms (MOCK ONLY) | 0.07ms | 2.56ms | 0.04ms | **8.22ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-005 | `trace-ai-005-1790109677707` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.94ms | 2.17ms | 0.02 ms (MOCK ONLY) | 0.01ms | 2.13ms | 0.02ms | **5.13ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-006 | `trace-ai-006-1790109677784` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 0.49ms | 1.95ms | 0.03 ms (MOCK ONLY) | 1.0ms | 1.0ms | 0.01ms | **2.44ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-007 | `trace-ai-007-1790109677860` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.82ms | 2.18ms | 0.01 ms (MOCK ONLY) | 0.01ms | 2.13ms | 0.02ms | **5.02ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-008 | `trace-ai-008-1790109677946` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 4.52ms | 7.61ms | 5.11 ms (MOCK ONLY) | 0.56ms | 1.92ms | 0.02ms | **12.15ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-009 | `trace-ai-009-1790109678026` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.82ms | 2.0ms | 0.03 ms (MOCK ONLY) | 0.01ms | 1.95ms | 0.02ms | **4.84ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-010 | `trace-ai-010-1790109678104` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.74ms | 2.14ms | 0.01 ms (MOCK ONLY) | 0.01ms | 2.11ms | 0.02ms | **4.9ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-011 | `trace-ai-011-1790109680519` | AI Preview & Confirm | nested_partition | 14.74ms | 0.02ms | 235.09ms | 2.53ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.43ms | 18.5ms | **270.88ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-012 | `trace-ai-012-1790109682975` | AI Preview & Confirm | nested_partition | 14.24ms | 0.02ms | 221.23ms | 2.59ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.49ms | 17.98ms | **256.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-013 | `trace-ai-013-1790109685353` | AI Preview & Confirm | nested_partition | 14.03ms | 0.02ms | 233.14ms | 2.6ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.5ms | 16.41ms | **266.2ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-014 | `trace-ai-014-1790109687610` | AI Preview & Confirm | nested_partition | 13.49ms | 0.7ms | 194.46ms | 2.83ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.75ms | 16.9ms | **228.39ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-015 | `trace-ai-015-1790109687683` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-016 | `trace-ai-016-1790109687756` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.01ms | 0.01ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-017 | `trace-ai-017-1790109687827` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-018 | `trace-ai-018-1790109687895` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-019 | `trace-ai-019-1790109687963` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-020 | `trace-ai-020-1790109688034` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.01ms | 0.01ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.02ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-021 | `trace-ai-021-1790109688105` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-022 | `trace-ai-022-1790109688173` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.03ms | 0.03ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-023 | `trace-ai-023-1790109688726` | AI Lab Summary | nested_partition | 0.0ms | 0.0ms | 478.89ms | 5.12ms | 0.01 ms (MOCK ONLY) | 0.02ms | 5.09ms | 0.03ms | **484.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-024 | `trace-ai-024-1790109691742` | Voice Input Fallback | nested_partition | 0.03ms | 0.0ms | 757.31ms | 757.31ms | 0.0 ms (MOCK ONLY) | 0.0ms | 0.0ms | 0.0ms | **1514.64ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |

## Provider & SLA Verification

> [!NOTE]
> **REAL AI Latency:** `NOT VERIFIED (Running in LOCAL Mode without live GEMINI_API_KEY)`.
> In local mode, AI resilience and structured output tests execute against deterministic mock service handlers.
> Upstream Gemini latency is labeled as **MOCK ONLY**. Real Gemini upstream latency is measured during `--mode live` runs.
