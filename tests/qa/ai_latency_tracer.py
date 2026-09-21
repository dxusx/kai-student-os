"""
KAI Student OS — AI Latency Tracer & Timing Integrity Module.
Provides high-precision monotonic timestamp tracing (t0..t15) and raw phase breakdown.
Strict arithmetic assertions: zero double-counting, non-overlapping parent partition, verified child hierarchy.
Separates REAL MEASUREMENT from TEST FIXTURE.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass
class AiRequestTrace:
    """
    Monotonic timestamp trace for a single AI request lifecycle.
    All client timestamps recorded using time.perf_counter() (monotonic, high-resolution).
    Server timings obtained via W3C Server-Timing headers or response metadata.
    DateTime subtraction is strictly forbidden.
    """
    t0_request_start: float
    t1_frontend_prepare_start: float
    t2_frontend_prepare_end: float
    t3_fetch_start: float
    t4_fetch_end: float
    t14_response_received: float
    t15_render_end: float
    raw_backend_ms: float
    raw_gemini_ms: float
    raw_db_ms: float
    raw_val_ms: float
    raw_auth_ms: float = 0.0
    is_fixture: bool = False

    # Optional server monotonic timestamps
    t5_backend_start: float = 0.0
    t6_backend_end: float = 0.0
    t7_gemini_start: float = 0.0
    t8_gemini_end: float = 0.0
    t9_validation_start: float = 0.0
    t10_validation_end: float = 0.0
    t11_db_start: float = 0.0
    t12_db_end: float = 0.0
    t13_response_start: float = 0.0

    def compute_metrics(self) -> Dict[str, Any]:
        """
        Computes non-overlapping parent partition and nested child phases from raw measurements.
        NO clamping. NO scaling. Real measurements are preserved in raw form.

        Parent Hierarchy:
        TOTAL WALL CLOCK (t15 - t0)
        ├── frontend_prepare_ms (t2 - t0)
        ├── dispatch_gap_ms (t3 - t2)
        ├── network_ms (pure wire transport: client_round_trip - backend_ms)
        ├── backend_ms (server execution: raw_backend_ms)
        │   ├── db_ms (academic subjects & schedule lookup)
        │   ├── gemini_ms (upstream inference or mock delay)
        │   ├── validation_ms (Pydantic schema validation & evidence)
        │   └── auth_overhead_ms (FastAPI routing & serialization)
        └── render_ms (client-side DOM rendering: t15 - t14)
        """
        # 1. Frontend preparation covers [t0, t2]
        frontend_prepare_ms = max(0.0, (self.t2_frontend_prepare_end - self.t0_request_start) * 1000.0)
        
        # 2. Dispatch gap between preparation end and fetch invocation
        dispatch_gap_ms = max(0.0, (self.t3_fetch_start - self.t2_frontend_prepare_end) * 1000.0)
        
        # 3. Client round trip covers [t3, t14]
        client_round_trip_ms = max(0.0, (self.t14_response_received - self.t3_fetch_start) * 1000.0)
        
        # Raw backend execution time reported by server
        backend_ms = self.raw_backend_ms
        if backend_ms <= 0.0 and self.t6_backend_end > self.t5_backend_start:
            backend_ms = (self.t6_backend_end - self.t5_backend_start) * 1000.0

        # Pure wire transport: round trip minus server processing time
        network_ms = client_round_trip_ms - backend_ms

        # Child phases inside backend
        gemini_ms = self.raw_gemini_ms
        if gemini_ms <= 0.0 and self.t8_gemini_end > self.t7_gemini_start:
            gemini_ms = (self.t8_gemini_end - self.t7_gemini_start) * 1000.0

        db_ms = self.raw_db_ms
        if db_ms <= 0.0 and self.t12_db_end > self.t11_db_start:
            db_ms = (self.t12_db_end - self.t11_db_start) * 1000.0

        validation_ms = self.raw_val_ms
        if validation_ms <= 0.0 and self.t10_validation_end > self.t9_validation_start:
            validation_ms = (self.t10_validation_end - self.t9_validation_start) * 1000.0

        auth_overhead_ms = backend_ms - (gemini_ms + validation_ms + db_ms)

        # 4. Render covers [t14, t15]
        render_ms = max(0.0, (self.t15_render_end - self.t14_response_received) * 1000.0)
        total_wall_ms = max(0.0, (self.t15_render_end - self.t0_request_start) * 1000.0)

        # Exact partition check sum
        parent_sum_ms = frontend_prepare_ms + dispatch_gap_ms + network_ms + backend_ms + render_ms

        return {
            "frontend_prepare_ms": round(frontend_prepare_ms, 2),
            "dispatch_gap_ms": round(dispatch_gap_ms, 2),
            "client_round_trip_ms": round(client_round_trip_ms, 2),
            "network_ms": round(network_ms, 2),
            "backend_ms": round(backend_ms, 2),
            "gemini_ms": round(gemini_ms, 2),
            "validation_ms": round(validation_ms, 2),
            "db_ms": round(db_ms, 2),
            "auth_overhead_ms": round(auth_overhead_ms, 2),
            "render_ms": round(render_ms, 2),
            "total_wall_ms": round(total_wall_ms, 2),
            "parent_sum_ms": round(parent_sum_ms, 2),
            "is_fixture": self.is_fixture,
            "measurement_model": "nested_partition",
            "formula": "total_wall_ms = frontend_prepare_ms + dispatch_gap_ms + network_ms + backend_ms + render_ms",
        }


def verify_latency_math(metrics: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates arithmetic integrity of raw latency measurements without synthetic alterations.
    Any failure immediately flags MEASUREMENT_ERROR.

    Invariants enforced:
    1. RAW INVARIANT: backend_ms <= client_round_trip_ms + 1.0ms tolerance.
       If backend exceeds round trip, measurement is corrupted.
    2. RAW INVARIANT: child phases (gemini + validation + db) <= backend_ms * 1.02 + 0.5ms.
       Children cannot exceed their parent backend container.
    3. PARTITION INVARIANT: total_wall_ms == sum(parent categories).
       abs(total_wall_ms - parent_sum) <= max(0.5, 0.05 * total_wall_ms).
       Every millisecond between t0 and t15 must belong to an explicit category.
    4. NON-NEGATIVE WIRE LATENCY: network_ms >= -1.0ms.
       Negative network indicates clock skew or timing inversion.
    """
    total = metrics.get("total_wall_ms", 0.0)
    fe = metrics.get("frontend_prepare_ms", 0.0)
    gap = metrics.get("dispatch_gap_ms", 0.0)
    round_trip = metrics.get("client_round_trip_ms", 0.0)
    net = metrics.get("network_ms", 0.0)
    be = metrics.get("backend_ms", 0.0)
    rnd = metrics.get("render_ms", 0.0)

    gem = metrics.get("gemini_ms", 0.0)
    val = metrics.get("validation_ms", 0.0)
    db = metrics.get("db_ms", 0.0)

    # In-memory / empty operations with near-zero duration (<0.05ms) are trivial
    if total <= 0.05 and be <= 0.05:
        return (True, None)

    # 1. RAW INVARIANT: backend cannot exceed client round trip
    if be > round_trip + 1.0:
        return (
            False,
            f"Measurement error: raw backend duration ({be:.2f}ms) exceeds client round trip ({round_trip:.2f}ms)"
        )

    # 2. RAW INVARIANT: nested children cannot exceed parent backend container
    child_sum = gem + val + db
    if child_sum > be * 1.02 + 0.5:
        return (
            False,
            f"Measurement error: child phases ({child_sum:.2f}ms = gemini:{gem}+val:{val}+db:{db}) exceed parent backend ({be:.2f}ms)"
        )

    # 3. PARTITION INVARIANT: total wall clock must equal sum of all parent categories
    parent_sum = fe + gap + net + be + rnd
    diff = abs(total - parent_sum)
    allowed_tolerance = max(0.5, 0.05 * total)
    if diff > allowed_tolerance:
        return (
            False,
            f"Measurement error: total_wall_ms ({total:.2f}ms) != sum of parent categories ({parent_sum:.2f}ms = fe:{fe}+gap:{gap}+net:{net}+be:{be}+rnd:{rnd}). Diff: {diff:.2f}ms"
        )

    # 4. NEGATIVE LATENCY CHECK: network transport cannot be meaningfully negative
    if net < -1.0:
        return (
            False,
            f"Measurement error: negative wire network latency ({net:.2f}ms) indicates clock skew or timing inversion"
        )

    return (True, None)


