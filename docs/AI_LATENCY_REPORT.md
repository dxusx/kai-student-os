# KAI Student OS — AI Latency & Performance Breakdown Report

**Date:** 2026-09-24 23:39:26  
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
| **Total Wall Clock** | 2.59ms | 4.7ms | 5.5ms | 10.1ms | 12.34ms | Verified against active mode |
| **Network Wire Transport** | 0.52ms | 2.61ms | 2.88ms | 4.99ms | 5.27ms | Verified against active mode |
| **Backend Processing** | 2.0ms | 2.04ms | 2.6ms | 5.16ms | 7.68ms | Verified against active mode |
| **Gemini Inference** | 0.01ms | 0.02ms | 0.54ms | 2.86ms | 5.18ms | **MOCK ONLY** in LOCAL mode |

## Latency Measurements Breakdown

| Test ID | Trace ID | Scenario | Model | Frontend | Gap | Network (Wire) | Backend | Gemini Upstream | Validation | DB Lookup | Render | Total Wall Clock | Provider | Mock SLA (<500ms) | Real AI SLA (<3s) | Math Integrity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AI-001 | `trace-ai-001-1790282311658` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 5.27ms | 2.06ms | 0.02 ms (MOCK ONLY) | 0.03ms | 1.99ms | 0.03ms | **7.36ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-002 | `trace-ai-002-1790282311735` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.63ms | 2.06ms | 0.02 ms (MOCK ONLY) | 0.01ms | 2.01ms | 0.02ms | **4.71ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-003 | `trace-ai-003-1790282311813` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.56ms | 2.0ms | 0.02 ms (MOCK ONLY) | 0.03ms | 1.94ms | 0.02ms | **4.58ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-004 | `trace-ai-004-1790282311889` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.59ms | 2.07ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.01ms | 0.02ms | **4.68ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-005 | `trace-ai-005-1790282311964` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.59ms | 2.0ms | 0.02 ms (MOCK ONLY) | 0.01ms | 1.96ms | 0.02ms | **4.61ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-006 | `trace-ai-006-1790282312037` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 0.52ms | 2.06ms | 0.03 ms (MOCK ONLY) | 1.0ms | 1.0ms | 0.01ms | **2.59ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-007 | `trace-ai-007-1790282312116` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.71ms | 2.03ms | 0.01 ms (MOCK ONLY) | 0.01ms | 1.99ms | 0.02ms | **4.76ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-008 | `trace-ai-008-1790282312200` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 4.64ms | 7.68ms | 5.18 ms (MOCK ONLY) | 0.55ms | 1.93ms | 0.02ms | **12.34ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-009 | `trace-ai-009-1790282312276` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.59ms | 2.03ms | 0.03 ms (MOCK ONLY) | 0.01ms | 1.98ms | 0.02ms | **4.64ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-010 | `trace-ai-010-1790282312353` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.69ms | 2.03ms | 0.01 ms (MOCK ONLY) | 0.01ms | 1.99ms | 0.02ms | **4.74ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-011 | `trace-ai-011-1790282314907` | AI Preview & Confirm | nested_partition | 13.0ms | 0.02ms | 271.41ms | 2.48ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.39ms | 16.83ms | **303.74ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-012 | `trace-ai-012-1790282317507` | AI Preview & Confirm | nested_partition | 13.44ms | 0.02ms | 270.0ms | 2.51ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.42ms | 16.43ms | **302.4ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-013 | `trace-ai-013-1790282320074` | AI Preview & Confirm | nested_partition | 13.68ms | 0.02ms | 215.57ms | 2.73ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.64ms | 17.12ms | **249.12ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-014 | `trace-ai-014-1790282322984` | AI Preview & Confirm | nested_partition | 13.64ms | 0.7ms | 266.58ms | 2.46ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.38ms | 16.82ms | **300.2ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-015 | `trace-ai-015-1790282323057` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-016 | `trace-ai-016-1790282323127` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-017 | `trace-ai-017-1790282323200` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-018 | `trace-ai-018-1790282323271` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-019 | `trace-ai-019-1790282323341` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-020 | `trace-ai-020-1790282323414` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.01ms | 0.01ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.02ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-021 | `trace-ai-021-1790282323485` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-022 | `trace-ai-022-1790282323559` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-023 | `trace-ai-023-1790282324118` | AI Lab Summary | nested_partition | 0.0ms | 0.0ms | 483.87ms | 5.26ms | 0.01 ms (MOCK ONLY) | 0.03ms | 5.22ms | 0.03ms | **489.16ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-024 | `trace-ai-024-1790282326108` | Voice Input Fallback | nested_partition | 0.02ms | 0.0ms | 215.03ms | 215.03ms | 0.0 ms (MOCK ONLY) | 0.0ms | 0.0ms | 0.0ms | **430.08ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |

## Provider & SLA Verification

> [!NOTE]
> **REAL AI Latency:** `NOT VERIFIED (Running in LOCAL Mode without live GEMINI_API_KEY)`.
> In local mode, AI resilience and structured output tests execute against deterministic mock service handlers.
> Upstream Gemini latency is labeled as **MOCK ONLY**. Real Gemini upstream latency is measured during `--mode live` runs.
