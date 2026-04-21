"""
Tests for Evaluation Metrics
"""

import pytest
import time

from openclaw_swarm.evaluation import (
    MetricType,
    MetricResult,
    EvaluationResult,
    Evaluator,
    Benchmark,
    create_performance_benchmark,
    create_quality_benchmark,
    create_cost_benchmark,
)


class TestMetricType:
    """Test MetricType enum"""

    def test_metric_types_exist(self):
        """Test all metric types exist"""
        assert MetricType.ACCURACY.value == "accuracy"
        assert MetricType.LATENCY.value == "latency"
        assert MetricType.THROUGHPUT.value == "throughput"
        assert MetricType.QUALITY.value == "quality"
        assert MetricType.COST.value == "cost"
        assert MetricType.CUSTOM.value == "custom"


class TestMetricResult:
    """Test MetricResult dataclass"""

    def test_metric_result_creation(self):
        """Test creating a metric result"""
        metric = MetricResult(name="response_time", value=100.5, unit="ms")

        assert metric.name == "response_time"
        assert metric.value == 100.5
        assert metric.unit == "ms"
        assert metric.timestamp is not None

    def test_metric_result_with_metadata(self):
        """Test metric result with metadata"""
        metric = MetricResult(
            name="accuracy",
            value=95.5,
            unit="percentage",
            metadata={"correct": 95, "total": 100},
        )

        assert metric.metadata["correct"] == 95

    def test_metric_result_to_dict(self):
        """Test converting metric result to dict"""
        metric = MetricResult(name="test", value=42.0, unit="units")

        result = metric.to_dict()

        assert result["name"] == "test"
        assert result["value"] == 42.0
        assert result["unit"] == "units"


class TestEvaluationResult:
    """Test EvaluationResult dataclass"""

    def test_evaluation_result_creation(self):
        """Test creating an evaluation result"""
        result = EvaluationResult(name="test_evaluation")

        assert result.name == "test_evaluation"
        assert len(result.metrics) == 0
        assert result.success is True

    def test_add_metric(self):
        """Test adding a metric"""
        result = EvaluationResult(name="test")
        metric = MetricResult(name="time", value=100, unit="ms")

        result.add_metric(metric)

        assert len(result.metrics) == 1
        assert result.metrics[0].name == "time"

    def test_get_metric(self):
        """Test getting a metric by name"""
        result = EvaluationResult(name="test")
        result.add_metric(MetricResult(name="time", value=100, unit="ms"))
        result.add_metric(MetricResult(name="accuracy", value=95, unit="%"))

        time_metric = result.get_metric("time")

        assert time_metric is not None
        assert time_metric.value == 100

    def test_evaluation_result_to_dict(self):
        """Test converting evaluation result to dict"""
        result = EvaluationResult(name="test")
        result.add_metric(MetricResult(name="time", value=100, unit="ms"))

        data = result.to_dict()

        assert data["name"] == "test"
        assert len(data["metrics"]) == 1


class TestEvaluator:
    """Test Evaluator class"""

    def test_evaluator_initialization(self):
        """Test evaluator initialization"""
        evaluator = Evaluator()

        assert evaluator.name == "default"
        assert len(evaluator.metrics) > 0  # Default metrics
        assert len(evaluator.evaluations) == 0

    def test_evaluator_with_name(self):
        """Test evaluator with custom name"""
        evaluator = Evaluator(name="custom")

        assert evaluator.name == "custom"

    def test_register_metric(self):
        """Test registering a metric"""
        evaluator = Evaluator()

        def custom_metric(func, *args, **kwargs):
            return MetricResult(name="custom", value=42, unit="units")

        evaluator.register_metric("custom", custom_metric)

        assert "custom" in evaluator.metrics

    def test_evaluate_function(self):
        """Test evaluating a function"""
        evaluator = Evaluator()

        def test_func(x):
            return x * 2

        result = evaluator.evaluate(
            name="test_eval", func=test_func, args=(5,), metrics=["response_time"]
        )

        assert result.success is True
        assert len(result.metrics) >= 1

    def test_evaluate_with_failure(self):
        """Test evaluating a function that fails"""
        evaluator = Evaluator()

        def failing_func(x):
            raise ValueError("Test error")

        result = evaluator.evaluate(name="failing_eval", func=failing_func, args=(5,))

        assert result.success is False
        assert "Test error" in result.error

    def test_get_statistics(self):
        """Test getting statistics"""
        evaluator = Evaluator()

        def test_func(x):
            return x

        # Run multiple evaluations
        for i in range(5):
            evaluator.evaluate(name=f"test_{i}", func=test_func, args=(i,))

        stats = evaluator.get_statistics("response_time")

        assert "count" in stats
        assert stats["count"] == 5

    def test_get_summary(self):
        """Test getting summary"""
        evaluator = Evaluator()

        def test_func(x):
            return x

        evaluator.evaluate(name="test", func=test_func, args=(1,))

        summary = evaluator.get_summary()

        assert summary["total_evaluations"] == 1
        assert summary["successful"] == 1

    def test_clear_evaluations(self):
        """Test clearing evaluations"""
        evaluator = Evaluator()

        def test_func(x):
            return x

        evaluator.evaluate(name="test", func=test_func, args=(1,))
        evaluator.evaluate(name="test", func=test_func, args=(2,))

        assert len(evaluator.evaluations) == 2

        evaluator.clear_evaluations()

        assert len(evaluator.evaluations) == 0


