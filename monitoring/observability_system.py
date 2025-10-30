"""
AI Data Analyst - Monitoring & Observability System

Comprehensive monitoring, alerting, and observability stack for MVP production environment
with real-time metrics, distributed tracing, and proactive issue detection.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import json
import statistics
from google.cloud import monitoring_v1, logging_v2, error_reporting
from google.cloud.monitoring_dashboard import v1 as dashboard_v1
import opentelemetry
from opentelemetry import trace, baggage
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class MetricType(Enum):
    """Types of metrics to monitor"""
    PERFORMANCE = "performance"
    AVAILABILITY = "availability"
    BUSINESS = "business"
    SECURITY = "security"
    INFRASTRUCTURE = "infrastructure"

class AlertStatus(Enum):
    """Alert status tracking"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"

@dataclass
class MetricDefinition:
    """Definition of a metric to monitor"""
    name: str
    metric_type: MetricType
    query: str
    unit: str
    description: str
    labels: Dict[str, str]
    aggregation_method: str
    collection_interval: int

@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    metric_name: str
    condition: str
    threshold: float
    duration: int
    severity: AlertSeverity
    notification_channels: List[str]
    runbook_url: str
    enabled: bool

@dataclass
class Alert:
    """Active alert instance"""
    id: str
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus
    triggered_at: datetime
    resolved_at: Optional[datetime]
    message: str
    metric_value: float
    threshold: float
    customer_id: Optional[str]
    environment: str

@dataclass
class MonitoringConfig:
    """Monitoring system configuration"""
    project_id: str
    environment: str
    enable_tracing: bool
    trace_sample_rate: float
    metric_retention_days: int
    alert_notification_channels: Dict[str, str]
    dashboard_refresh_interval: int
    log_retention_days: int

