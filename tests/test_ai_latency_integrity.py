"""
Regression and Integrity Tests for AI Latency Instrumentation.
Proves the nested partition timing model, raw measurement integrity without clamping,
child-phase nesting constraints, exact boundary gap accounting, and rejection of invalid traces.
"""

import time
import pytest
from tests.qa.ai_latency_tracer import (
    AiRequestTrace,
    create_test_fixture_trace,
    build_consistent_trace,
    parse_server_timing_header,
    verify_latency_math,
)


def test_valid_real_trace():
    """
    Validates that a real measurement trace with raw timings satisfies all invariants:
    total_wall_ms = frontend_prepare_ms + dispatch_gap_ms + network_ms + backend_ms + render_ms
    where network_ms = client_round_trip_ms - backend_ms.
    """
    t0 = 1000.000000
    t1 = t0
    t2 = t0 + 0.002000     # frontend prepare: 2.0ms
    t3 = t2 + 0.000200     # dispatch gap: 0.2ms
    t4 = t3 + 0.050000     # client round trip: 50.0ms
    t14 = t4               # response received
    t15 = t14 + 0.003000   # render: 3.0ms (total wall: 55.2ms)

    raw_backend = 32.0     # server backend execution: 32.0ms
    raw_gemini = 15.0      # gemini inference: 15.0ms
    raw_db = 2.5           # db query: 2.5ms
    raw_val = 1.0          # validation: 1.0ms

    trace = AiRequestTrace(
        t0_request_start=t0,
        t1_frontend_prepare_start=t1,
        t2_frontend_prepare_end=t2,
        t3_fetch_start=t3,
        t4_fetch_end=t4,
        t14_response_received=t14,
        t15_render_end=t15,
        raw_backend_ms=raw_backend,
        raw_gemini_ms=raw_gemini,
        raw_db_ms=raw_db,
        raw_val_ms=raw_val,
        raw_auth_ms=raw_backend - (raw_gemini + raw_db + raw_val),
        is_fixture=False,
    )

    metrics = trace.compute_metrics()

    # 1. Exact partition check
    assert metrics["frontend_prepare_ms"] == 2.0
    assert metrics["dispatch_gap_ms"] == 0.2
    assert metrics["client_round_trip_ms"] == 50.0
    assert metrics["backend_ms"] == 32.0
    assert metrics["network_ms"] == 18.0  # pure wire transport = 50.0 - 32.0
    assert metrics["render_ms"] == 3.0
    assert metrics["total_wall_ms"] == 55.2
    assert metrics["parent_sum_ms"] == 55.2
    assert metrics["is_fixture"] is False

    # 2. Mathematical integrity verification passes
    is_valid, err = verify_latency_math(metrics)
    assert is_valid is True, f"Integrity check failed: {err}"


def test_invalid_raw_backend_timing_fails_with_measurement_error():
    """
    CRITICAL INVARIANT:
    If a real trace reports backend duration exceeding the entire client round trip,
    it MUST NOT be synthetically clamped or hidden. It MUST trigger MEASUREMENT_ERROR.
    """
    t0 = 100.0
    t1 = t0
    t2 = t0 + 0.001        # prepare: 1.0ms
    t3 = t2                # fetch start
    t4 = t3 + 0.020        # client round trip: 20.0ms
    t14 = t4
    t15 = t14 + 0.001      # render: 1.0ms

    # Invalid raw measurement: server claims 45.0ms inside a 20.0ms round trip!
    corrupted_trace = AiRequestTrace(
        t0_request_start=t0,
        t1_frontend_prepare_start=t1,
        t2_frontend_prepare_end=t2,
        t3_fetch_start=t3,
        t4_fetch_end=t4,
        t14_response_received=t14,
        t15_render_end=t15,
        raw_backend_ms=45.0,  # > 20.0ms round trip!
        raw_gemini_ms=10.0,
        raw_db_ms=1.0,
        raw_val_ms=1.0,
        is_fixture=False,
    )

    metrics = corrupted_trace.compute_metrics()
    is_valid, err = verify_latency_math(metrics)
    assert is_valid is False, "Corrupted raw backend timing should have failed!"
    assert "exceeds client round trip" in err or "Measurement error" in err


