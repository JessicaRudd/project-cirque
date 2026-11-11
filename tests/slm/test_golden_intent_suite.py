"""Golden Intent Test Suite & SLM Benchmark Evaluation for Project Cirque.

Tests:
1. Loads ground truth benchmark test cases from tests/slm/fixtures/golden_intent_test_cases.json.
2. Parameterizes evaluation through GemmaIntentParser across all golden inputs.
3. Asserts 100% field-by-field accuracy matching the expected SkiIntent specification.
4. Benchmarks execution latency (wall clock time in milliseconds) per case and verifies < 5ms mock budget.
5. Computes precision, recall, exact match ratio, and exports benchmark telemetry to .cirque/devlog/M2_LOCAL_SLM/step_2_2_benchmark.json.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import pytest

from slm.gemma_intent_parser import GemmaIntentParser, SkiIntent

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = REPO_ROOT / "tests" / "slm" / "fixtures" / "golden_intent_test_cases.json"
DEFAULT_BENCHMARK_REPORT_PATH = REPO_ROOT / ".cirque" / "devlog" / "M2_LOCAL_SLM" / "step_2_2_benchmark.json"


def load_golden_cases() -> List[Dict[str, Any]]:
    """Loads benchmark test cases from the golden fixture file."""
    assert FIXTURE_PATH.exists(), f"Missing fixture at {FIXTURE_PATH}"
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)
    assert len(cases) >= 8, f"Expected at least 8 test cases, found {len(cases)}"
    return cases


GOLDEN_CASES = load_golden_cases()


@pytest.fixture(scope="module")
def parser() -> GemmaIntentParser:
    return GemmaIntentParser(mode="mock")


@pytest.mark.parametrize("case", GOLDEN_CASES, ids=lambda c: c["test_id"])
def test_golden_intent_case_accuracy(parser: GemmaIntentParser, case: Dict[str, Any]):
    """Tests each golden intent case for exact field parity and < 5ms mock latency."""
    transcript = case["input"]
    expected = case["expected"]

    start_time = time.perf_counter()
    intent: SkiIntent = parser.process_transcript(transcript)
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    assert elapsed_ms < 5.0, f"Execution too slow: {elapsed_ms:.2f}ms >= 5.0ms"

    for key, expected_value in expected.items():
        actual_value = getattr(intent, key)
        assert actual_value == expected_value, (
            f"Field mismatch in [{case['test_id']}] for '{key}': "
            f"expected={expected_value!r}, actual={actual_value!r}"
        )


def compile_benchmark_report(
    parser: GemmaIntentParser,
    output_path: Optional[Path] = DEFAULT_BENCHMARK_REPORT_PATH,
) -> Dict[str, Any]:
    """Executes all golden cases, aggregates accuracy and p95 latency, and optionally writes JSON."""
    cases = load_golden_cases()
    results = []
    latencies_ms: List[float] = []
    field_failures: Dict[str, int] = {}
    total_fields_evaluated = 0
    total_fields_matched = 0

    for case in cases:
        t0 = time.perf_counter()
        intent = parser.process_transcript(case["input"])
        duration_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(duration_ms)

        expected = case["expected"]
        case_passed = True
        case_mismatches = {}

        for field, exp_val in expected.items():
            total_fields_evaluated += 1
            act_val = getattr(intent, field)
            if act_val == exp_val:
                total_fields_matched += 1
            else:
                case_passed = False
                case_mismatches[field] = {"expected": exp_val, "actual": act_val}
                field_failures[field] = field_failures.get(field, 0) + 1

        results.append({
            "test_id": case["test_id"],
            "name": case["name"],
            "input": case["input"],
            "passed": case_passed,
            "latency_ms": round(duration_ms, 3),
            "mismatches": case_mismatches,
        })

    passed_count = sum(1 for r in results if r["passed"])
    exact_match_ratio = passed_count / len(cases)
    field_accuracy = total_fields_matched / total_fields_evaluated if total_fields_evaluated else 0.0
    avg_latency_ms = sum(latencies_ms) / len(latencies_ms)
    sorted_latencies = sorted(latencies_ms)
    p95_idx = min(len(sorted_latencies) - 1, max(0, math.ceil(len(sorted_latencies) * 0.95) - 1))
    p95_latency_ms = sorted_latencies[p95_idx]

    benchmark_report = {
        "step_id": "STEP_2_2",
        "milestone_id": "M2_LOCAL_SLM",
        "title": "Golden Intent Test Suite & Benchmark Evaluation",
        "status": "PASSED" if exact_match_ratio == 1.0 else "FAILED",
        "benchmark_summary": {
            "total_test_cases": len(cases),
            "passed_cases": passed_count,
            "failed_cases": len(cases) - passed_count,
            "exact_match_ratio": round(exact_match_ratio, 4),
            "field_level_accuracy": round(field_accuracy, 4),
            "total_fields_evaluated": total_fields_evaluated,
            "field_failures_breakdown": field_failures,
        },
        "latency_metrics": {
            "mock_avg_latency_ms": round(avg_latency_ms, 3),
            "mock_p95_latency_ms": round(p95_latency_ms, 3),
            "simulated_edge_slm_budget_ms": 450.0,
            "target_sla_met": avg_latency_ms < 5.0,
        },
        "test_cases": results,
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(benchmark_report, f, indent=2)

    return benchmark_report


def test_compile_and_export_benchmark_report(parser: GemmaIntentParser, tmp_path: Path):
    """Exports the benchmark report into tmp_path without mutating tracked repository files."""
    out_file = tmp_path / "step_2_2_benchmark.json"
    report = compile_benchmark_report(parser, output_path=out_file)
    assert report["benchmark_summary"]["exact_match_ratio"] == 1.0
    assert out_file.exists(), "Benchmark report must be exported"


if __name__ == "__main__":
    compile_benchmark_report(GemmaIntentParser(mode="mock"), DEFAULT_BENCHMARK_REPORT_PATH)