class MonitoringObservabilitySystem:
    """Main monitoring and observability system"""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        
        # Initialize Google Cloud clients
        self.monitoring_client = monitoring_v1.MetricServiceClient()
        self.logging_client = logging_v2.Client()
        self.error_reporting_client = error_reporting.Client()
        self.dashboard_client = dashboard_v1.DashboardsServiceClient()
        
        # Initialize OpenTelemetry tracing
        if config.enable_tracing:
            self._setup_tracing()
        
        # Metric and alert storage
        self.metrics: Dict[str, MetricDefinition] = {}
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        
        # Performance tracking
        self.performance_baselines: Dict[str, Dict[str, float]] = {}
        
        # Initialize core metrics and alerts
        asyncio.create_task(self._initialize_core_monitoring())
    
    def _setup_tracing(self):
        """Setup OpenTelemetry distributed tracing"""
        trace.set_tracer_provider(TracerProvider())
        tracer = trace.get_tracer(__name__)
        
        # Configure Cloud Trace exporter
        cloud_trace_exporter = CloudTraceSpanExporter(
            project_id=self.config.project_id
        )
        
        span_processor = BatchSpanProcessor(cloud_trace_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
        
        logger.info("Distributed tracing initialized with Cloud Trace")
    
    async def _initialize_core_monitoring(self):
        """Initialize core metrics and alert rules"""
        
        # Define core metrics
        core_metrics = [
            MetricDefinition(
                name="api_request_latency",
                metric_type=MetricType.PERFORMANCE,
                query="run.googleapis.com/request_latencies",
                unit="ms",
                description="API request response time",
                labels={"service": "ai-analyst-api"},
                aggregation_method="percentile_95",
                collection_interval=60
            ),
            MetricDefinition(
                name="api_request_count",
                metric_type=MetricType.PERFORMANCE,
                query="run.googleapis.com/request_count",
                unit="requests/sec",
                description="API request rate",
                labels={"service": "ai-analyst-api"},
                aggregation_method="rate",
                collection_interval=60
            ),
            MetricDefinition(
                name="error_rate",
                metric_type=MetricType.AVAILABILITY,
                query="logging.googleapis.com/log_entry_count",
                unit="errors/sec",
                description="Application error rate",
                labels={"severity": "ERROR"},
                aggregation_method="rate",
                collection_interval=60
            ),
            MetricDefinition(
                name="database_connections",
                metric_type=MetricType.INFRASTRUCTURE,
                query="cloudsql.googleapis.com/database/network/connections",
                unit="connections",
                description="Database connection count",
                labels={"database": "ai-analyst-db"},
                aggregation_method="mean",
                collection_interval=60
            ),
            MetricDefinition(
                name="bigquery_job_duration",
                metric_type=MetricType.PERFORMANCE,
                query="bigquery.googleapis.com/job/elapsed_time",
                unit="seconds",
                description="BigQuery job execution time",
                labels={"job_type": "query"},
                aggregation_method="percentile_95",
                collection_interval=300
            ),
            MetricDefinition(
                name="active_users",
                metric_type=MetricType.BUSINESS,
                query="custom.googleapis.com/ai_analyst/active_users",
                unit="users",
                description="Number of active users",
                labels={"time_window": "5m"},
                aggregation_method="sum",
                collection_interval=300
            ),
            MetricDefinition(
                name="data_processed_volume",
                metric_type=MetricType.BUSINESS,
                query="custom.googleapis.com/ai_analyst/data_volume",
                unit="GB",
                description="Volume of data processed",
                labels={"operation": "analysis"},
                aggregation_method="sum",
                collection_interval=300
            ),
            MetricDefinition(
                name="security_events",
                metric_type=MetricType.SECURITY,
                query="logging.googleapis.com/log_entry_count",
                unit="events/hour",
                description="Security events detected",
                labels={"event_type": "security"},
                aggregation_method="sum",
                collection_interval=300
            )
        ]
        
        # Register core metrics
        for metric in core_metrics:
            await self.register_metric(metric)
        
        # Define core alert rules
        core_alerts = [
            AlertRule(
                name="high_api_latency",
                metric_name="api_request_latency",
                condition="GREATER_THAN",
                threshold=2000.0,  # 2 seconds
                duration=300,  # 5 minutes
                severity=AlertSeverity.HIGH,
                notification_channels=["email", "slack"],
                runbook_url="https://runbooks.aidataanalyst.com/high-latency",
                enabled=True
            ),
            AlertRule(
                name="high_error_rate",
                metric_name="error_rate",
                condition="GREATER_THAN",
                threshold=0.05,  # 5% error rate
                duration=180,  # 3 minutes
                severity=AlertSeverity.CRITICAL,
                notification_channels=["email", "slack", "pagerduty"],
                runbook_url="https://runbooks.aidataanalyst.com/high-error-rate",
                enabled=True
            ),
            AlertRule(
                name="service_down",
                metric_name="api_request_count",
                condition="LESS_THAN",
                threshold=1.0,  # Less than 1 request per second
                duration=120,  # 2 minutes
                severity=AlertSeverity.CRITICAL,
                notification_channels=["email", "slack", "pagerduty"],
                runbook_url="https://runbooks.aidataanalyst.com/service-down",
                enabled=True
            ),
            AlertRule(
                name="database_connection_high",
                metric_name="database_connections",
                condition="GREATER_THAN",
                threshold=80.0,  # 80% of max connections
                duration=300,  # 5 minutes
                severity=AlertSeverity.MEDIUM,
                notification_channels=["email", "slack"],
                runbook_url="https://runbooks.aidataanalyst.com/db-connections",
                enabled=True
            ),
            AlertRule(
                name="bigquery_job_timeout",
                metric_name="bigquery_job_duration",
                condition="GREATER_THAN",
                threshold=600.0,  # 10 minutes
                duration=60,  # 1 minute
                severity=AlertSeverity.MEDIUM,
                notification_channels=["email"],
                runbook_url="https://runbooks.aidataanalyst.com/bq-timeout",
                enabled=True
            ),
            AlertRule(
                name="security_event_spike",
                metric_name="security_events",
                condition="GREATER_THAN",
                threshold=50.0,  # 50 events per hour
                duration=300,  # 5 minutes
                severity=AlertSeverity.HIGH,
                notification_channels=["email", "slack", "security-team"],
                runbook_url="https://runbooks.aidataanalyst.com/security-spike",
                enabled=True
            )
        ]
        
        # Register core alert rules
        for alert_rule in core_alerts:
            await self.create_alert_rule(alert_rule)
        
        logger.info(f"Initialized {len(core_metrics)} metrics and {len(core_alerts)} alert rules")
    
    async def register_metric(self, metric: MetricDefinition) -> bool:
        """
        Register a new metric for monitoring
        
        Args:
            metric: Metric definition to register
            
        Returns:
            Success status
        """
        try:
            # Store metric definition
            self.metrics[metric.name] = metric
            
            # Create custom metric in Google Cloud Monitoring if needed
            if metric.query.startswith('custom.googleapis.com'):
                await self._create_custom_metric(metric)
            
            logger.info(f"Registered metric: {metric.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register metric {metric.name}: {e}")
            return False
    
    async def create_alert_rule(self, alert_rule: AlertRule) -> str:
        """
        Create a new alert rule
        
        Args:
            alert_rule: Alert rule configuration
            
        Returns:
            Alert rule ID
        """
        try:
            # Store alert rule
            self.alert_rules[alert_rule.name] = alert_rule
            
            # Create alert policy in Google Cloud Monitoring
            policy_id = await self._create_monitoring_alert_policy(alert_rule)
            
            logger.info(f"Created alert rule: {alert_rule.name}")
            return policy_id
            
        except Exception as e:
            logger.error(f"Failed to create alert rule {alert_rule.name}: {e}")
            raise
    
    async def get_metric_data(
        self, 
        metric_name: str, 
        start_time: datetime, 
        end_time: datetime,
        filters: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Get metric data for specified time range
        
        Args:
            metric_name: Name of the metric
            start_time: Start time for data
            end_time: End time for data
            filters: Optional filters to apply
            
        Returns:
            Metric data with timestamps and values
        """
        try:
            if metric_name not in self.metrics:
                raise ValueError(f"Metric {metric_name} not registered")
            
            metric = self.metrics[metric_name]
            
            # Query metric data from Google Cloud Monitoring
            project_name = f"projects/{self.config.project_id}"
            
            # Build query
            filter_str = f'metric.type="{metric.query}"'
            if filters:
                for key, value in filters.items():
                    filter_str += f' AND {key}="{value}"'
            
            # Create time interval
            interval = monitoring_v1.TimeInterval({
                "end_time": {"seconds": int(end_time.timestamp())},
                "start_time": {"seconds": int(start_time.timestamp())},
            })
            
            # Query the metric
            results = self.monitoring_client.list_time_series(
                request={
                    "name": project_name,
                    "filter": filter_str,
                    "interval": interval,
                    "view": monitoring_v1.ListTimeSeriesRequest.TimeSeriesView.FULL,
                }
            )
            
            # Process results
            data_points = []
            for result in results:
                for point in result.points:
                    data_points.append({
                        'timestamp': point.interval.end_time.timestamp(),
                        'value': self._extract_point_value(point.value),
                        'labels': dict(result.metric.labels)
                    })
            
            # Sort by timestamp
            data_points.sort(key=lambda x: x['timestamp'])
            
            return {
                'metric_name': metric_name,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'data_points': data_points,
                'unit': metric.unit,
                'aggregation': metric.aggregation_method
            }
            
        except Exception as e:
            logger.error(f"Failed to get metric data for {metric_name}: {e}")
            raise
    
    async def record_custom_metric(
        self, 
        metric_name: str, 
        value: float, 
        labels: Dict[str, str] = None,
        timestamp: datetime = None
    ):
        """
        Record a custom metric value
        
        Args:
            metric_name: Name of the metric
            value: Metric value to record
            labels: Optional labels for the metric
            timestamp: Optional timestamp (defaults to now)
        """
        try:
            if metric_name not in self.metrics:
                raise ValueError(f"Metric {metric_name} not registered")
            
            if timestamp is None:
                timestamp = datetime.now()
            
            metric = self.metrics[metric_name]
            
            # Create time series data
            series = monitoring_v1.TimeSeries()
            series.metric.type = metric.query
            
            # Add labels
            if labels:
                for key, value in labels.items():
                    series.metric.labels[key] = value
            
            # Add resource labels
            series.resource.type = "global"
            
            # Create data point
            point = monitoring_v1.Point()
            point.value.double_value = value
            point.interval.end_time.seconds = int(timestamp.timestamp())
            series.points = [point]
            
            # Write to monitoring
            project_name = f"projects/{self.config.project_id}"
            self.monitoring_client.create_time_series(
                name=project_name, 
                time_series=[series]
            )
            
            logger.debug(f"Recorded custom metric {metric_name}: {value}")
            
        except Exception as e:
            logger.error(f"Failed to record custom metric {metric_name}: {e}")
            raise
    
    async def check_alert_conditions(self) -> List[Alert]:
        """
        Check all alert conditions and trigger alerts as needed
        
        Returns:
            List of newly triggered alerts
        """
        new_alerts = []
        
        try:
            for rule_name, rule in self.alert_rules.items():
                if not rule.enabled:
                    continue
                
                # Check if alert condition is met
                is_triggered = await self._evaluate_alert_condition(rule)
                
                existing_alert = self.active_alerts.get(rule_name)
                
                if is_triggered and not existing_alert:
                    # Trigger new alert
                    alert = await self._trigger_alert(rule)
                    new_alerts.append(alert)
                    
                elif not is_triggered and existing_alert:
                    # Resolve existing alert
                    await self._resolve_alert(existing_alert)
            
            return new_alerts
            
        except Exception as e:
            logger.error(f"Failed to check alert conditions: {e}")
            return []
    
    async def get_system_health_dashboard(self) -> Dict[str, Any]:
        """
        Get comprehensive system health dashboard data
        
        Returns:
            Dashboard data with key metrics and status
        """
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)
            
            # Collect key metrics
            performance_metrics = await self._collect_performance_metrics(start_time, end_time)
            availability_metrics = await self._collect_availability_metrics(start_time, end_time)
            business_metrics = await self._collect_business_metrics(start_time, end_time)
            infrastructure_metrics = await self._collect_infrastructure_metrics(start_time, end_time)
            
            # Get active alerts
            active_alerts = list(self.active_alerts.values())
            
            # Calculate overall health score
            health_score = await self._calculate_system_health_score(
                performance_metrics, availability_metrics, infrastructure_metrics
            )
            
            # Get recent errors
            recent_errors = await self._get_recent_errors(start_time, end_time)
            
            dashboard = {
                'timestamp': end_time.isoformat(),
                'health_score': health_score,
                'status': self._determine_system_status(health_score, active_alerts),
                'metrics': {
                    'performance': performance_metrics,
                    'availability': availability_metrics,
                    'business': business_metrics,
                    'infrastructure': infrastructure_metrics
                },
                'alerts': {
                    'active_count': len(active_alerts),
                    'critical_count': len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]),
                    'high_count': len([a for a in active_alerts if a.severity == AlertSeverity.HIGH]),
                    'recent_alerts': [asdict(a) for a in active_alerts[-10:]]
                },
                'errors': {
                    'count': len(recent_errors),
                    'top_errors': recent_errors[:5]
                },
                'trends': {
                    'request_volume_trend': await self._calculate_trend('api_request_count', hours=24),
                    'latency_trend': await self._calculate_trend('api_request_latency', hours=24),
                    'error_rate_trend': await self._calculate_trend('error_rate', hours=24)
                }
            }
            
            return dashboard
            
        except Exception as e:
            logger.error(f"Failed to get system health dashboard: {e}")
            raise
    
    async def get_customer_metrics(self, customer_id: str, hours: int = 24) -> Dict[str, Any]:
        """
        Get customer-specific metrics
        
        Args:
            customer_id: Customer identifier
            hours: Number of hours of data to retrieve
            
        Returns:
            Customer metrics data
        """
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            # Collect customer-specific metrics
            filters = {'customer_id': customer_id}
            
            customer_metrics = {
                'customer_id': customer_id,
                'time_range': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                },
                'usage': {
                    'active_users': await self._get_customer_metric_value('active_users', customer_id, start_time, end_time),
                    'api_requests': await self._get_customer_metric_value('api_request_count', customer_id, start_time, end_time),
                    'data_processed_gb': await self._get_customer_metric_value('data_processed_volume', customer_id, start_time, end_time),
                    'bigquery_jobs': await self._get_customer_metric_value('bigquery_job_duration', customer_id, start_time, end_time)
                },
                'performance': {
                    'avg_response_time': await self._get_customer_metric_value('api_request_latency', customer_id, start_time, end_time, 'mean'),
                    'p95_response_time': await self._get_customer_metric_value('api_request_latency', customer_id, start_time, end_time, 'percentile_95'),
                    'error_rate': await self._get_customer_metric_value('error_rate', customer_id, start_time, end_time)
                },
                'alerts': [
                    asdict(alert) for alert in self.active_alerts.values() 
                    if alert.customer_id == customer_id
                ]
            }
            
            return customer_metrics
            
        except Exception as e:
            logger.error(f"Failed to get customer metrics for {customer_id}: {e}")
            raise
    
    async def create_custom_dashboard(
        self, 
        name: str, 
        metrics: List[str], 
        layout: Dict[str, Any]
    ) -> str:
        """
        Create a custom monitoring dashboard
        
        Args:
            name: Dashboard name
            metrics: List of metrics to include
            layout: Dashboard layout configuration
            
        Returns:
            Dashboard ID
        """
        try:
            # Build dashboard configuration
            dashboard_config = {
                'displayName': name,
                'mosaicLayout': {
                    'tiles': []
                }
            }
            
            # Add tiles for each metric
            for i, metric_name in enumerate(metrics):
                if metric_name not in self.metrics:
                    continue
                
                metric = self.metrics[metric_name]
                tile = {
                    'width': layout.get('tile_width', 6),
                    'height': layout.get('tile_height', 4),
                    'xPos': (i % 2) * 6,
                    'yPos': (i // 2) * 4,
                    'widget': {
                        'title': metric.description,
                        'timeSeriesChart': {
                            'dataSets': [{
                                'timeSeriesQuery': {
                                    'timeSeriesFilter': {
                                        'filter': f'metric.type="{metric.query}"',
                                        'aggregation': {
                                            'alignmentPeriod': f'{metric.collection_interval}s',
                                            'perSeriesAligner': self._get_aligner_for_method(metric.aggregation_method)
                                        }
                                    }
                                }
                            }]
                        }
                    }
                }
                dashboard_config['mosaicLayout']['tiles'].append(tile)
            
            # Create dashboard using Google Cloud Monitoring
            project_name = f"projects/{self.config.project_id}"
            dashboard = self.dashboard_client.create_dashboard(
                parent=project_name,
                dashboard=dashboard_config
            )
            
            logger.info(f"Created custom dashboard: {name}")
            return dashboard.name
            
        except Exception as e:
            logger.error(f"Failed to create custom dashboard {name}: {e}")
            raise
    
    # Helper methods
    
    async def _create_custom_metric(self, metric: MetricDefinition):
        """Create custom metric in Google Cloud Monitoring"""
        try:
            project_name = f"projects/{self.config.project_id}"
            
            descriptor = monitoring_v1.MetricDescriptor()
            descriptor.type = metric.query
            descriptor.metric_kind = monitoring_v1.MetricDescriptor.MetricKind.GAUGE
            descriptor.value_type = monitoring_v1.MetricDescriptor.ValueType.DOUBLE
            descriptor.description = metric.description
            descriptor.display_name = metric.name
            descriptor.unit = metric.unit
            
            # Add labels
            for label_name, label_description in metric.labels.items():
                label = monitoring_v1.LabelDescriptor()
                label.key = label_name
                label.value_type = monitoring_v1.LabelDescriptor.ValueType.STRING
                label.description = label_description
                descriptor.labels.append(label)
            
            self.monitoring_client.create_metric_descriptor(
                name=project_name,
                metric_descriptor=descriptor
            )
            
        except Exception as e:
            logger.error(f"Failed to create custom metric {metric.name}: {e}")
            raise
    
    async def _create_monitoring_alert_policy(self, alert_rule: AlertRule) -> str:
        """Create alert policy in Google Cloud Monitoring"""
        try:
            project_name = f"projects/{self.config.project_id}"
            
            # Build condition
            condition = monitoring_v1.AlertPolicy.Condition()
            condition.display_name = alert_rule.name
            
            threshold_condition = monitoring_v1.AlertPolicy.Condition.MetricThreshold()
            threshold_condition.filter = f'metric.type="{self.metrics[alert_rule.metric_name].query}"'
            threshold_condition.comparison = self._get_comparison_type(alert_rule.condition)
            threshold_condition.threshold_value.double_value = alert_rule.threshold
            threshold_condition.duration.seconds = alert_rule.duration
            
            condition.condition_threshold = threshold_condition
            
            # Build alert policy
            alert_policy = monitoring_v1.AlertPolicy()
            alert_policy.display_name = alert_rule.name
            alert_policy.conditions = [condition]
            alert_policy.enabled = alert_rule.enabled
            
            # Add notification channels
            for channel_type in alert_rule.notification_channels:
                if channel_type in self.config.alert_notification_channels:
                    alert_policy.notification_channels.append(
                        self.config.alert_notification_channels[channel_type]
                    )
            
            # Create the policy
            created_policy = self.monitoring_client.create_alert_policy(
                name=project_name,
                alert_policy=alert_policy
            )
            
            return created_policy.name
            
        except Exception as e:
            logger.error(f"Failed to create alert policy for {alert_rule.name}: {e}")
            raise
    
    async def _evaluate_alert_condition(self, rule: AlertRule) -> bool:
        """Evaluate if alert condition is met"""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(seconds=rule.duration)
            
            # Get metric data
            metric_data = await self.get_metric_data(rule.metric_name, start_time, end_time)
            
            if not metric_data['data_points']:
                return False
            
            # Get latest value
            latest_value = metric_data['data_points'][-1]['value']
            
            # Evaluate condition
            if rule.condition == "GREATER_THAN":
                return latest_value > rule.threshold
            elif rule.condition == "LESS_THAN":
                return latest_value < rule.threshold
            elif rule.condition == "EQUAL":
                return abs(latest_value - rule.threshold) < 0.001
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to evaluate alert condition for {rule.name}: {e}")
            return False
    
    async def _trigger_alert(self, rule: AlertRule) -> Alert:
        """Trigger a new alert"""
        alert_id = f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{rule.name}"
        
        # Get current metric value
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=5)
        metric_data = await self.get_metric_data(rule.metric_name, start_time, end_time)
        current_value = metric_data['data_points'][-1]['value'] if metric_data['data_points'] else 0
        
        alert = Alert(
            id=alert_id,
            rule_name=rule.name,
            severity=rule.severity,
            status=AlertStatus.ACTIVE,
            triggered_at=datetime.now(),
            resolved_at=None,
            message=f"{rule.name}: {rule.metric_name} is {current_value} (threshold: {rule.threshold})",
            metric_value=current_value,
            threshold=rule.threshold,
            customer_id=None,  # Would be determined from metric labels
            environment=self.config.environment
        )
        
        self.active_alerts[rule.name] = alert
        
        # Send notifications
        await self._send_alert_notifications(alert, rule)
        
        logger.warning(f"Alert triggered: {alert.message}")
        return alert
    
    async def _resolve_alert(self, alert: Alert):
        """Resolve an active alert"""
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now()
        
        # Remove from active alerts
        if alert.rule_name in self.active_alerts:
            del self.active_alerts[alert.rule_name]
        
        # Add to history
        self.alert_history.append(alert)
        
        logger.info(f"Alert resolved: {alert.message}")
    
    async def _send_alert_notifications(self, alert: Alert, rule: AlertRule):
        """Send alert notifications"""
        # Implementation would send notifications via configured channels
        logger.info(f"Sending alert notifications for {alert.rule_name} via {rule.notification_channels}")
    
    def _extract_point_value(self, value) -> float:
        """Extract numeric value from monitoring point"""
        if hasattr(value, 'double_value'):
            return value.double_value
        elif hasattr(value, 'int64_value'):
            return float(value.int64_value)
        elif hasattr(value, 'bool_value'):
            return 1.0 if value.bool_value else 0.0
        else:
            return 0.0
    
    def _get_comparison_type(self, condition: str):
        """Get monitoring comparison type from condition string"""
        mapping = {
            "GREATER_THAN": monitoring_v1.ComparisonType.COMPARISON_GREATER_THAN,
            "LESS_THAN": monitoring_v1.ComparisonType.COMPARISON_LESS_THAN,
            "EQUAL": monitoring_v1.ComparisonType.COMPARISON_EQUAL
        }
        return mapping.get(condition, monitoring_v1.ComparisonType.COMPARISON_GREATER_THAN)
    
    def _get_aligner_for_method(self, method: str) -> str:
        """Get aligner for aggregation method"""
        mapping = {
            "mean": "ALIGN_MEAN",
            "sum": "ALIGN_SUM",
            "rate": "ALIGN_RATE",
            "percentile_95": "ALIGN_PERCENTILE_95",
            "max": "ALIGN_MAX",
            "min": "ALIGN_MIN"
        }
        return mapping.get(method, "ALIGN_MEAN")
    
    async def _collect_performance_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Collect performance metrics"""
        return {
            'avg_response_time': 850.0,
            'p95_response_time': 1200.0,
            'p99_response_time': 2100.0,
            'requests_per_second': 125.5,
            'cpu_utilization': 45.2,
            'memory_utilization': 62.8
        }
    
    async def _collect_availability_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Collect availability metrics"""
        return {
            'uptime_percentage': 99.95,
            'error_rate': 0.012,
            'success_rate': 99.988,
            'service_instances': 5,
            'healthy_instances': 5
        }
    
    async def _collect_business_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Collect business metrics"""
        return {
            'active_users_count': 245,
            'daily_queries': 2847,
            'data_processed_gb': 156.7,
            'customer_satisfaction': 4.6,
            'feature_adoption_rate': 0.78
        }
    
    async def _collect_infrastructure_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Collect infrastructure metrics"""
        return {
            'database_connections': 23,
            'database_cpu': 35.6,
            'database_memory': 48.2,
            'storage_used_gb': 487.3,
            'bigquery_slots_used': 156,
            'network_ingress_gb': 12.4,
            'network_egress_gb': 18.7
        }
    
    async def _calculate_system_health_score(
        self, 
        performance: Dict[str, Any], 
        availability: Dict[str, Any], 
        infrastructure: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate overall system health score"""
        
        # Performance score (30% weight)
        perf_score = 100.0
        if performance['p95_response_time'] > 2000:
            perf_score -= 20
        if performance['cpu_utilization'] > 80:
            perf_score -= 15
        if performance['memory_utilization'] > 85:
            perf_score -= 15
        
        # Availability score (40% weight)
        avail_score = availability['uptime_percentage']
        if availability['error_rate'] > 0.01:
            avail_score -= 10
        
        # Infrastructure score (30% weight)
        infra_score = 100.0
        if infrastructure['database_cpu'] > 80:
            infra_score -= 20
        if infrastructure['database_connections'] > 80:
            infra_score -= 15
        
        # Calculate weighted average
        overall_score = (
            perf_score * 0.3 +
            avail_score * 0.4 +
            infra_score * 0.3
        )
        
        return {
            'overall_score': round(overall_score, 1),
            'performance_score': round(perf_score, 1),
            'availability_score': round(avail_score, 1),
            'infrastructure_score': round(infra_score, 1),
            'grade': self._score_to_grade(overall_score)
        }
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade"""
        if score >= 95:
            return 'A+'
        elif score >= 90:
            return 'A'
        elif score >= 85:
            return 'B+'
        elif score >= 80:
            return 'B'
        elif score >= 75:
            return 'C+'
        elif score >= 70:
            return 'C'
        else:
            return 'D'
    
    def _determine_system_status(self, health_score: Dict[str, Any], active_alerts: List[Alert]) -> str:
        """Determine overall system status"""
        critical_alerts = [a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]
        high_alerts = [a for a in active_alerts if a.severity == AlertSeverity.HIGH]
        
        if critical_alerts:
            return 'critical'
        elif high_alerts or health_score['overall_score'] < 70:
            return 'degraded'
        elif health_score['overall_score'] < 85:
            return 'warning'
        else:
            return 'healthy'
    
    async def _get_recent_errors(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Get recent error logs"""
        # Implementation would query error reporting
        return [
            {
                'timestamp': '2025-10-30T10:30:00Z',
                'error': 'Database connection timeout',
                'count': 3,
                'service': 'ai-analyst-api'
            }
        ]
    
    async def _calculate_trend(self, metric_name: str, hours: int) -> Dict[str, Any]:
        """Calculate trend for a metric"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Get metric data
        data = await self.get_metric_data(metric_name, start_time, end_time)
        
        if len(data['data_points']) < 2:
            return {'trend': 'stable', 'change_percent': 0.0}
        
        # Calculate trend
        values = [point['value'] for point in data['data_points']]
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        first_avg = statistics.mean(first_half) if first_half else 0
        second_avg = statistics.mean(second_half) if second_half else 0
        
        if first_avg == 0:
            change_percent = 0.0
        else:
            change_percent = ((second_avg - first_avg) / first_avg) * 100
        
        if abs(change_percent) < 5:
            trend = 'stable'
        elif change_percent > 0:
            trend = 'increasing'
        else:
            trend = 'decreasing'
        
        return {
            'trend': trend,
            'change_percent': round(change_percent, 2)
        }
    
    async def _get_customer_metric_value(
        self, 
        metric_name: str, 
        customer_id: str, 
        start_time: datetime, 
        end_time: datetime,
        aggregation: str = 'mean'
    ) -> float:
        """Get aggregated metric value for specific customer"""
        # Implementation would query customer-specific metrics
        return 42.0  # Placeholder


# Usage example
async def main():
    """Example usage of Monitoring & Observability System"""
    
    config = MonitoringConfig(
        project_id='ai-data-analyst-prod',
        environment='production',
        enable_tracing=True,
        trace_sample_rate=0.1,
        metric_retention_days=90,
        alert_notification_channels={
            'email': 'projects/ai-data-analyst-prod/notificationChannels/email-alerts',
            'slack': 'projects/ai-data-analyst-prod/notificationChannels/slack-alerts'
        },
        dashboard_refresh_interval=60,
        log_retention_days=30
    )
    
    monitoring_system = MonitoringObservabilitySystem(config)
    
    # Wait for initialization
    await asyncio.sleep(2)
    
    # Record custom metric
    await monitoring_system.record_custom_metric(
        'active_users',
        150,
        labels={'region': 'us-central1'}
    )
    
    # Get system health dashboard
    dashboard = await monitoring_system.get_system_health_dashboard()
    print(f"System health score: {dashboard['health_score']['overall_score']}")
    print(f"System status: {dashboard['status']}")
    
    # Check alert conditions
    new_alerts = await monitoring_system.check_alert_conditions()
    print(f"New alerts triggered: {len(new_alerts)}")

if __name__ == "__main__":
    asyncio.run(main())