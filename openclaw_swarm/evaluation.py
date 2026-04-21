"""
OpenClaw Swarm - Evaluation Metrics
Quality metrics and benchmarking for agent performance
"""

import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import statistics
import time


class MetricType(Enum):
    """Types of metrics"""

    ACCURACY = "accuracy"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    QUALITY = "quality"
    COST = "cost"
    CUSTOM = "custom"


@dataclass
class MetricResult:
    """Result of a metric evaluation"""

    name: str
    value: float
    unit: str
    timestamp: datetime = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class EvaluationResult:
    """Result of an evaluation run"""

    id: str
    name: str
    metrics: List[MetricResult] = field(default_factory=list)
    start_time: datetime = None
    end_time: datetime = None
    duration_ms: float = 0
    success: bool = True
    error: Optional[str] = None

    def __post_init__(self):
        if not self.id:
            self.id = f"eval_{int(time.time() * 1000)}"

    def add_metric(self, metric: MetricResult):
        """Add a metric result"""
        self.metrics.append(metric)

    def get_metric(self, name: str) -> Optional[MetricResult]:
        """Get a metric by name"""
        return next((m for m in self.metrics if m.name == name), None)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "metrics": [m.to_dict() for m in self.metrics],
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
        }


class Evaluator:
    """Evaluate agent performance with metrics"""

    def __init__(self, name: str = "default"):
        self.name = name
        self.metrics: Dict[str, Callable] = {}
        self.evaluations: List[EvaluationResult] = []
        self._register_default_metrics()

    def _register_default_metrics(self):
        """Register default metrics"""
        self.register_metric("response_time", self._measure_response_time)
        self.register_metric("accuracy", self._measure_accuracy)
        self.register_metric("throughput", self._measure_throughput)
        self.register_metric("quality_score", self._measure_quality_score)

    def register_metric(self, name: str, handler: Callable):
        """Register a metric handler"""
        self.metrics[name] = handler

    def _measure_response_time(self, func: Callable, *args, **kwargs) -> MetricResult:
        """Measure response time in milliseconds"""
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()

        duration_ms = (end - start) * 1000

        return MetricResult(
            name="response_time",
            value=duration_ms,
            unit="ms",
            metadata={"function": func.__name__},
        )

    def _measure_accuracy(self, predictions: List, ground_truth: List) -> MetricResult:
        """Measure accuracy"""
        if len(predictions) != len(ground_truth):
            return MetricResult(
                name="accuracy",
                value=0.0,
                unit="percentage",
                metadata={"error": "Length mismatch"},
            )

        correct = sum(1 for p, g in zip(predictions, ground_truth) if p == g)
        accuracy = (correct / len(predictions)) * 100

        return MetricResult(
            name="accuracy",
            value=accuracy,
            unit="percentage",
            metadata={"correct": correct, "total": len(predictions)},
        )

    def _measure_throughput(
        self, operations: int, duration_seconds: float
    ) -> MetricResult:
        """Measure throughput (operations per second)"""
        throughput = operations / duration_seconds if duration_seconds > 0 else 0

        return MetricResult(
            name="throughput",
            value=throughput,
            unit="ops/s",
            metadata={"operations": operations, "duration_s": duration_seconds},
        )

    def _measure_quality_score(self, scores: List[float]) -> MetricResult:
        """Measure quality score (average)"""
        if not scores:
            return MetricResult(name="quality_score", value=0.0, unit="score")

        avg_score = statistics.mean(scores)
        std_dev = statistics.stdev(scores) if len(scores) > 1 else 0

        return MetricResult(
            name="quality_score",
            value=avg_score,
            unit="score",
            metadata={"std_dev": std_dev, "count": len(scores)},
        )

    def evaluate(
        self,
        name: str,
        func: Callable,
        *args,
        metrics: Optional[List[str]] = None,
        **kwargs,
    ) -> EvaluationResult:
        """Evaluate a function with metrics"""
        result = EvaluationResult(name=name)
        result.start_time = datetime.now()

        try:
            # Run function
            func_result = func(*args, **kwargs)
            result.success = True

            # Collect metrics
            metrics_to_run = metrics or list(self.metrics.keys())

            for metric_name in metrics_to_run:
                if metric_name in self.metrics:
                    try:
                        metric_result = self.metrics[metric_name](func, *args, **kwargs)
                        if isinstance(metric_result, MetricResult):
                            result.add_metric(metric_result)
                    except Exception as e:
                        result.add_metric(
                            MetricResult(
                                name=metric_name,
                                value=0.0,
                                unit="error",
                                metadata={"error": str(e)},
                            )
                        )

        except Exception as e:
            result.success = False
            result.error = str(e)

        result.end_time = datetime.now()
        result.duration_ms = (
            result.end_time - result.start_time
        ).total_seconds() * 1000

        self.evaluations.append(result)
        return result

    def evaluate_batch(
        self,
        name: str,
        func: Callable,
        inputs: List[Any],
        metrics: Optional[List[str]] = None,
    ) -> List[EvaluationResult]:
        """Evaluate multiple inputs"""
        results = []

        for i, input_data in enumerate(inputs):
            result = self.evaluate(
                name=f"{name}_{i}", func=func, args=(input_data,), metrics=metrics
            )
            results.append(result)

        return results

    def get_statistics(self, metric_name: str) -> Dict[str, float]:
        """Get statistics for a metric across all evaluations"""
        values = []

        for evaluation in self.evaluations:
            metric = evaluation.get_metric(metric_name)
            if metric:
                values.append(metric.value)

        if not values:
            return {"count": 0}

        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all evaluations"""
        return {
            "total_evaluations": len(self.evaluations),
            "successful": sum(1 for e in self.evaluations if e.success),
            "failed": sum(1 for e in self.evaluations if not e.success),
            "avg_duration_ms": (
                statistics.mean([e.duration_ms for e in self.evaluations])
                if self.evaluations
                else 0
            ),
            "metrics_available": list(self.metrics.keys()),
        }

    def clear_evaluations(self):
        """Clear all evaluations"""
        self.evaluations.clear()


class Benchmark:
    """Run benchmarks and compare results"""

    def __init__(self, name: str = "default"):
        self.name = name
        self.benchmarks: Dict[str, List[EvaluationResult]] = {}
        self.baseline: Optional[EvaluationResult] = None

    def add_benchmark(self, name: str, result: EvaluationResult):
        """Add a benchmark result"""
        if name not in self.benchmarks:
            self.benchmarks[name] = []
        self.benchmarks[name].append(result)

    def set_baseline(self, result: EvaluationResult):
        """Set baseline for comparison"""
        self.baseline = result

    def compare_to_baseline(self, result: EvaluationResult) -> Dict[str, Any]:
        """Compare result to baseline"""
        if not self.baseline:
            return {"error": "No baseline set"}

        comparison = {
            "name": result.name,
            "baseline_name": self.baseline.name,
            "duration_diff_ms": result.duration_ms - self.baseline.duration_ms,
            "metrics": {},
        }

        for metric in result.metrics:
            baseline_metric = self.baseline.get_metric(metric.name)
            if baseline_metric:
                diff = metric.value - baseline_metric.value
                pct_change = (
                    (diff / baseline_metric.value * 100)
                    if baseline_metric.value != 0
                    else 0
                )

                comparison["metrics"][metric.name] = {
                    "value": metric.value,
                    "baseline": baseline_metric.value,
                    "diff": diff,
                    "pct_change": pct_change,
                }

        return comparison

    def get_rankings(
        self, metric_name: str, ascending: bool = True
    ) -> List[Dict[str, Any]]:
        """Get rankings for a metric"""
        rankings = []

        for name, results in self.benchmarks.items():
            for result in results:
                metric = result.get_metric(metric_name)
                if metric:
                    rankings.append(
                        {
                            "benchmark": name,
                            "evaluation_id": result.id,
                            "value": metric.value,
                            "unit": metric.unit,
                        }
                    )

        return sorted(rankings, key=lambda x: x["value"], reverse=not ascending)

    def get_best(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Get best result for a metric"""
        rankings = self.get_rankings(metric_name, ascending=True)
        return rankings[0] if rankings else None

    def get_worst(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Get worst result for a metric"""
        rankings = self.get_rankings(metric_name, ascending=False)
        return rankings[0] if rankings else None

    def export_results(self) -> str:
        """Export results as JSON"""
        data = {
            "name": self.name,
            "baseline": self.baseline.to_dict() if self.baseline else None,
            "benchmarks": {
                name: [r.to_dict() for r in results]
                for name, results in self.benchmarks.items()
            },
        }
        return json.dumps(data, indent=2)

    def import_results(self, json_data: str):
        """Import results from JSON"""
        data = json.loads(json_data)

        if data.get("baseline"):
            baseline_data = data["baseline"]
            self.baseline = EvaluationResult(
                id=baseline_data["id"], name=baseline_data["name"]
            )

        for name, results in data.get("benchmarks", {}).items():
            for result_data in results:
                result = EvaluationResult(
                    id=result_data["id"], name=result_data["name"]
                )
                self.add_benchmark(name, result)


# Pre-defined benchmarks
def create_performance_benchmark() -> Benchmark:
    """Create a performance benchmark"""
    return Benchmark(name="performance")


def create_quality_benchmark() -> Benchmark:
    """Create a quality benchmark"""
    return Benchmark(name="quality")


def create_cost_benchmark() -> Benchmark:
    """Create a cost benchmark"""
    return Benchmark(name="cost")