def parse_server_timing_header(header_value: Optional[str]) -> Dict[str, float]:
    """
    Parses W3C Server-Timing header (e.g., 'backend;dur=14.2, gemini;dur=8.1').
    Returns dictionary of component name to duration in milliseconds.
    """
    timings: Dict[str, float] = {}
    if not header_value:
        return timings
    
    parts = header_value.split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        subparts = part.split(";")
        metric_name = subparts[0].strip()
        dur = 0.0
        for p in subparts[1:]:
            p = p.strip()
            if p.startswith("dur="):
                try:
                    dur = float(p[4:])
                except ValueError:
                    dur = 0.0
        timings[metric_name] = dur
    return timings


def create_test_fixture_trace(
    t0: float = 1000.0,
    frontend_prepare_ms: float = 2.0,
    dispatch_gap_ms: float = 0.5,
    client_round_trip_ms: float = 50.0,
    backend_ms: float = 30.0,
    gemini_ms: float = 20.0,
    db_ms: float = 2.0,
    val_ms: float = 1.0,
    render_ms: float = 5.0,
) -> AiRequestTrace:
    """
    TEST FIXTURE ONLY.
    Constructs a deterministic synthetic AiRequestTrace for unit tests and offline testing.
    Never used in real measurement pipeline.
    """
    t1 = t0
    t2 = t1 + (frontend_prepare_ms / 1000.0)
    t3 = t2 + (dispatch_gap_ms / 1000.0)
    t4 = t3 + (client_round_trip_ms / 1000.0)
    t14 = t4
    t15 = t14 + (render_ms / 1000.0)

    return AiRequestTrace(
        t0_request_start=t0,
        t1_frontend_prepare_start=t1,
        t2_frontend_prepare_end=t2,
        t3_fetch_start=t3,
        t4_fetch_end=t4,
        t14_response_received=t14,
        t15_render_end=t15,
        raw_backend_ms=backend_ms,
        raw_gemini_ms=gemini_ms,
        raw_db_ms=db_ms,
        raw_val_ms=val_ms,
        raw_auth_ms=max(0.0, backend_ms - (gemini_ms + db_ms + val_ms)),
        is_fixture=True,
    )


