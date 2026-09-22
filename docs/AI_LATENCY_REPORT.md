# KAI Student OS — AI Latency & Performance Breakdown Report

**Date:** 2026-09-23 00:53:09  
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
| **Total Wall Clock** | 2.75ms | 5.79ms | 6.5ms | 11.49ms | 13.8ms | Verified against active mode |
| **Network Wire Transport** | 0.55ms | 3.19ms | 3.4ms | 5.64ms | 6.4ms | Verified against active mode |
| **Backend Processing** | 2.09ms | 2.4ms | 3.07ms | 6.41ms | 9.07ms | Verified against active mode |
| **Gemini Inference** | 0.01ms | 0.03ms | 0.67ms | 3.56ms | 6.44ms | **MOCK ONLY** in LOCAL mode |

## Latency Measurements Breakdown

| Test ID | Trace ID | Scenario | Model | Frontend | Gap | Network (Wire) | Backend | Gemini Upstream | Validation | DB Lookup | Render | Total Wall Clock | Provider | Mock SLA (<500ms) | Real AI SLA (<3s) | Math Integrity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AI-001 | `trace-ai-001-1790113935178` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 6.4ms | 2.22ms | 0.03 ms (MOCK ONLY) | 0.04ms | 2.13ms | 0.03ms | **8.66ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-002 | `trace-ai-002-1790113935266` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 3.34ms | 2.58ms | 0.04 ms (MOCK ONLY) | 0.03ms | 2.49ms | 0.04ms | **5.96ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-003 | `trace-ai-003-1790113935353` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.86ms | 2.09ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.02ms | 0.03ms | **4.98ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-004 | `trace-ai-004-1790113935441` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 3.42ms | 2.61ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.54ms | 0.02ms | **6.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-005 | `trace-ai-005-1790113935526` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 3.01ms | 2.58ms | 0.02 ms (MOCK ONLY) | 0.01ms | 2.53ms | 0.02ms | **5.62ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-006 | `trace-ai-006-1790113935612` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 0.55ms | 2.19ms | 0.03 ms (MOCK ONLY) | 1.0ms | 1.0ms | 0.01ms | **2.75ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-007 | `trace-ai-007-1790113935700` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 3.88ms | 3.17ms | 0.02 ms (MOCK ONLY) | 0.02ms | 3.12ms | 0.03ms | **7.07ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-008 | `trace-ai-008-1790113935801` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 4.71ms | 9.07ms | 6.44 ms (MOCK ONLY) | 0.58ms | 2.02ms | 0.02ms | **13.8ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-009 | `trace-ai-009-1790113935892` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 3.05ms | 2.11ms | 0.03 ms (MOCK ONLY) | 0.01ms | 2.06ms | 0.02ms | **5.18ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-010 | `trace-ai-010-1790113935977` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.78ms | 2.1ms | 0.01 ms (MOCK ONLY) | 0.01ms | 2.06ms | 0.02ms | **4.9ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-011 | `trace-ai-011-1790113938755` | AI Preview & Confirm | nested_partition | 18.39ms | 0.02ms | 356.32ms | 3.8ms | 0.02 ms (MOCK ONLY) | 0.04ms | 3.7ms | 16.3ms | **394.84ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-012 | `trace-ai-012-1790113941423` | AI Preview & Confirm | nested_partition | 15.97ms | 0.02ms | 331.43ms | 2.64ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.55ms | 19.21ms | **369.28ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-013 | `trace-ai-013-1790113944080` | AI Preview & Confirm | nested_partition | 17.48ms | 0.03ms | 287.96ms | 3.02ms | 0.03 ms (MOCK ONLY) | 0.04ms | 2.9ms | 19.08ms | **327.57ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-014 | `trace-ai-014-1790113946548` | AI Preview & Confirm | nested_partition | 18.16ms | 0.76ms | 360.16ms | 2.61ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.5ms | 17.12ms | **398.81ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-015 | `trace-ai-015-1790113946632` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-016 | `trace-ai-016-1790113946714` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-017 | `trace-ai-017-1790113946790` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-018 | `trace-ai-018-1790113946870` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-019 | `trace-ai-019-1790113946949` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.03ms | 0.03ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-020 | `trace-ai-020-1790113947025` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.01ms | 0.01ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-021 | `trace-ai-021-1790113947106` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-022 | `trace-ai-022-1790113947182` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-023 | `trace-ai-023-1790113947796` | AI Lab Summary | nested_partition | 0.0ms | 0.0ms | 527.6ms | 5.99ms | 0.01 ms (MOCK ONLY) | 0.02ms | 5.95ms | 0.04ms | **533.63ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-024 | `trace-ai-024-1790113949896` | Voice Input Fallback | nested_partition | 0.03ms | 0.0ms | 268.04ms | 268.04ms | 0.0 ms (MOCK ONLY) | 0.0ms | 0.0ms | 0.0ms | **536.11ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |

## Provider & SLA Verification

> [!NOTE]
> **REAL AI Latency:** `NOT VERIFIED (Running in LOCAL Mode without live GEMINI_API_KEY)`.
> In local mode, AI resilience and structured output tests execute against deterministic mock service handlers.
> Upstream Gemini latency is labeled as **MOCK ONLY**. Real Gemini upstream latency is measured during `--mode live` runs.
