# KAI Student OS — AI Latency & Performance Breakdown Report

**Date:** 2026-09-23 00:39:22  
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
| **Total Wall Clock** | 3.24ms | 5.21ms | 6.17ms | 11.28ms | 13.16ms | Verified against active mode |
| **Network Wire Transport** | 0.65ms | 3.04ms | 3.31ms | 5.71ms | 6.6ms | Verified against active mode |
| **Backend Processing** | 1.97ms | 2.18ms | 2.85ms | 5.85ms | 8.52ms | Verified against active mode |
| **Gemini Inference** | 0.01ms | 0.02ms | 0.62ms | 3.3ms | 5.98ms | **MOCK ONLY** in LOCAL mode |

## Latency Measurements Breakdown

| Test ID | Trace ID | Scenario | Model | Frontend | Gap | Network (Wire) | Backend | Gemini Upstream | Validation | DB Lookup | Render | Total Wall Clock | Provider | Mock SLA (<500ms) | Real AI SLA (<3s) | Math Integrity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AI-001 | `trace-ai-001-1790113109919` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 6.6ms | 2.35ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.27ms | 0.03ms | **8.98ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-002 | `trace-ai-002-1790113110008` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 3.09ms | 2.18ms | 0.03 ms (MOCK ONLY) | 0.02ms | 2.12ms | 0.03ms | **5.3ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-003 | `trace-ai-003-1790113110099` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.92ms | 2.18ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.12ms | 0.02ms | **5.12ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-004 | `trace-ai-004-1790113110187` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 3.57ms | 2.29ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.21ms | 0.02ms | **5.89ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-005 | `trace-ai-005-1790113110274` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 3.0ms | 2.11ms | 0.02 ms (MOCK ONLY) | 0.01ms | 2.07ms | 0.02ms | **5.13ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-006 | `trace-ai-006-1790113110357` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 0.65ms | 2.58ms | 0.03 ms (MOCK ONLY) | 1.0ms | 1.0ms | 0.01ms | **3.24ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-007 | `trace-ai-007-1790113110439` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.69ms | 1.97ms | 0.01 ms (MOCK ONLY) | 0.01ms | 1.94ms | 0.02ms | **4.68ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-008 | `trace-ai-008-1790113110529` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 4.62ms | 8.52ms | 5.98 ms (MOCK ONLY) | 0.57ms | 1.95ms | 0.02ms | **13.16ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-009 | `trace-ai-009-1790113110611` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 3.12ms | 2.17ms | 0.03 ms (MOCK ONLY) | 0.01ms | 2.12ms | 0.02ms | **5.31ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-010 | `trace-ai-010-1790113110692` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 2.8ms | 2.12ms | 0.01 ms (MOCK ONLY) | 0.01ms | 2.08ms | 0.02ms | **4.94ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-011 | `trace-ai-011-1790113113445` | AI Preview & Confirm | nested_partition | 14.08ms | 0.02ms | 328.9ms | 2.47ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.37ms | 16.46ms | **361.93ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-012 | `trace-ai-012-1790113115791` | AI Preview & Confirm | nested_partition | 14.14ms | 0.02ms | 280.63ms | 2.75ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.66ms | 17.98ms | **315.52ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-013 | `trace-ai-013-1790113118113` | AI Preview & Confirm | nested_partition | 13.18ms | 0.02ms | 266.51ms | 2.37ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.29ms | 17.0ms | **299.08ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-014 | `trace-ai-014-1790113120394` | AI Preview & Confirm | nested_partition | 14.75ms | 0.71ms | 262.02ms | 2.42ms | 0.02 ms (MOCK ONLY) | 0.03ms | 2.34ms | 17.15ms | **297.06ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-015 | `trace-ai-015-1790113120470` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-016 | `trace-ai-016-1790113120543` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-017 | `trace-ai-017-1790113120617` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-018 | `trace-ai-018-1790113120689` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.03ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-019 | `trace-ai-019-1790113120766` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.03ms | 0.03ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-020 | `trace-ai-020-1790113120840` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.01ms | 0.01ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.02ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-021 | `trace-ai-021-1790113120920` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-022 | `trace-ai-022-1790113120997` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.03ms | 0.03ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-023 | `trace-ai-023-1790113121604` | AI Lab Summary | nested_partition | 0.0ms | 0.0ms | 523.46ms | 5.21ms | 0.01 ms (MOCK ONLY) | 0.02ms | 5.18ms | 0.03ms | **528.71ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-024 | `trace-ai-024-1790113123659` | Voice Input Fallback | nested_partition | 0.03ms | 0.0ms | 233.34ms | 233.34ms | 0.0 ms (MOCK ONLY) | 0.0ms | 0.0ms | 0.0ms | **466.7ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |

## Provider & SLA Verification

> [!NOTE]
> **REAL AI Latency:** `NOT VERIFIED (Running in LOCAL Mode without live GEMINI_API_KEY)`.
> In local mode, AI resilience and structured output tests execute against deterministic mock service handlers.
> Upstream Gemini latency is labeled as **MOCK ONLY**. Real Gemini upstream latency is measured during `--mode live` runs.
