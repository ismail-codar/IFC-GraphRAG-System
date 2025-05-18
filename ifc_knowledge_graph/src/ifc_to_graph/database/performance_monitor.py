"""
Performance Monitoring for Neo4j Operations

This module provides functionality to measure, track, and analyze the performance
of Neo4j database operations, focusing on query execution times and resource usage.
"""

import logging
import time
import json
import datetime
from typing import Dict, List, Any, Optional, Callable
import threading
import statistics
import psutil
import platform
from functools import wraps

# Configure logging
logger = logging.getLogger(__name__)

class PerformanceMetric:
    """
    Container for a single performance metric with its metadata.
    """
    
    def __init__(
        self, 
        name: str, 
        value: float, 
        unit: str, 
        timestamp: float,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a performance metric.
        
        Args:
            name: Name of the metric
            value: Value of the metric
            unit: Unit of measurement (e.g., 'ms', 'MB', 'count')
            timestamp: Unix timestamp when the metric was recorded
            context: Additional contextual information
        """
        self.name = name
        self.value = value
        self.unit = unit
        self.timestamp = timestamp
        self.context = context or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary representation."""
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp,
            "datetime": datetime.datetime.fromtimestamp(self.timestamp).isoformat(),
            "context": self.context
        }


class PerformanceMonitor:
    """
    Class for monitoring and analyzing Neo4j operation performance.
    """
    
    def __init__(self, enabled: bool = True):
        """
        Initialize the performance monitor.
        
        Args:
            enabled: Whether performance monitoring is enabled
        """
        self.enabled = enabled
        self.metrics: List[PerformanceMetric] = []
        self._lock = threading.Lock()
        
        # Basic system info
        self.system_info = {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(logical=True),
            "physical_cpu_count": psutil.cpu_count(logical=False),
            "memory_total": psutil.virtual_memory().total,
        }
        
        if enabled:
            logger.info("Performance monitoring enabled")
        
    def record_metric(
        self, 
        name: str, 
        value: float, 
        unit: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a performance metric.
        
        Args:
            name: Name of the metric
            value: Value of the metric
            unit: Unit of measurement
            context: Additional contextual information
        """
        if not self.enabled:
            return
        
        with self._lock:
            metric = PerformanceMetric(
                name=name,
                value=value,
                unit=unit,
                timestamp=time.time(),
                context=context
            )
            self.metrics.append(metric)
    
    def start_timer(self, name: str, context: Optional[Dict[str, Any]] = None) -> Callable:
        """
        Start a timer for an operation.
        
        Args:
            name: Name of the timer
            context: Additional contextual information
            
        Returns:
            Function to stop the timer and record the metric
        """
        if not self.enabled:
            return lambda: None
        
        start_time = time.time()
        
        def stop_timer() -> float:
            if not self.enabled:
                return 0
            
            elapsed_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            self.record_metric(
                name=f"{name}_duration",
                value=elapsed_time,
                unit="ms",
                context=context
            )
            return elapsed_time
        
        return stop_timer
    
    def measure_memory(self, name: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Measure current memory usage.
        
        Args:
            name: Name for the memory measurement
            context: Additional contextual information
        """
        if not self.enabled:
            return
        
        # Get current process memory usage
        process = psutil.Process()
        memory_info = process.memory_info()
        
        # Record RSS (Resident Set Size)
        self.record_metric(
            name=f"{name}_memory_rss",
            value=memory_info.rss / (1024 * 1024),  # Convert to MB
            unit="MB",
            context=context
        )
        
        # Record VMS (Virtual Memory Size)
        self.record_metric(
            name=f"{name}_memory_vms",
            value=memory_info.vms / (1024 * 1024),  # Convert to MB
            unit="MB",
            context=context
        )
    
    def get_metrics_by_name(self, name: str) -> List[PerformanceMetric]:
        """
        Get all metrics with a specific name.
        
        Args:
            name: Name of the metrics to retrieve
            
        Returns:
            List of matching metrics
        """
        return [m for m in self.metrics if m.name == name]
    
    def get_statistics(self, metric_name: str) -> Dict[str, Any]:
        """
        Calculate statistics for a specific metric.
        
        Args:
            metric_name: Name of the metric to analyze
            
        Returns:
            Dictionary with statistics
        """
        metrics = self.get_metrics_by_name(metric_name)
        if not metrics:
            return {"count": 0}
        
        values = [m.value for m in metrics]
        
        stats = {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "unit": metrics[0].unit
        }
        
        # Calculate standard deviation if we have enough values
        if len(values) > 1:
            stats["std_dev"] = statistics.stdev(values)
        
        return stats
    
    def get_all_statistics(self) -> Dict[str, Dict[str, Any]]:
        """
        Calculate statistics for all metrics.
        
        Returns:
            Dictionary mapping metric names to their statistics
        """
        unique_names = set(m.name for m in self.metrics)
        return {name: self.get_statistics(name) for name in unique_names}
    
    def export_metrics(self, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Export all metrics to a JSON file.
        
        Args:
            file_path: Optional path to save JSON file
            
        Returns:
            Dictionary with all metrics and statistics
        """
        # Prepare the export data
        export_data = {
            "system_info": self.system_info,
            "metrics": [m.to_dict() for m in self.metrics],
            "statistics": self.get_all_statistics(),
            "export_time": datetime.datetime.now().isoformat()
        }
        
        # Save to file if path provided
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(export_data, f, indent=2)
                logger.info(f"Performance metrics exported to {file_path}")
            except Exception as e:
                logger.error(f"Error exporting metrics to {file_path}: {str(e)}")
        
        return export_data
    
    def clear_metrics(self) -> None:
        """Clear all recorded metrics."""
        with self._lock:
            self.metrics = []
    
    def summary_report(self) -> str:
        """
        Generate a human-readable summary report.
        
        Returns:
            String containing the summary report
        """
        if not self.metrics:
            return "No performance metrics recorded."
        
        stats = self.get_all_statistics()
        
        report = ["Performance Monitor Summary Report"]
        report.append("=" * 80)
        report.append(f"Total metrics recorded: {len(self.metrics)}")
        report.append(f"Unique metric types: {len(stats)}")
        report.append(f"System: {self.system_info['platform']}")
        report.append(f"Python version: {self.system_info['python_version']}")
        report.append(f"Memory available: {self.system_info['memory_total'] / (1024**3):.2f} GB")
        report.append("-" * 80)
        
        # Report on query durations
        query_metrics = {k: v for k, v in stats.items() if k.endswith("_duration")}
        if query_metrics:
            report.append("\nQuery Performance:")
            for name, stat in query_metrics.items():
                report.append(f"  {name.replace('_duration', '')}:")
                report.append(f"    Count: {stat['count']} calls")
                report.append(f"    Average: {stat['mean']:.2f} {stat['unit']}")
                report.append(f"    Median: {stat['median']:.2f} {stat['unit']}")
                report.append(f"    Min/Max: {stat['min']:.2f}/{stat['max']:.2f} {stat['unit']}")
                if "std_dev" in stat:
                    report.append(f"    Std Dev: {stat['std_dev']:.2f} {stat['unit']}")
        
        # Report on memory usage
        memory_metrics = {k: v for k, v in stats.items() if "memory" in k}
        if memory_metrics:
            report.append("\nMemory Usage:")
            for name, stat in memory_metrics.items():
                report.append(f"  {name.replace('_memory_rss', '').replace('_memory_vms', '')}:")
                if name.endswith("_rss"):
                    report.append(f"    Average RSS: {stat['mean']:.2f} {stat['unit']}")
                    report.append(f"    Peak RSS: {stat['max']:.2f} {stat['unit']}")
                elif name.endswith("_vms"):
                    report.append(f"    Average VMS: {stat['mean']:.2f} {stat['unit']}")
                    report.append(f"    Peak VMS: {stat['max']:.2f} {stat['unit']}")
        
        return "\n".join(report)


def timing_decorator(monitor: PerformanceMonitor):
    """
    Decorator to automatically time function execution.
    
    Args:
        monitor: Performance monitor instance
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not monitor.enabled:
                return func(*args, **kwargs)
                
            timer_name = f"{func.__module__}.{func.__qualname__}"
            stop_timer = monitor.start_timer(timer_name)
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                stop_timer()
        
        return wrapper
    
    return decorator 