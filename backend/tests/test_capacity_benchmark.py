import pytest
from scripts.benchmark_multi_source import supported_source_count


def test_supported_source_count_uses_largest_passing_scenario() -> None:
    results = [
        {"source_count": 1, "minimum_source_fps": 8.2},
        {"source_count": 2, "minimum_source_fps": 4.1},
        {"source_count": 3, "minimum_source_fps": 2.7},
    ]

    assert supported_source_count(results, 5.0) == 1


def test_supported_source_count_can_report_no_passing_scenario() -> None:
    assert supported_source_count([{"source_count": 1, "minimum_source_fps": 3.0}], 5.0) == 0


@pytest.mark.parametrize("target", [5.0, 10.0])
def test_supported_source_count_is_independent_of_result_order(target) -> None:
    results = [
        {"source_count": 2, "minimum_source_fps": target},
        {"source_count": 1, "minimum_source_fps": target + 1},
    ]

    assert supported_source_count(results, target) == 2
