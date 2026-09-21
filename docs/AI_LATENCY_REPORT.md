# KAI Student OS — AI Latency & Performance Breakdown Report

**Date:** 2026-09-21 19:18:06  
**Mode:** LOCAL  
**Execution Environment:** Isolated QA (Mocked Gemini Service)  

## Executive Performance Summary

- **Profiling Pipeline Phases:**
  1. `frontend_prepare`: Token, prompt sanitization, payload serialization
  2. `network`: HTTP round-trip latency to `/api/ai/*`
  3. `backend`: FastAPI middleware, auth validation, and routing
  4. `Gemini`: Google Generative AI upstream inference
  5. `validation`: Pydantic structured output validation and schema compliance
  6. `DB`: Atomic persistence and relationship binding
  7. `render`: UI DOM rendering and state hydration

## Latency Measurements Breakdown

| Test ID | Scenario | Frontend | Network | Backend | Gemini Upstream | Validation | DB Persistence | Render | Total End-to-End | Mode / Provider | SLA Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| AI-001 | AI Task Parse Pipeline | 3.0ms | 3781.8ms | 2521.2ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **12606.0ms** | **MOCK** | ⚠️ BREACH |
| AI-002 | AI Task Parse Pipeline | 3.0ms | 3752.4ms | 2501.6ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **12508.0ms** | **MOCK** | ⚠️ BREACH |
| AI-003 | AI Task Parse Pipeline | 3.0ms | 3740.7ms | 2493.8ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **12469.0ms** | **MOCK** | ⚠️ BREACH |
| AI-004 | AI Task Parse Pipeline | 3.0ms | 3803.4ms | 2535.6ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **12678.0ms** | **MOCK** | ⚠️ BREACH |
| AI-005 | AI Task Parse Pipeline | 3.0ms | 3744.9ms | 2496.6ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **12483.0ms** | **MOCK** | ⚠️ BREACH |
| AI-006 | AI Task Parse Pipeline | 3.0ms | 3744.6ms | 2496.4ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **12482.0ms** | **MOCK** | ⚠️ BREACH |
| AI-007 | AI Task Parse Pipeline | 3.0ms | 3732.0ms | 2488.0ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **12440.0ms** | **MOCK** | ⚠️ BREACH |
| AI-008 | AI Task Parse Pipeline | 3.0ms | 3721.2ms | 2480.8ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **12404.0ms** | **MOCK** | ⚠️ BREACH |
| AI-009 | AI Task Parse Pipeline | 3.0ms | 3785.1ms | 2523.4ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **12617.0ms** | **MOCK** | ⚠️ BREACH |
| AI-010 | AI Task Parse Pipeline | 3.0ms | 3724.2ms | 2482.8ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **12414.0ms** | **MOCK** | ⚠️ BREACH |
| AI-011 | AI Preview & Confirm | 3.0ms | 1249.5ms | 833.0ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **4165.0ms** | **MOCK** | ⚠️ BREACH |
| AI-012 | AI Preview & Confirm | 3.0ms | 1239.3ms | 826.2ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **4131.0ms** | **MOCK** | ⚠️ BREACH |
| AI-013 | AI Preview & Confirm | 3.0ms | 1281.0ms | 854.0ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **4270.0ms** | **MOCK** | ⚠️ BREACH |
| AI-014 | AI Preview & Confirm | 3.0ms | 1168.8ms | 779.2ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **3896.0ms** | **MOCK** | ⚠️ BREACH |
| AI-015 | AI Resilience & Errors | 3.0ms | 0.0ms | 0.0ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **0.0ms** | **MOCK** | ✅ PASS (<3s) |
| AI-016 | AI Resilience & Errors | 3.0ms | 0.0ms | 0.0ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **0.0ms** | **MOCK** | ✅ PASS (<3s) |
| AI-017 | AI Resilience & Errors | 3.0ms | 0.0ms | 0.0ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **0.0ms** | **MOCK** | ✅ PASS (<3s) |
| AI-018 | AI Resilience & Errors | 3.0ms | 0.0ms | 0.0ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **0.0ms** | **MOCK** | ✅ PASS (<3s) |
| AI-019 | AI Resilience & Errors | 3.0ms | 0.0ms | 0.0ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **0.0ms** | **MOCK** | ✅ PASS (<3s) |
| AI-020 | AI Resilience & Errors | 3.0ms | 0.0ms | 0.0ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **0.0ms** | **MOCK** | ✅ PASS (<3s) |
| AI-021 | AI Resilience & Errors | 3.0ms | 0.0ms | 0.0ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **0.0ms** | **MOCK** | ✅ PASS (<3s) |
| AI-022 | AI Resilience & Errors | 3.0ms | 0.0ms | 0.0ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **0.0ms** | **MOCK** | ✅ PASS (<3s) |
| AI-023 | AI Lab Summary | 3.0ms | 389.7ms | 259.8ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **1299.0ms** | **MOCK** | ✅ PASS (<3s) |
| AI-024 | Voice Input Fallback | 3.0ms | 232.2ms | 154.8ms | 15.0 ms (mock) | 1.5ms | 2.0ms | 15.0ms | **774.0ms** | **MOCK** | ✅ PASS (<3s) |

## Verification of Real AI Latency

> [!NOTE]
> **REAL AI Latency:** `NOT VERIFIED (Running in LOCAL Mode without live GEMINI_API_KEY)`.
> In local mode, AI resilience and structured output tests execute against deterministic mock service handlers.
> Live Gemini upstream latency is measured during `--mode live` acceptance runs.