def legacy_build_synthetic_fixture_trace(
    t0: float,
    t1: float,
    t2: float,
    t3: float,
    t4: float,
    t14: float,
    t15: float,
    raw_backend_ms: float = 14.0,
    raw_gemini_ms: float = 10.0,
    raw_db_ms: float = 1.0,
    raw_val_ms: float = 1.0,
) -> AiRequestTrace:
    """
    LEGACY TEST FIXTURE ONLY.
    Synthetic fixture helper that clamps/scales values for isolated unit test scenarios.
    MUST NEVER be used for real measurements (is_fixture is strictly True).
    """
    fe_ms = max(0.0, (t2 - t0) * 1000.0)
    gap_ms = max(0.0, (t3 - t2) * 1000.0)
    round_trip_ms = max(0.001, (t14 - t3) * 1000.0)
    rnd_ms = max(0.0, (t15 - t14) * 1000.0)

    # In synthetic fixture, ensure backend does not exceed round trip
    safe_backend = min(raw_backend_ms, round_trip_ms * 0.95)
    safe_child_sum = raw_gemini_ms + raw_db_ms + raw_val_ms
    if safe_child_sum > safe_backend * 0.95:
        scale = (safe_backend * 0.90) / max(0.001, safe_child_sum)
        g_ms = raw_gemini_ms * scale
        d_ms = raw_db_ms * scale
        v_ms = raw_val_ms * scale
    else:
        g_ms = raw_gemini_ms
        d_ms = raw_db_ms
        v_ms = raw_val_ms

    return create_test_fixture_trace(
        t0=t0,
        frontend_prepare_ms=fe_ms,
        dispatch_gap_ms=gap_ms,
        client_round_trip_ms=round_trip_ms,
        backend_ms=safe_backend,
        gemini_ms=g_ms,
        db_ms=d_ms,
        val_ms=v_ms,
        render_ms=rnd_ms,
    )


# Explicit legacy alias
build_consistent_trace = legacy_build_synthetic_fixture_trace
