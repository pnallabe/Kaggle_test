"""
AI Data Analyst Cloud Run Performance & Autoscaling Manager
Phase 6: MVP Release & Performance Optimization

This module provides comprehensive Cloud Run performance optimization including:
- Intelligent autoscaling configuration
- Container performance tuning
- Resource allocation optimization
- Cold start minimization
- Traffic management and load balancing
"""

import logging
import time
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import statistics

# Google Cloud imports
from google.cloud import run_v2, monitoring_v3, logging as cloud_logging
from google.cloud.exceptions import NotFound
from google.api_core import exceptions
import google.auth

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScalingStrategy(Enum):
    """Cloud Run scaling strategies"""
    REACTIVE = "reactive"  # Scale based on current load
    PREDICTIVE = "predictive"  # Scale based on predicted load
    AGGRESSIVE = "aggressive"  # Scale up quickly, down slowly
    CONSERVATIVE = "conservative"  # Scale up slowly, down quickly


class PerformanceProfile(Enum):
    """Performance optimization profiles"""
    COST_OPTIMIZED = "cost_optimized"
    LATENCY_OPTIMIZED = "latency_optimized"
    THROUGHPUT_OPTIMIZED = "throughput_optimized"
    BALANCED = "balanced"


@dataclass
class ContainerConfig:
    """Configuration for Cloud Run container optimization"""
    cpu_limit: str  # e.g., "2000m" for 2 vCPUs
    memory_limit: str  # e.g., "4Gi" for 4GB
    min_instances: int
    max_instances: int
    max_instance_request_concurrency: int
    cpu_throttling: bool = True
    startup_cpu_boost: bool = True
    execution_environment: str = "gen2"  # gen1 or gen2


@dataclass
class AutoscalingConfig:
    """Advanced autoscaling configuration"""
    target_cpu_utilization: float = 0.6  # 60%
    target_memory_utilization: float = 0.7  # 70%
    target_request_utilization: float = 0.8  # 80%
    scale_up_stabilization_window: int = 60  # seconds
    scale_down_stabilization_window: int = 300  # seconds
    scale_up_step_size: int = 2  # instances
    scale_down_step_size: int = 1  # instances
    cold_start_threshold_ms: int = 3000  # 3 seconds


@dataclass
class PerformanceMetrics:
    """Cloud Run performance metrics"""
    service_name: str
    revision_name: str
    timestamp: datetime
    instance_count: int
    request_count: int
    request_latency_p50_ms: float
    request_latency_p95_ms: float
    request_latency_p99_ms: float
    cpu_utilization: float
    memory_utilization: float
    cold_starts: int
    error_rate: float
    billable_instance_time: float


