# KAI Student OS — AI Latency & Performance Breakdown Report

**Date:** 2026-09-22 01:08:25  
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
| **Total Wall Clock** | 2.48ms | 4.78ms | 5.65ms | 10.5ms | 13.03ms | Verified against active mode |
| **Network Wire Transport** | 0.49ms | 2.7ms | 2.95ms | 5.12ms | 5.27ms | Verified against active mode |
| **Backend Processing** | 1.97ms | 2.1ms | 2.67ms | 5.42ms | 8.07ms | Verified against active mode |
| **Gemini Inference** | 0.01ms | 0.02ms | 0.55ms | 2.97ms | 5.37ms | **MOCK ONLY** in LOCAL mode |

## Latency Measurements Breakdown

| Test ID | Trace ID | Scenario | Model | Frontend | Gap | Network (Wire) | Backend | Gemini Upstream | Validation | DB Lookup | Render | Total Wall Clock | Provider | Mock SLA (<500ms) | Real AI SLA (<3s) | Math Integrity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AI-001 | `trace-ai-001-1790028456221` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 5.27ms | 2.1ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.02ms | 0.03ms | **7.4ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-002 | `trace-ai-002-1790028456296` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.64ms | 2.1ms | 0.02 ms (MOCK ONLY) | 0.01ms | 2.05ms | 0.02ms | **4.76ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-003 | `trace-ai-003-1790028456371` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.72ms | 2.04ms | 0.02 ms (MOCK ONLY) | 0.03ms | 1.98ms | 0.02ms | **4.78ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-004 | `trace-ai-004-1790028456447` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.66ms | 2.1ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.04ms | 0.02ms | **4.78ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-005 | `trace-ai-005-1790028456525` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.68ms | 2.0ms | 0.02 ms (MOCK ONLY) | 0.01ms | 1.96ms | 0.02ms | **4.7ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-006 | `trace-ai-006-1790028456600` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 0.49ms | 1.97ms | 0.03 ms (MOCK ONLY) | 1.0ms | 1.0ms | 0.01ms | **2.48ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-007 | `trace-ai-007-1790028456680` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.67ms | 2.19ms | 0.01 ms (MOCK ONLY) | 0.04ms | 2.13ms | 0.02ms | **4.88ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-008 | `trace-ai-008-1790028456767` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 4.94ms | 8.07ms | 5.37 ms (MOCK ONLY) | 0.57ms | 2.11ms | 0.02ms | **13.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-009 | `trace-ai-009-1790028456849` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.71ms | 2.13ms | 0.03 ms (MOCK ONLY) | 0.01ms | 2.08ms | 0.02ms | **4.86ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-010 | `trace-ai-010-1790028456928` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.72ms | 2.04ms | 0.01 ms (MOCK ONLY) | 0.01ms | 2.01ms | 0.02ms | **4.78ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-011 | `trace-ai-011-1790028459375` | AI Preview & Confirm | nested_partition | 15.04ms | 0.02ms | 294.25ms | 2.65ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.56ms | 18.24ms | **330.2ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-012 | `trace-ai-012-1790028461875` | AI Preview & Confirm | nested_partition | 14.13ms | 0.02ms | 229.54ms | 2.37ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.28ms | 17.1ms | **263.16ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-013 | `trace-ai-013-1790028464286` | AI Preview & Confirm | nested_partition | 16.26ms | 0.02ms | 279.86ms | 2.21ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.12ms | 18.04ms | **316.39ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-014 | `trace-ai-014-1790028467093` | AI Preview & Confirm | nested_partition | 14.5ms | 0.71ms | 217.46ms | 2.48ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.39ms | 16.92ms | **252.07ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-015 | `trace-ai-015-1790028467166` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-016 | `trace-ai-016-1790028467237` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.01ms | 0.01ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-017 | `trace-ai-017-1790028467308` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-018 | `trace-ai-018-1790028467377` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-019 | `trace-ai-019-1790028467446` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-020 | `trace-ai-020-1790028467515` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.01ms | 0.01ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-021 | `trace-ai-021-1790028467586` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-022 | `trace-ai-022-1790028467655` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.03ms | 0.03ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-023 | `trace-ai-023-1790028468218` | AI Lab Summary | nested_partition | 0.0ms | 0.0ms | 485.48ms | 5.22ms | 0.01 ms (MOCK ONLY) | 0.02ms | 5.19ms | 0.03ms | **490.73ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-024 | `trace-ai-024-1790028470090` | Voice Input Fallback | nested_partition | 0.02ms | 0.0ms | 211.03ms | 211.03ms | 0.0 ms (MOCK ONLY) | 0.0ms | 0.0ms | 0.0ms | **422.08ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |

## Provider & SLA Verification

> [!NOTE]
> **REAL AI Latency:** `NOT VERIFIED (Running in LOCAL Mode without live GEMINI_API_KEY)`.
> In local mode, AI resilience and structured output tests execute against deterministic mock service handlers.
> Upstream Gemini latency is labeled as **MOCK ONLY**. Real Gemini upstream latency is measured during `--mode live` runs.
