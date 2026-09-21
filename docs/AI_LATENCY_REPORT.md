# KAI Student OS — AI Latency & Performance Breakdown Report

**Date:** 2026-09-21 22:53:58  
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
| **Total Wall Clock** | 513.16ms | 1291.65ms | 1221.8ms | 1338.63ms | 1360.33ms | Verified against active mode |
| **Network Wire Transport** | 102.49ms | 524.65ms | 486.91ms | 562.6ms | 588.71ms | Verified against active mode |
| **Backend Processing** | 409.94ms | 766.89ms | 733.96ms | 784.24ms | 784.94ms | Verified against active mode |
| **Gemini Inference** | 0.01ms | 0.03ms | 2.12ms | 10.59ms | 15.0ms | **MOCK ONLY** in LOCAL mode |

## Latency Measurements Breakdown

| Test ID | Trace ID | Scenario | Model | Frontend | Gap | Network (Wire) | Backend | Gemini Upstream | Validation | DB Lookup | Render | Total Wall Clock | Provider | Mock SLA (<500ms) | Real AI SLA (<3s) | Math Integrity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AI-001 | `trace-ai-001-1790020369236` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 588.71ms | 770.72ms | 0.03 ms (MOCK ONLY) | 0.05ms | 2.72ms | 0.9ms | **1360.33ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-002 | `trace-ai-002-1790020370600` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 514.02ms | 769.42ms | 0.89 ms (MOCK ONLY) | 0.03ms | 2.69ms | 1.08ms | **1284.52ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-003 | `trace-ai-003-1790020371966` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 512.54ms | 769.02ms | 0.03 ms (MOCK ONLY) | 0.04ms | 2.69ms | 1.04ms | **1282.6ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-004 | `trace-ai-004-1790020373350` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 517.64ms | 783.38ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.46ms | 0.89ms | **1301.91ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-005 | `trace-ai-005-1790020374730` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 530.69ms | 762.79ms | 0.02 ms (MOCK ONLY) | 0.01ms | 2.3ms | 0.88ms | **1294.37ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-006 | `trace-ai-006-1790020375325` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 102.49ms | 409.94ms | 15.0 ms (MOCK ONLY) | 1.0ms | 1.0ms | 0.73ms | **513.16ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-007 | `trace-ai-007-1790020376695` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 523.32ms | 761.5ms | 0.01 ms (MOCK ONLY) | 0.01ms | 2.54ms | 0.86ms | **1285.68ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-008 | `trace-ai-008-1790020378089` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 525.99ms | 784.94ms | 5.19 ms (MOCK ONLY) | 0.57ms | 2.68ms | 1.17ms | **1312.1ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-009 | `trace-ai-009-1790020379462` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 527.58ms | 763.16ms | 0.03 ms (MOCK ONLY) | 0.02ms | 2.38ms | 0.85ms | **1291.59ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-010 | `trace-ai-010-1790020380838` | AI Task Parse Pipeli | nested_partition | 0.0ms | 0.0ms | 526.11ms | 764.76ms | 0.02 ms (MOCK ONLY) | 0.01ms | 2.3ms | 0.84ms | **1291.71ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-011 | `trace-ai-011-1790020384340` | AI Preview & Confirm | nested_partition | 17.42ms | 0.02ms | 360.22ms | 788.33ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.4ms | 19.74ms | **1185.74ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-012 | `trace-ai-012-1790020387740` | AI Preview & Confirm | nested_partition | 17.05ms | 0.02ms | 227.28ms | 826.76ms | 0.03 ms (MOCK ONLY) | 0.05ms | 2.47ms | 17.42ms | **1088.54ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-013 | `trace-ai-013-1790020391096` | AI Preview & Confirm | nested_partition | 17.58ms | 0.02ms | 348.72ms | 779.53ms | 0.04 ms (MOCK ONLY) | 0.07ms | 2.9ms | 18.91ms | **1164.75ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-014 | `trace-ai-014-1790020395059` | AI Preview & Confirm | nested_partition | 18.94ms | 0.82ms | 539.92ms | 815.6ms | 0.02 ms (MOCK ONLY) | 0.04ms | 2.43ms | 18.97ms | **1394.25ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-015 | `trace-ai-015-1790020395144` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-016 | `trace-ai-016-1790020395230` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.03ms | 0.03ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-017 | `trace-ai-017-1790020395315` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-018 | `trace-ai-018-1790020395395` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-019 | `trace-ai-019-1790020395479` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.03ms | 0.03ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.06ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-020 | `trace-ai-020-1790020395563` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.01ms | 0.01ms | 0.0 ms (MOCK ONLY) | 0.01ms | 0.0ms | 0.0ms | **0.02ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-021 | `trace-ai-021-1790020395648` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.02ms | 0.02ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.04ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-022 | `trace-ai-022-1790020395726` | AI Resilience & Erro | nested_partition | 0.0ms | 0.0ms | 0.03ms | 0.03ms | 0.0 ms (MOCK ONLY) | 0.02ms | 0.0ms | 0.0ms | **0.05ms** | **MOCK** | ✅ PASS (<500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-023 | `trace-ai-023-1790020397097` | AI Lab Summary | nested_partition | 0.0ms | 0.0ms | 520.81ms | 765.97ms | 0.03 ms (MOCK ONLY) | 760.07ms | 5.87ms | 0.07ms | **1286.84ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |
| AI-024 | `trace-ai-024-1790020399374` | Voice Input Fallback | nested_partition | 0.02ms | 0.0ms | 374.93ms | 374.93ms | 0.0 ms (MOCK ONLY) | 0.0ms | 0.0ms | 0.0ms | **749.88ms** | **MOCK** | ⚠️ BREACH (>500ms) | NOT VERIFIED (Mock Mode) | ✅ VALID |

## Provider & SLA Verification

> [!NOTE]
> **REAL AI Latency:** `NOT VERIFIED (Running in LOCAL Mode without live GEMINI_API_KEY)`.
> In local mode, AI resilience and structured output tests execute against deterministic mock service handlers.
> Upstream Gemini latency is labeled as **MOCK ONLY**. Real Gemini upstream latency is measured during `--mode live` runs.