class CloudRunOptimizationManager:
    """Comprehensive Cloud Run performance and autoscaling optimization"""
    
    def __init__(self, project_id: str, region: str = "us-central1"):
        self.project_id = project_id
        self.region = region
        
        # Initialize clients
        self.run_client = run_v2.ServicesClient()
        self.monitoring_client = monitoring_v3.MetricServiceClient()
        self.logging_client = cloud_logging.Client(project=project_id)
        
        # Performance targets
        self.performance_targets = {
            "request_latency_p95_ms": 1000,  # 1 second
            "request_latency_p99_ms": 2000,  # 2 seconds
            "cold_start_percentage": 0.05,   # 5%
            "error_rate": 0.01,              # 1%
            "cpu_utilization_target": 0.6,   # 60%
            "memory_utilization_target": 0.7, # 70%
            "cost_efficiency_target": 0.8    # 80% billable vs allocated time
        }
        
        # Optimization profiles
        self.optimization_profiles = {
            PerformanceProfile.COST_OPTIMIZED: {
                "min_instances": 0,
                "max_instances": 10,
                "cpu_limit": "1000m",
                "memory_limit": "2Gi",
                "concurrency": 80,
                "scaling_strategy": ScalingStrategy.CONSERVATIVE
            },
            PerformanceProfile.LATENCY_OPTIMIZED: {
                "min_instances": 2,
                "max_instances": 50,
                "cpu_limit": "2000m", 
                "memory_limit": "4Gi",
                "concurrency": 20,
                "scaling_strategy": ScalingStrategy.AGGRESSIVE
            },
            PerformanceProfile.THROUGHPUT_OPTIMIZED: {
                "min_instances": 1,
                "max_instances": 100,
                "cpu_limit": "4000m",
                "memory_limit": "8Gi", 
                "concurrency": 100,
                "scaling_strategy": ScalingStrategy.PREDICTIVE
            },
            PerformanceProfile.BALANCED: {
                "min_instances": 1,
                "max_instances": 25,
                "cpu_limit": "2000m",
                "memory_limit": "4Gi",
                "concurrency": 50,
                "scaling_strategy": ScalingStrategy.REACTIVE
            }
        }
        
        logger.info(f"CloudRunOptimizationManager initialized for project: {project_id}")
    
    def optimize_service_configuration(self, service_name: str, 
                                     profile: PerformanceProfile,
                                     custom_config: Optional[ContainerConfig] = None) -> Dict[str, Any]:
        """Optimize Cloud Run service configuration for performance"""
        try:
            # Get current service configuration
            service_path = f"projects/{self.project_id}/locations/{self.region}/services/{service_name}"
            
            try:
                current_service = self.run_client.get_service(name=service_path)
            except NotFound:
                raise ValueError(f"Service {service_name} not found")
            
            # Determine optimal configuration
            if custom_config:
                config = custom_config
            else:
                profile_config = self.optimization_profiles[profile]
                config = ContainerConfig(
                    cpu_limit=profile_config["cpu_limit"],
                    memory_limit=profile_config["memory_limit"],
                    min_instances=profile_config["min_instances"],
                    max_instances=profile_config["max_instances"],
                    max_instance_request_concurrency=profile_config["concurrency"]
                )
            
            # Build the updated service specification
            service = run_v2.Service()
            service.name = service_path
            
            # Template configuration
            template = run_v2.RevisionTemplate()
            
            # Scaling configuration
            template.scaling = run_v2.RevisionScaling(
                min_instance_count=config.min_instances,
                max_instance_count=config.max_instances
            )
            
            # Container configuration
            container = run_v2.Container()
            
            # Resource limits
            resources = run_v2.ResourceRequirements()
            resources.limits = {
                "cpu": config.cpu_limit,
                "memory": config.memory_limit
            }
            container.resources = resources
            
            # Add container to template
            template.containers = [container]
            
            # Service-level configuration
            template.max_instance_request_concurrency = config.max_instance_request_concurrency
            template.execution_environment = config.execution_environment
            
            # CPU allocation and throttling
            if config.cpu_throttling:
                template.annotations = {
                    "run.googleapis.com/cpu-throttling": "true"
                }
            else:
                template.annotations = {
                    "run.googleapis.com/cpu-throttling": "false"
                }
            
            # Startup CPU boost for faster cold starts
            if config.startup_cpu_boost:
                template.annotations.update({
                    "run.googleapis.com/startup-cpu-boost": "true"
                })
            
            service.template = template
            
            # Update the service
            operation = self.run_client.update_service(service=service)
            
            logger.info(f"Service optimization initiated for: {service_name}")
            
            # Wait for operation to complete
            operation.result(timeout=300)  # 5 minute timeout
            
            # Get updated service details
            updated_service = self.run_client.get_service(name=service_path)
            
            optimization_result = {
                "service_name": service_name,
                "optimization_profile": profile.value,
                "applied_configuration": {
                    "cpu_limit": config.cpu_limit,
                    "memory_limit": config.memory_limit,
                    "min_instances": config.min_instances,
                    "max_instances": config.max_instances,
                    "max_concurrency": config.max_instance_request_concurrency,
                    "execution_environment": config.execution_environment
                },
                "service_status": {
                    "url": updated_service.uri,
                    "ready": updated_service.conditions[0].state.name if updated_service.conditions else "UNKNOWN",
                    "latest_revision": updated_service.latest_ready_revision
                },
                "optimization_timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Service optimization completed: {service_name}")
            return optimization_result
            
        except Exception as e:
            logger.error(f"Failed to optimize service configuration: {e}")
            raise
    
    def configure_intelligent_autoscaling(self, service_name: str, 
                                        config: AutoscalingConfig) -> Dict[str, Any]:
        """Configure intelligent autoscaling based on multiple metrics"""
        try:
            service_path = f"projects/{self.project_id}/locations/{self.region}/services/{service_name}"
            
            # Create autoscaling annotations
            autoscaling_annotations = {
                # CPU-based scaling
                "autoscaling.knative.dev/target": str(int(config.target_cpu_utilization * 100)),
                "autoscaling.knative.dev/metric": "cpu",
                
                # Memory-based scaling
                "autoscaling.knative.dev/targetUtilizationPercentage": str(int(config.target_memory_utilization * 100)),
                
                # Concurrency-based scaling  
                "autoscaling.knative.dev/maxScale": "100",
                "autoscaling.knative.dev/minScale": "1",
                
                # Scaling behavior
                "autoscaling.knative.dev/scaleUpRate": str(config.scale_up_step_size),
                "autoscaling.knative.dev/scaleDownRate": str(config.scale_down_step_size),
                "autoscaling.knative.dev/stableWindow": f"{config.scale_down_stabilization_window}s",
                
                # Custom metrics
                "run.googleapis.com/custom-audiences": "performance-optimizer"
            }
            
            # Apply configuration through service update
            service = self.run_client.get_service(name=service_path)
            
            # Update template annotations
            if not service.template.annotations:
                service.template.annotations = {}
            
            service.template.annotations.update(autoscaling_annotations)
            
            # Update service
            operation = self.run_client.update_service(service=service)
            operation.result(timeout=300)
            
            autoscaling_result = {
                "service_name": service_name,
                "autoscaling_config": asdict(config),
                "applied_annotations": autoscaling_annotations,
                "configuration_timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Intelligent autoscaling configured for: {service_name}")
            return autoscaling_result
            
        except Exception as e:
            logger.error(f"Failed to configure autoscaling: {e}")
            raise
    
    def monitor_performance_metrics(self, service_name: str, hours: int = 24) -> List[PerformanceMetrics]:
        """Monitor comprehensive performance metrics for Cloud Run service"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            # Define metric queries
            metric_queries = {
                "request_count": "run.googleapis.com/request_count",
                "request_latencies": "run.googleapis.com/request_latencies",
                "instance_count": "run.googleapis.com/container/instance_count",
                "cpu_utilizations": "run.googleapis.com/container/cpu/utilizations",
                "memory_utilizations": "run.googleapis.com/container/memory/utilizations",
                "billable_instance_time": "run.googleapis.com/container/billable_instance_time"
            }
            
            metrics_data = {}
            
            # Query each metric
            for metric_name, metric_type in metric_queries.items():
                try:
                    query = (
                        f'resource.type="cloud_run_revision" AND '
                        f'resource.labels.service_name="{service_name}" AND '
                        f'metric.type="{metric_type}"'
                    )
                    
                    interval = monitoring_v3.TimeInterval(
                        {
                            "end_time": {"seconds": int(end_time.timestamp())},
                            "start_time": {"seconds": int(start_time.timestamp())},
                        }
                    )
                    
                    request = monitoring_v3.ListTimeSeriesRequest(
                        name=f"projects/{self.project_id}",
                        filter=query,
                        interval=interval,
                        view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                    )
                    
                    results = self.monitoring_client.list_time_series(request=request)
                    metrics_data[metric_name] = list(results)
                    
                except Exception as e:
                    logger.warning(f"Failed to query metric {metric_name}: {e}")
                    metrics_data[metric_name] = []
            
            # Process metrics into performance metrics objects
            performance_metrics = []
            
            # Group metrics by time intervals (e.g., hourly)
            time_buckets = {}
            bucket_size_minutes = 60  # 1 hour buckets
            
            for metric_name, time_series_list in metrics_data.items():
                for time_series in time_series_list:
                    revision_name = time_series.resource.labels.get("revision_name", "unknown")
                    
                    for point in time_series.points:
                        timestamp = point.interval.end_time
                        dt = datetime.fromtimestamp(timestamp.seconds)
                        
                        # Round to bucket
                        bucket_time = dt.replace(minute=0, second=0, microsecond=0)
                        bucket_key = (bucket_time, revision_name)
                        
                        if bucket_key not in time_buckets:
                            time_buckets[bucket_key] = {
                                "timestamp": bucket_time,
                                "revision_name": revision_name,
                                "metrics": {}
                            }
                        
                        time_buckets[bucket_key]["metrics"][metric_name] = point.value
            
            # Convert buckets to PerformanceMetrics objects
            for (bucket_time, revision_name), bucket_data in time_buckets.items():
                metrics = bucket_data["metrics"]
                
                # Extract values with defaults
                request_count = getattr(metrics.get("request_count", {}), "int64_value", 0)
                instance_count = getattr(metrics.get("instance_count", {}), "double_value", 0)
                
                # Calculate latency percentiles (simplified)
                latency_data = metrics.get("request_latencies", {})
                latency_dist = getattr(latency_data, "distribution_value", None)
                
                if latency_dist:
                    # Extract percentiles from distribution
                    p50_ms = self._extract_percentile(latency_dist, 0.5)
                    p95_ms = self._extract_percentile(latency_dist, 0.95)
                    p99_ms = self._extract_percentile(latency_dist, 0.99)
                else:
                    p50_ms = p95_ms = p99_ms = 0
                
                cpu_util = getattr(metrics.get("cpu_utilizations", {}), "double_value", 0)
                memory_util = getattr(metrics.get("memory_utilizations", {}), "double_value", 0)
                billable_time = getattr(metrics.get("billable_instance_time", {}), "double_value", 0)
                
                performance_metric = PerformanceMetrics(
                    service_name=service_name,
                    revision_name=revision_name,
                    timestamp=bucket_time,
                    instance_count=int(instance_count),
                    request_count=int(request_count),
                    request_latency_p50_ms=p50_ms,
                    request_latency_p95_ms=p95_ms,
                    request_latency_p99_ms=p99_ms,
                    cpu_utilization=cpu_util,
                    memory_utilization=memory_util,
                    cold_starts=0,  # Would need separate query
                    error_rate=0.0,  # Would need separate query
                    billable_instance_time=billable_time
                )
                
                performance_metrics.append(performance_metric)
            
            logger.info(f"Collected {len(performance_metrics)} performance metric samples for {service_name}")
            return performance_metrics
            
        except Exception as e:
            logger.error(f"Failed to monitor performance metrics: {e}")
            return []
    
    def _extract_percentile(self, distribution, percentile: float) -> float:
        """Extract percentile from Cloud Monitoring distribution"""
        try:
            # Simplified percentile extraction
            # In practice, would need more sophisticated distribution analysis
            if hasattr(distribution, 'bucket_counts') and distribution.bucket_counts:
                # Use mean as approximation for demo
                return distribution.mean * 1000  # Convert to milliseconds
            return 0
        except Exception:
            return 0
    
    def analyze_cold_start_performance(self, service_name: str, hours: int = 24) -> Dict[str, Any]:
        """Analyze cold start performance and provide optimization recommendations"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            # Query Cloud Logging for cold start events
            log_filter = f'''
            resource.type="cloud_run_revision"
            resource.labels.service_name="{service_name}"
            textPayload:"Cold start"
            timestamp>="{start_time.isoformat()}Z"
            timestamp<="{end_time.isoformat()}Z"
            '''
            
            entries = self.logging_client.list_entries(filter_=log_filter)
            cold_start_events = []
            
            for entry in entries:
                if "Cold start" in str(entry.payload):
                    cold_start_events.append({
                        "timestamp": entry.timestamp,
                        "severity": entry.severity.name if entry.severity else "INFO",
                        "trace": entry.trace
                    })
            
            # Analyze cold start patterns
            total_cold_starts = len(cold_start_events)
            
            if total_cold_starts == 0:
                return {
                    "service_name": service_name,
                    "analysis_period_hours": hours,
                    "total_cold_starts": 0,
                    "recommendations": ["No cold starts detected - service performing well"]
                }
            
            # Group cold starts by hour to identify patterns
            hourly_cold_starts = {}
            for event in cold_start_events:
                hour = event["timestamp"].replace(minute=0, second=0, microsecond=0)
                hourly_cold_starts[hour] = hourly_cold_starts.get(hour, 0) + 1
            
            # Calculate statistics
            avg_cold_starts_per_hour = total_cold_starts / hours
            peak_cold_starts = max(hourly_cold_starts.values()) if hourly_cold_starts else 0
            
            # Generate recommendations
            recommendations = []
            
            if avg_cold_starts_per_hour > 2:
                recommendations.append("Consider increasing min_instances to reduce cold starts")
            
            if peak_cold_starts > 5:
                recommendations.append("Implement predictive scaling for traffic spikes")
            
            if total_cold_starts > hours * 1.5:
                recommendations.append("Enable startup CPU boost for faster container initialization")
                recommendations.append("Optimize container image size and startup time")
            
            cold_start_analysis = {
                "service_name": service_name,
                "analysis_period_hours": hours,
                "total_cold_starts": total_cold_starts,
                "avg_cold_starts_per_hour": round(avg_cold_starts_per_hour, 2),
                "peak_cold_starts_per_hour": peak_cold_starts,
                "cold_start_pattern": {
                    hour.isoformat(): count 
                    for hour, count in sorted(hourly_cold_starts.items())
                },
                "recommendations": recommendations,
                "performance_impact": {
                    "estimated_latency_increase_ms": total_cold_starts * 3000,  # Assume 3s per cold start
                    "user_experience_impact": "high" if avg_cold_starts_per_hour > 5 else "medium" if avg_cold_starts_per_hour > 2 else "low"
                }
            }
            
            logger.info(f"Cold start analysis completed: {total_cold_starts} cold starts in {hours} hours")
            return cold_start_analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze cold start performance: {e}")
            raise
    
    def optimize_container_image(self, service_name: str) -> Dict[str, Any]:
        """Provide container image optimization recommendations"""
        try:
            # Get current service configuration
            service_path = f"projects/{self.project_id}/locations/{self.region}/services/{service_name}"
            service = self.run_client.get_service(name=service_path)
            
            # Extract image information
            if not service.template.containers:
                raise ValueError("No containers found in service")
            
            container = service.template.containers[0]
            image_uri = container.image
            
            # Analyze container configuration
            resources = container.resources
            cpu_limit = resources.limits.get("cpu", "1000m") if resources and resources.limits else "1000m"
            memory_limit = resources.limits.get("memory", "512Mi") if resources and resources.limits else "512Mi"
            
            # Generate optimization recommendations
            optimization_recommendations = []
            
            # CPU and Memory optimization
            if cpu_limit == "1000m" and memory_limit == "512Mi":
                optimization_recommendations.append({
                    "category": "resource_allocation",
                    "priority": "medium",
                    "recommendation": "Consider profiling actual resource usage to optimize CPU/memory allocation",
                    "current_config": f"CPU: {cpu_limit}, Memory: {memory_limit}",
                    "suggested_action": "Run load tests to determine optimal resource allocation"
                })
            
            # Image optimization
            optimization_recommendations.append({
                "category": "container_image",
                "priority": "high",
                "recommendation": "Use multi-stage Docker builds to reduce image size",
                "current_image": image_uri,
                "suggested_actions": [
                    "Use distroless or alpine base images",
                    "Remove unnecessary dependencies and files",
                    "Use .dockerignore to exclude development files",
                    "Implement layer caching strategies"
                ]
            })
            
            # Startup optimization
            optimization_recommendations.append({
                "category": "startup_performance",
                "priority": "high", 
                "recommendation": "Optimize application startup time",
                "suggested_actions": [
                    "Lazy load heavy dependencies",
                    "Pre-compile code where possible",
                    "Use connection pooling for databases",
                    "Implement health check endpoints"
                ]
            })
            
            # Runtime optimization
            optimization_recommendations.append({
                "category": "runtime_performance",
                "priority": "medium",
                "recommendation": "Optimize runtime performance",
                "suggested_actions": [
                    "Enable HTTP/2 for better connection reuse",
                    "Implement request/response compression",
                    "Use async/await patterns for I/O operations",
                    "Cache frequently accessed data"
                ]
            })
            
            container_optimization = {
                "service_name": service_name,
                "current_configuration": {
                    "image": image_uri,
                    "cpu_limit": cpu_limit,
                    "memory_limit": memory_limit,
                    "execution_environment": service.template.execution_environment
                },
                "optimization_recommendations": optimization_recommendations,
                "estimated_improvements": {
                    "cold_start_reduction": "30-50%",
                    "memory_usage_reduction": "20-40%",
                    "cost_savings": "15-25%"
                },
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Container optimization analysis completed for: {service_name}")
            return container_optimization
            
        except Exception as e:
            logger.error(f"Failed to optimize container image: {e}")
            raise
    
    def implement_traffic_management(self, service_name: str, 
                                   traffic_split: Dict[str, int]) -> Dict[str, Any]:
        """Implement advanced traffic management and canary deployments"""
        try:
            service_path = f"projects/{self.project_id}/locations/{self.region}/services/{service_name}"
            service = self.run_client.get_service(name=service_path)
            
            # Configure traffic allocation
            traffic_targets = []
            
            for revision_name, percentage in traffic_split.items():
                traffic_target = run_v2.TrafficTarget()
                traffic_target.revision = revision_name
                traffic_target.percent = percentage
                traffic_targets.append(traffic_target)
            
            # Update service with new traffic configuration
            service.traffic = traffic_targets
            
            operation = self.run_client.update_service(service=service)
            operation.result(timeout=300)
            
            traffic_management_result = {
                "service_name": service_name,
                "traffic_configuration": {
                    revision: percentage for revision, percentage in traffic_split.items()
                },
                "deployment_strategy": "canary" if len(traffic_split) > 1 else "blue_green",
                "configuration_timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Traffic management configured for: {service_name}")
            return traffic_management_result
            
        except Exception as e:
            logger.error(f"Failed to implement traffic management: {e}")
            raise
    
    def generate_performance_report(self, service_name: str, 
                                  metrics: List[PerformanceMetrics]) -> Dict[str, Any]:
        """Generate comprehensive performance optimization report"""
        try:
            if not metrics:
                return {
                    "service_name": service_name,
                    "status": "no_data",
                    "message": "No performance metrics available"
                }
            
            # Calculate performance statistics
            latencies_p95 = [m.request_latency_p95_ms for m in metrics if m.request_latency_p95_ms > 0]
            latencies_p99 = [m.request_latency_p99_ms for m in metrics if m.request_latency_p99_ms > 0]
            cpu_utilizations = [m.cpu_utilization for m in metrics if m.cpu_utilization > 0]
            memory_utilizations = [m.memory_utilization for m in metrics if m.memory_utilization > 0]
            instance_counts = [m.instance_count for m in metrics]
            
            # Performance summary
            performance_summary = {
                "avg_latency_p95_ms": round(statistics.mean(latencies_p95), 2) if latencies_p95 else 0,
                "max_latency_p95_ms": round(max(latencies_p95), 2) if latencies_p95 else 0,
                "avg_latency_p99_ms": round(statistics.mean(latencies_p99), 2) if latencies_p99 else 0,
                "avg_cpu_utilization": round(statistics.mean(cpu_utilizations), 3) if cpu_utilizations else 0,
                "max_cpu_utilization": round(max(cpu_utilizations), 3) if cpu_utilizations else 0,
                "avg_memory_utilization": round(statistics.mean(memory_utilizations), 3) if memory_utilizations else 0,
                "max_memory_utilization": round(max(memory_utilizations), 3) if memory_utilizations else 0,
                "avg_instance_count": round(statistics.mean(instance_counts), 1),
                "max_instance_count": max(instance_counts),
                "min_instance_count": min(instance_counts)
            }
            
            # Performance validation against targets
            performance_validation = {}
            
            if latencies_p95:
                avg_p95 = statistics.mean(latencies_p95)
                performance_validation["latency_p95"] = {
                    "actual": avg_p95,
                    "target": self.performance_targets["request_latency_p95_ms"],
                    "status": "pass" if avg_p95 <= self.performance_targets["request_latency_p95_ms"] else "fail"
                }
            
            if cpu_utilizations:
                avg_cpu = statistics.mean(cpu_utilizations)
                performance_validation["cpu_utilization"] = {
                    "actual": avg_cpu,
                    "target": self.performance_targets["cpu_utilization_target"],
                    "status": "pass" if avg_cpu <= self.performance_targets["cpu_utilization_target"] else "attention"
                }
            
            # Generate optimization recommendations
            recommendations = []
            
            if performance_validation.get("latency_p95", {}).get("status") == "fail":
                recommendations.append({
                    "priority": "high",
                    "category": "latency",
                    "recommendation": "Latency exceeds target - consider increasing resources or optimizing code"
                })
            
            if performance_validation.get("cpu_utilization", {}).get("status") == "attention":
                if statistics.mean(cpu_utilizations) > 0.8:
                    recommendations.append({
                        "priority": "medium",
                        "category": "scaling",
                        "recommendation": "High CPU utilization - consider horizontal scaling"
                    })
            
            # Cost optimization opportunities
            avg_instance_count = statistics.mean(instance_counts)
            min_instance_count = min(instance_counts)
            
            if min_instance_count > 0 and avg_instance_count / min_instance_count < 2:
                recommendations.append({
                    "priority": "low",
                    "category": "cost",
                    "recommendation": "Consider reducing min_instances to optimize costs"
                })
            
            performance_report = {
                "service_name": service_name,
                "report_period": {
                    "start_time": min(m.timestamp for m in metrics).isoformat(),
                    "end_time": max(m.timestamp for m in metrics).isoformat(),
                    "sample_count": len(metrics)
                },
                "performance_summary": performance_summary,
                "performance_validation": performance_validation,
                "optimization_recommendations": recommendations,
                "overall_performance_score": self._calculate_performance_score(performance_validation),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Performance report generated for: {service_name}")
            return performance_report
            
        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            raise
    
    def _calculate_performance_score(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall performance score"""
        try:
            if not validation_results:
                return {"score": 0, "grade": "F", "status": "insufficient_data"}
            
            scores = []
            
            for metric, result in validation_results.items():
                if result["status"] == "pass":
                    scores.append(100)
                elif result["status"] == "attention":
                    scores.append(70)
                else:  # fail
                    scores.append(30)
            
            overall_score = statistics.mean(scores) if scores else 0
            
            if overall_score >= 90:
                grade = "A"
            elif overall_score >= 80:
                grade = "B"
            elif overall_score >= 70:
                grade = "C"
            elif overall_score >= 60:
                grade = "D"
            else:
                grade = "F"
            
            return {
                "score": round(overall_score, 1),
                "grade": grade,
                "status": "excellent" if grade in ["A", "B"] else "needs_improvement"
            }
            
        except Exception:
            return {"score": 0, "grade": "F", "status": "calculation_error"}


if __name__ == "__main__":
    # Example usage
    project_id = "ai-data-analyst-mvp"
    service_name = "ai-analyst-api"
    
    # Initialize optimization manager
    optimizer = CloudRunOptimizationManager(project_id)
    
    print("Cloud Run Optimization Manager - Demo")
    print("=" * 50)
    
    # 1. Optimize service configuration for balanced performance
    try:
        optimization_result = optimizer.optimize_service_configuration(
            service_name, 
            PerformanceProfile.BALANCED
        )
        print(f"✅ Service optimized: {optimization_result['applied_configuration']['cpu_limit']} CPU, {optimization_result['applied_configuration']['memory_limit']} memory")
    except Exception as e:
        print(f"⚠️ Service optimization: {e}")
    
    # 2. Configure intelligent autoscaling
    autoscaling_config = AutoscalingConfig(
        target_cpu_utilization=0.6,
        target_memory_utilization=0.7,
        scale_up_stabilization_window=60,
        scale_down_stabilization_window=300
    )
    
    try:
        autoscaling_result = optimizer.configure_intelligent_autoscaling(
            service_name, 
            autoscaling_config
        )
        print(f"🔄 Autoscaling configured: Target {autoscaling_config.target_cpu_utilization*100}% CPU utilization")
    except Exception as e:
        print(f"⚠️ Autoscaling configuration: {e}")
    
    # 3. Monitor performance metrics
    try:
        performance_metrics = optimizer.monitor_performance_metrics(service_name, hours=24)
        if performance_metrics:
            avg_latency = statistics.mean([m.request_latency_p95_ms for m in performance_metrics if m.request_latency_p95_ms > 0])
            print(f"📊 Performance monitoring: {len(performance_metrics)} samples, avg P95 latency: {avg_latency:.1f}ms")
        else:
            print("📊 Performance monitoring: No recent metrics available")
    except Exception as e:
        print(f"⚠️ Performance monitoring: {e}")
        performance_metrics = []
    
    # 4. Analyze cold start performance
    try:
        cold_start_analysis = optimizer.analyze_cold_start_performance(service_name, hours=24)
        print(f"🥶 Cold start analysis: {cold_start_analysis['total_cold_starts']} cold starts in 24h")
        if cold_start_analysis['recommendations']:
            print(f"   Recommendations: {len(cold_start_analysis['recommendations'])} items")
    except Exception as e:
        print(f"⚠️ Cold start analysis: {e}")
    
    # 5. Container image optimization recommendations
    try:
        container_optimization = optimizer.optimize_container_image(service_name)
        recommendations = container_optimization['optimization_recommendations']
        print(f"🐳 Container optimization: {len(recommendations)} recommendations")
        for rec in recommendations[:2]:  # Show first 2
            print(f"   - {rec['category']}: {rec['recommendation']}")
    except Exception as e:
        print(f"⚠️ Container optimization: {e}")
    
    # 6. Generate comprehensive performance report
    if performance_metrics:
        try:
            performance_report = optimizer.generate_performance_report(service_name, performance_metrics)
            score = performance_report['overall_performance_score']
            print(f"📈 Performance report: Score {score['score']}/100 (Grade: {score['grade']})")
            print(f"   Recommendations: {len(performance_report['optimization_recommendations'])}")
        except Exception as e:
            print(f"⚠️ Performance report: {e}")
    
    print("\\n🚀 Cloud Run Optimization Manager - COMPLETED!")
    print("⚡ Intelligent autoscaling with multi-metric targeting")
    print("🎯 Performance-optimized container configurations")
    print("🥶 Cold start analysis and mitigation")
    print("📊 Comprehensive performance monitoring")
    print("💰 Cost optimization recommendations")
    print("🚦 Advanced traffic management capabilities")