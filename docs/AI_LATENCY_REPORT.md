# KAI Student OS — AI Latency & Performance Breakdown Report

**Date:** 2026-09-22 23:12:25  
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
| **Total Wall Clock** | 2.42ms | 4.58ms | 5.37ms | 9.87ms | 11.84ms | Verified against active mode |
| **Network Wire Transport** | 0.48ms | 2.62ms | 2.84ms | 4.83ms | 5.34ms | Verified against active mode |
| **Backend Processing** | 1.88ms | 1.94ms | 2.51ms | 5.13ms | 7.61ms | Verified against active mode |
| **Gemini Inference** | 0.01ms | 0.02ms | 0.53ms | 2.83ms | 5.12ms | **MOCK ONLY** in LOCAL mode |

## Latency Measurements Breakdown

| Test ID | Trace ID | Scenario | Model | Frontend | Gap | Network (Wire) | Backend | Gemini Upstream | Validation | DB Lookup | Render | Total Wall Clock | Provider | Mock SLA (<500ms) | Real AI SLA (<3s) | Math Integrity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AI-001 | `trace-ai-001-1790107893255` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 5.34ms | 2.09ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.01ms | 0.03ms | **7.46ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-002 | `trace-ai-002-1790107893329` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.64ms | 1.92ms | 0.02 ms (MOCK ONLY) | 0.01ms | 1.87ms | 0.02ms | **4.58ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-003 | `trace-ai-003-1790107893403` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.6ms | 1.96ms | 0.02 ms (MOCK ONLY) | 0.03ms | 1.9ms | 0.02ms | **4.57ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-004 | `trace-ai-004-1790107893479` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.58ms | 1.9ms | 0.02 ms (MOCK ONLY) | 0.03ms | 1.84ms | 0.02ms | **4.49ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-005 | `trace-ai-005-1790107893553` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.65ms | 1.92ms | 0.01 ms (MOCK ONLY) | 0.01ms | 1.89ms | 0.02ms | **4.59ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-006 | `trace-ai-006-1790107893626` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 0.48ms | 1.93ms | 0.03 ms (MOCK ONLY) | 1.0ms | 1.0ms | 0.01ms | **2.42ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-007 | `trace-ai-007-1790107893702` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.72ms | 1.96ms | 0.01 ms (MOCK ONLY) | 0.01ms | 1.93ms | 0.02ms | **4.7ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-008 | `trace-ai-008-1790107893784` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 4.21ms | 7.61ms | 5.12 ms (MOCK ONLY) | 0.55ms | 1.91ms | 0.02ms | **11.84ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-009 | `trace-ai-009-1790107893858` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.57ms | 1.97ms | 0.03 ms (MOCK ONLY) | 0.01ms | 1.92ms | 0.02ms | **4.56ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-010 | `trace-ai-010-1790107893934` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.61ms | 1.88ms | 0.01 ms (MOCK ONLY) | 0.01ms | 1.85ms | 0.02ms | **4.51ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-011 | `trace-ai-011-1790107896539` | AI Preview & Confirm | nested_partition | 14.53ms | 0.02ms | 514.05ms | 2.52ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.43ms | 18.36ms | **549.49ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-012 | `trace-ai-012-1790107898961` | AI Preview & Confirm | nested_partition | 13.04ms | 0.02ms | 209.1ms | 2.46ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.37ms | 16.91ms | **241.53ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-013 | `trace-ai-013-1790107901683` | AI Preview & Confirm | nested_partition | 14.05ms | 0.02ms | 548.03ms | 2.76ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.66ms | 17.51ms | **582.38ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-014 | `trace-ai-014-1790107904824` | AI Preview & Confirm | nested_partition | 14.78ms | 0.7ms | 299.06ms | 2.42ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.34ms | 17.1ms | **334.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-015 | `trace-ai-015-1790107904904` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-016 | `trace-ai-016-1790107904973` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.01ms | 0.01ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-017 | `trace-ai-017-1790107905042` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-018 | `trace-ai-018-1790107905112` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-019 | `trace-ai-019-1790107905182` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-020 | `trace-ai-020-1790107905250` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.01ms | 0.01ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.02ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-021 | `trace-ai-021-1790107905318` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-022 | `trace-ai-022-1790107905386` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-023 | `trace-ai-023-1790107905940` | AI Lab Summary | nested_partition | 0.0ms | 0.0ms | 479.52ms | 4.99ms | 0.01 ms (MOCK ONLY) | 0.02ms | 4.96ms | 0.03ms | **484.54ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-024 | `trace-ai-024-1790107908927` | Voice Input Fallback | nested_partition | 0.02ms | 0.0ms | 756.81ms | 756.81ms | 0.0 ms (MOCK ONLY) | 0.0ms | 0.0ms | 0.0ms | **1513.64ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |

## Provider & SLA Verification

> [!NOTE]
> **REAL AI Latency:** `NOT VERIFIED (Running in LOCAL Mode without live GEMINI_API_KEY)`.
> In local mode, AI resilience and structured output tests execute against deterministic mock service handlers.
> Upstream Gemini latency is labeled as **MOCK ONLY**. Real Gemini upstream latency is measured during `--mode live` runs.
