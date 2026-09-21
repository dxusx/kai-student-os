"""
Regression and Integrity Tests for AI Latency Instrumentation.
Proves the nested timing model, non-overlapping parent phase arithmetic,
child-phase nesting constraints, and strict absence of double-counting.
"""

import time
import pytest
from tests.qa.ai_latency_tracer import (
    AiRequestTrace,
    build_consistent_trace,
    parse_server_timing_header,
    verify_latency_math,
)


def test_nested_timing_model_arithmetic_consistency():
    """
    Validates that a realistic trace satisfies the nested timing formula:
    total_wall_ms = frontend_prepare_ms + network_ms + backend_ms + render_ms
    where network_ms = round_trip_ms - backend_ms.
    """
    t0 = 1000.000000
    t1 = t0
    t2 = t0 + 0.001200  # frontend prepare: 1.2ms
    t3 = t2             # fetch start
    t5 = t3 + 0.001000  # backend start (1.0ms network wire out)
    t11 = t5 + 0.000500 # db start
    t12 = t11 + 0.002000 # db end (2.0ms db)
    t7 = t12 + 0.000100 # gemini start
    t8 = t7 + 0.015000  # gemini end (15.0ms gemini)
    t9 = t8 + 0.000200  # val start
    t10 = t9 + 0.001500 # val end (1.5ms val)
    t6 = t10 + 0.000500 # backend end (total backend: 19.8ms)
    t13 = t6            # response start
    t4 = t6 + 0.001000  # fetch end (1.0ms network wire in)
    t14 = t4            # response received
    t15 = t14 + 0.001500 # render end (1.5ms render)

    trace = AiRequestTrace(
        t0_request_start=t0,
        t1_frontend_prepare_start=t1,
        t2_frontend_prepare_end=t2,
        t3_fetch_start=t3,
        t4_fetch_end=t4,
        t5_backend_start=t5,
        t6_backend_end=t6,
        t7_gemini_start=t7,
        t8_gemini_end=t8,
        t9_validation_start=t9,
        t10_validation_end=t10,
        t11_db_start=t11,
        t12_db_end=t12,
        t13_response_start=t13,
        t14_response_received=t14,
        t15_render_end=t15,
    )

    metrics = trace.compute_metrics()

    # 1. Non-overlapping parent sum equals total wall clock
    parent_sum = (
        metrics["frontend_prepare_ms"]
        + metrics["network_ms"]
        + metrics["backend_ms"]
        + metrics["render_ms"]
    )
    diff = abs(metrics["total_wall_ms"] - parent_sum)
    assert diff <= 0.05 * metrics["total_wall_ms"] + 0.1, f"Parent sum mismatch: {parent_sum} != {metrics['total_wall_ms']}"

    # 2. Child phases must not exceed parent backend
    child_sum = metrics["gemini_ms"] + metrics["validation_ms"] + metrics["db_ms"]
    assert child_sum <= metrics["backend_ms"] * 1.05 + 0.1, f"Children ({child_sum}) exceed backend ({metrics['backend_ms']})"

    # 3. CRITICAL ASSERTION: Total is NOT double-counting (network + backend)
    double_counted = 2 * (metrics["network_ms"] + metrics["backend_ms"])
    assert metrics["total_wall_ms"] != pytest.approx(double_counted, rel=0.1), (
        f"Double-counting defect: total {metrics['total_wall_ms']} equals 2*(net+backend) {double_counted}"
    )

    # 4. Mathematical integrity checker returns valid
    is_valid, err = verify_latency_math(metrics)
    assert is_valid is True, f"Integrity check failed unexpectedly: {err}"


def test_reproduce_and_reject_legacy_double_counting():
    """
    Specifically reproduces the legacy bug where total was ~12606ms while sum of phases was ~6339ms.
    Proves that verify_latency_math catches this defect and rejects it as invalid.
    """
    legacy_buggy_metrics = {
        "frontend_prepare_ms": 3.0,
        "network_ms": 3781.8,
        "backend_ms": 2521.2,
        "gemini_ms": 15.0,
        "validation_ms": 1.5,
        "db_ms": 2.0,
        "render_ms": 15.0,
        "total_wall_ms": 12606.0,  # ~2x the sum of parent phases!
    }

    is_valid, err = verify_latency_math(legacy_buggy_metrics)
    assert is_valid is False
    assert "Arithmetic inconsistency" in err or "total_wall_ms" in err


def test_reject_nested_hierarchy_violation():
    """
    Proves that verify_latency_math rejects records where child phases exceed parent backend time.
    """
    corrupted_metrics = {
        "frontend_prepare_ms": 1.0,
        "network_ms": 2.0,
        "backend_ms": 10.0,
        "gemini_ms": 15.0,  # 15ms inside a 10ms backend!
        "validation_ms": 2.0,
        "db_ms": 2.0,
        "render_ms": 1.0,
        "total_wall_ms": 14.0,
    }

    is_valid, err = verify_latency_math(corrupted_metrics)
    assert is_valid is False
    assert "Nested hierarchy violation" in err


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
    assert (t1 - t0) * 1000 >= 0.5  # at least ~0.5ms elapsed


def test_build_consistent_trace_arithmetic():
    """
    Verifies that build_consistent_trace creates an AiRequestTrace that strictly satisfies
    all invariants, even when server timings exceed client round-trip or raw child phases
    are larger than backend time.
    """
    t0 = 200.0
    t1 = 200.0
    t2 = 200.005  # 5ms prepare
    t3 = 200.005  # fetch start
    t4 = 200.025  # 20ms round trip
    t14 = t4
    t15 = 200.030 # 5ms render

    # Intentionally pass oversized server timings: 50ms backend inside a 20ms round-trip,
    # and 40ms gemini + 20ms db inside backend
    trace = build_consistent_trace(
        t0=t0,
        t1=t1,
        t2=t2,
        t3=t3,
        t4=t4,
        t14=t14,
        t15=t15,
        raw_backend_ms=50.0,
        raw_gemini_ms=40.0,
        raw_db_ms=20.0,
        raw_val_ms=10.0,
    )
    metrics = trace.compute_metrics()
    is_valid, err = verify_latency_math(metrics)
    assert is_valid is True, f"Consistent trace validation failed: {err}"
    assert metrics["backend_ms"] <= 20.0
    assert metrics["gemini_ms"] + metrics["db_ms"] + metrics["validation_ms"] <= metrics["backend_ms"]