class TestBenchmark:
    """Test Benchmark class"""

    def test_benchmark_initialization(self):
        """Test benchmark initialization"""
        benchmark = Benchmark()

        assert benchmark.name == "default"
        assert len(benchmark.benchmarks) == 0
        assert benchmark.baseline is None

    def test_benchmark_with_name(self):
        """Test benchmark with custom name"""
        benchmark = Benchmark(name="performance")

        assert benchmark.name == "performance"

    def test_add_benchmark(self):
        """Test adding a benchmark result"""
        benchmark = Benchmark()
        result = EvaluationResult(name="test")

        benchmark.add_benchmark("test_benchmark", result)

        assert "test_benchmark" in benchmark.benchmarks
        assert len(benchmark.benchmarks["test_benchmark"]) == 1

    def test_set_baseline(self):
        """Test setting baseline"""
        benchmark = Benchmark()
        result = EvaluationResult(name="baseline")

        benchmark.set_baseline(result)

        assert benchmark.baseline is not None
        assert benchmark.baseline.name == "baseline"

    def test_compare_to_baseline(self):
        """Test comparing to baseline"""
        benchmark = Benchmark()

        baseline = EvaluationResult(name="baseline")
        baseline.add_metric(MetricResult(name="time", value=100, unit="ms"))
        benchmark.set_baseline(baseline)

        result = EvaluationResult(name="test")
        result.add_metric(MetricResult(name="time", value=80, unit="ms"))

        comparison = benchmark.compare_to_baseline(result)

        assert comparison["duration_diff_ms"] < 0  # Faster
        assert "metrics" in comparison

    def test_compare_to_baseline_no_baseline(self):
        """Test comparing without baseline"""
        benchmark = Benchmark()
        result = EvaluationResult(name="test")

        comparison = benchmark.compare_to_baseline(result)

        assert "error" in comparison

    def test_get_rankings(self):
        """Test getting rankings"""
        benchmark = Benchmark()

        # Add multiple results
        for i, value in enumerate([100, 80, 120, 90]):
            result = EvaluationResult(name=f"test_{i}")
            result.add_metric(MetricResult(name="time", value=value, unit="ms"))
            benchmark.add_benchmark("test", result)

        rankings = benchmark.get_rankings("time", ascending=True)

        assert len(rankings) == 4
        assert rankings[0]["value"] == 80  # Best (lowest)

    def test_get_best(self):
        """Test getting best result"""
        benchmark = Benchmark()

        for value in [100, 80, 120]:
            result = EvaluationResult(name=f"test_{value}")
            result.add_metric(MetricResult(name="time", value=value, unit="ms"))
            benchmark.add_benchmark("test", result)

        best = benchmark.get_best("time")

        assert best is not None
        assert best["value"] == 80  # Lowest time is best

    def test_get_worst(self):
        """Test getting worst result"""
        benchmark = Benchmark()

        for value in [100, 80, 120]:
            result = EvaluationResult(name=f"test_{value}")
            result.add_metric(MetricResult(name="time", value=value, unit="ms"))
            benchmark.add_benchmark("test", result)

        worst = benchmark.get_worst("time")

        assert worst is not None
        assert worst["value"] == 120  # Highest time is worst

    def test_export_results(self):
        """Test exporting results"""
        benchmark = Benchmark(name="test")
        result = EvaluationResult(name="test_result")
        benchmark.add_benchmark("test", result)

        exported = benchmark.export_results()

        assert "test" in exported
        assert "name" in exported

    def test_import_results(self):
        """Test importing results"""
        benchmark = Benchmark()

        # Create and export
        result1 = EvaluationResult(name="result1")
        benchmark.add_benchmark("test", result1)
        exported = benchmark.export_results()

        # Import into new benchmark
        benchmark2 = Benchmark()
        benchmark2.import_results(exported)

        assert "test" in benchmark2.benchmarks


class TestBenchmarkFactories:
    """Test benchmark factory functions"""

    def test_create_performance_benchmark(self):
        """Test creating performance benchmark"""
        benchmark = create_performance_benchmark()

        assert benchmark.name == "performance"

    def test_create_quality_benchmark(self):
        """Test creating quality benchmark"""
        benchmark = create_quality_benchmark()

        assert benchmark.name == "quality"

    def test_create_cost_benchmark(self):
        """Test creating cost benchmark"""
        benchmark = create_cost_benchmark()

        assert benchmark.name == "cost"
