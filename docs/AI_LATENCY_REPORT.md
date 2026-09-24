# KAI Student OS — AI Latency & Performance Breakdown Report

**Date:** 2026-09-25 00:45:35  
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
| **Total Wall Clock** | 2.5ms | 4.78ms | 5.54ms | 9.99ms | 12.1ms | Verified against active mode |
| **Network Wire Transport** | 0.5ms | 2.72ms | 2.91ms | 4.85ms | 5.23ms | Verified against active mode |
| **Backend Processing** | 1.97ms | 2.02ms | 2.61ms | 5.21ms | 7.69ms | Verified against active mode |
| **Gemini Inference** | 0.01ms | 0.02ms | 0.53ms | 2.82ms | 5.1ms | **MOCK ONLY** in LOCAL mode |

## Latency Measurements Breakdown

| Test ID | Trace ID | Scenario | Model | Frontend | Gap | Network (Wire) | Backend | Gemini Upstream | Validation | DB Lookup | Render | Total Wall Clock | Provider | Mock SLA (<500ms) | Real AI SLA (<3s) | Math Integrity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AI-001 | `trace-ai-001-1790286280764` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 5.23ms | 2.17ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.09ms | 0.03ms | **7.42ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-002 | `trace-ai-002-1790286280841` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.73ms | 2.02ms | 0.02 ms (MOCK ONLY) | 0.01ms | 1.97ms | 0.02ms | **4.77ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-003 | `trace-ai-003-1790286280916` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.73ms | 2.07ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.01ms | 0.02ms | **4.82ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-004 | `trace-ai-004-1790286280993` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.62ms | 1.97ms | 0.02 ms (MOCK ONLY) | 0.03ms | 1.9ms | 0.02ms | **4.61ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-005 | `trace-ai-005-1790286281069` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.71ms | 2.01ms | 0.01 ms (MOCK ONLY) | 0.01ms | 1.97ms | 0.02ms | **4.74ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-006 | `trace-ai-006-1790286281142` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 0.5ms | 1.99ms | 0.03 ms (MOCK ONLY) | 1.0ms | 1.0ms | 0.01ms | **2.5ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-007 | `trace-ai-007-1790286281220` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.71ms | 2.03ms | 0.01 ms (MOCK ONLY) | 0.01ms | 2.0ms | 0.02ms | **4.76ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-008 | `trace-ai-008-1790286281305` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 4.39ms | 7.69ms | 5.1 ms (MOCK ONLY) | 0.55ms | 2.01ms | 0.02ms | **12.1ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-009 | `trace-ai-009-1790286281382` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.74ms | 2.02ms | 0.03 ms (MOCK ONLY) | 0.01ms | 1.97ms | 0.02ms | **4.78ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-010 | `trace-ai-010-1790286281458` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.71ms | 2.13ms | 0.01 ms (MOCK ONLY) | 0.01ms | 2.09ms | 0.02ms | **4.86ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-011 | `trace-ai-011-1790286284035` | AI Preview & Confirm | nested_partition | 13.61ms | 0.02ms | 235.79ms | 2.55ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.46ms | 16.34ms | **268.31ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-012 | `trace-ai-012-1790286286703` | AI Preview & Confirm | nested_partition | 13.46ms | 0.02ms | 303.96ms | 2.52ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.43ms | 16.6ms | **336.56ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-013 | `trace-ai-013-1790286289324` | AI Preview & Confirm | nested_partition | 12.47ms | 0.02ms | 293.24ms | 2.59ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.5ms | 16.34ms | **324.66ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-014 | `trace-ai-014-1790286292216` | AI Preview & Confirm | nested_partition | 13.44ms | 0.66ms | 184.53ms | 2.52ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.43ms | 16.26ms | **217.41ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-015 | `trace-ai-015-1790286292287` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-016 | `trace-ai-016-1790286292356` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.01ms | 0.01ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-017 | `trace-ai-017-1790286292425` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-018 | `trace-ai-018-1790286292497` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-019 | `trace-ai-019-1790286292569` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-020 | `trace-ai-020-1790286292640` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.01ms | 0.01ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.02ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-021 | `trace-ai-021-1790286292717` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-022 | `trace-ai-022-1790286292788` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-023 | `trace-ai-023-1790286293351` | AI Lab Summary | nested_partition | 0.0ms | 0.0ms | 488.28ms | 5.24ms | 0.01 ms (MOCK ONLY) | 0.03ms | 5.2ms | 0.03ms | **493.55ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-024 | `trace-ai-024-1790286295327` | Voice Input Fallback | nested_partition | 0.03ms | 0.0ms | 179.13ms | 179.13ms | 0.0 ms (MOCK ONLY) | 0.0ms | 0.0ms | 0.0ms | **358.3ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |

## Provider & SLA Verification

> [!NOTE]
> **REAL AI Latency:** `NOT VERIFIED (Running in LOCAL Mode without live GEMINI_API_KEY)`.
> In local mode, AI resilience and structured output tests execute against deterministic mock service handlers.
> Upstream Gemini latency is labeled as **MOCK ONLY**. Real Gemini upstream latency is measured during `--mode live` runs.