def test_invalid_child_timing_fails_with_measurement_error():
    """
    CRITICAL INVARIANT:
    If child phases (gemini + db + val) exceed parent backend duration,
    it MUST NOT be scaled down. It MUST trigger MEASUREMENT_ERROR.
    """
    t0 = 100.0
    t1 = t0
    t2 = t0 + 0.001
    t3 = t2
    t4 = t3 + 0.050        # round trip: 50.0ms
    t14 = t4
    t15 = t14 + 0.001

    # Invalid raw measurement: backend is 20ms, but children sum to 35ms!
    corrupted_trace = AiRequestTrace(
        t0_request_start=t0,
        t1_frontend_prepare_start=t1,
        t2_frontend_prepare_end=t2,
        t3_fetch_start=t3,
        t4_fetch_end=t4,
        t14_response_received=t14,
        t15_render_end=t15,
        raw_backend_ms=20.0,
        raw_gemini_ms=25.0,  # 25 + 5 + 5 = 35ms > 20ms backend!
        raw_db_ms=5.0,
        raw_val_ms=5.0,
        is_fixture=False,
    )

    metrics = corrupted_trace.compute_metrics()
    is_valid, err = verify_latency_math(metrics)
    assert is_valid is False, "Corrupted child timings should have failed!"
    assert "exceed parent backend" in err


def test_unaccounted_gap_fails_with_measurement_error():
    """
    CRITICAL INVARIANT:
    Every millisecond between t0 and t15 must belong to an explicit parent category.
    If there is an unaccounted gap (e.g. total != parent_sum), it MUST trigger MEASUREMENT_ERROR.
    """
    corrupted_metrics = {
        "frontend_prepare_ms": 1.0,
        "dispatch_gap_ms": 0.0,
        "client_round_trip_ms": 10.0,
        "network_ms": 5.0,
        "backend_ms": 5.0,
        "gemini_ms": 2.0,
        "validation_ms": 1.0,
        "db_ms": 1.0,
        "render_ms": 1.0,
        "total_wall_ms": 100.0,  # 100ms total, but phases only sum to 7ms! (93ms gap)
    }

    is_valid, err = verify_latency_math(corrupted_metrics)
    assert is_valid is False
    assert "total_wall_ms" in err or "Measurement error" in err


def test_legacy_double_counting_rejected_as_measurement_error():
    """
    Specifically reproduces the legacy defect where total was ~12606ms while sum of phases was ~6339ms.
    Proves that verify_latency_math rejects this as an arithmetic inconsistency / double counting.
    """
    legacy_buggy_metrics = {
        "frontend_prepare_ms": 3.0,
        "dispatch_gap_ms": 0.0,
        "client_round_trip_ms": 3781.8,
        "network_ms": 3781.8,
        "backend_ms": 2521.2,
        "gemini_ms": 15.0,
        "validation_ms": 1.5,
        "db_ms": 2.0,
        "render_ms": 15.0,
        "total_wall_ms": 12606.0,  # ~2x sum of phases!
    }

    is_valid, err = verify_latency_math(legacy_buggy_metrics)
    assert is_valid is False
    assert "total_wall_ms" in err or "Measurement error" in err


def test_valid_synthetic_fixture():
    """
    Verifies that create_test_fixture_trace creates a synthetic fixture trace
    explicitly flagged as is_fixture=True for testing and offline simulations.
    """
    trace = create_test_fixture_trace(
        t0=500.0,
        frontend_prepare_ms=3.0,
        dispatch_gap_ms=0.5,
        client_round_trip_ms=60.0,
        backend_ms=35.0,
        gemini_ms=20.0,
        db_ms=2.0,
        val_ms=1.0,
        render_ms=4.0,
    )
    metrics = trace.compute_metrics()
    assert metrics["is_fixture"] is True
    is_valid, err = verify_latency_math(metrics)
    assert is_valid is True, f"Fixture should be valid: {err}"
    assert metrics["total_wall_ms"] == metrics["parent_sum_ms"]


def test_server_timing_header_parser():
    """
    Verifies robust parsing of W3C Server-Timing headers.
    """
    header = "backend;dur=18.50, gemini;dur=12.25, db;dur=1.80, validation;dur=1.45, auth;dur=3.00"
    parsed = parse_server_timing_header(header)
    assert parsed["backend"] == 18.50
    assert parsed["gemini"] == 12.25
    assert parsed["db"] == 1.80
    assert parsed["validation"] == 1.45
    assert parsed["auth"] == 3.00


def test_monotonic_clock_ordering():
    """
    Verifies that real calls to time.perf_counter() produce strictly non-decreasing monotonic timestamps.
    """
    t0 = time.perf_counter()
    time.sleep(0.001)
    t1 = time.perf_counter()
    assert t1 > t0
    assert (t1 - t0) * 1000 >= 0.5
