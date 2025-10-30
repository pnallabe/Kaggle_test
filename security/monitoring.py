"""
Cloud Monitoring and Alerting Module

This module provides comprehensive monitoring and alerting including:
- SLI/SLO tracking and monitoring
- Custom metrics and dashboards
- Intelligent alerting and notification
- Multi-tenant monitoring isolation
- Performance and availability tracking
- Integration with Google Cloud Monitoring
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
import uuid
import statistics

from google.cloud import monitoring_v3
from google.cloud import logging as cloud_logging
from google.cloud import pubsub_v1
from google.api_core import exceptions
import google.protobuf.duration_pb2 as duration_pb2
import google.protobuf.timestamp_pb2 as timestamp_pb2

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    DISTRIBUTION = "distribution"


class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertState(Enum):
    """Alert states"""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class NotificationChannel(Enum):
    """Notification channel types"""
    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    WEBHOOK = "webhook"


@dataclass
class MetricDefinition:
    """Definition of a custom metric"""
    name: str
    display_name: str
    description: str
    metric_type: MetricType
    unit: str
    labels: List[str] = field(default_factory=list)
    value_type: str = "DOUBLE"  # BOOL, INT64, DOUBLE, STRING, DISTRIBUTION


@dataclass
class SLI:
    """Service Level Indicator definition"""
    name: str
    description: str
    metric_filter: str
    good_service_filter: str
    total_service_filter: str
    rolling_period_days: int = 7
    goal_percentage: float = 99.9


@dataclass
class SLO:
    """Service Level Objective definition"""
    name: str
    description: str
    sli: SLI
    target_percentage: float
    compliance_period_days: int
    burn_rate_threshold: float = 1.0


@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    display_name: str
    description: str
    condition: str
    severity: AlertSeverity
    notification_channels: List[str]
    threshold_value: float
    comparison: str  # GREATER_THAN, LESS_THAN, EQUAL, etc.
    duration: int  # seconds
    enabled: bool = True
    auto_resolve: bool = True
    suppress_duration: int = 3600  # seconds


@dataclass
class Alert:
    """Alert instance"""
    alert_id: str
    rule_name: str
    tenant_id: str
    timestamp: datetime
    severity: AlertSeverity
    state: AlertState
    message: str
    details: Dict[str, Any]
    metric_value: float
    threshold_value: float
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


@dataclass
class Dashboard:
    """Monitoring dashboard configuration"""
    name: str
    display_name: str
    description: str
    tenant_id: Optional[str]
    widgets: List[Dict[str, Any]]
    layout: Dict[str, Any]
    refresh_interval: int = 60  # seconds


class CloudMonitoringManager:
    """Google Cloud Monitoring integration with multi-tenant support"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.project_path = f"projects/{project_id}"
        
        # Initialize clients
        self.client = monitoring_v3.MetricServiceClient()
        self.alert_client = monitoring_v3.AlertPolicyServiceClient()
        self.notification_client = monitoring_v3.NotificationChannelServiceClient()
        self.dashboard_client = monitoring_v3.DashboardsServiceClient()
        
        # Publisher for alert notifications
        self.publisher = pubsub_v1.PublisherClient()
        
        # Define standard SLIs for AI Data Analyst platform
        self.standard_slis = self._define_standard_slis()
        
        # Define standard SLOs
        self.standard_slos = self._define_standard_slos()
        
        # Active alerts tracking
        self.active_alerts: Dict[str, Alert] = {}
    
    def _define_standard_slis(self) -> Dict[str, SLI]:
        """Define standard SLIs for the platform"""
        return {
            "api_availability": SLI(
                name="api_availability",
                description="API endpoint availability",
                metric_filter='resource.type="cloud_run_revision"',
                good_service_filter='response.status_code<400',
                total_service_filter='response.status_code>=200',
                rolling_period_days=7,
                goal_percentage=99.9
            ),
            "query_success_rate": SLI(
                name="query_success_rate",
                description="BigQuery success rate",
                metric_filter='resource.type="bigquery_project"',
                good_service_filter='protoPayload.methodName="jobservice.jobcompleted" AND protoPayload.serviceData.jobCompletedEvent.job.jobStatus.state="DONE"',
                total_service_filter='protoPayload.methodName="jobservice.jobcompleted"',
                rolling_period_days=7,
                goal_percentage=99.5
            ),
            "response_time": SLI(
                name="response_time",
                description="API response time",
                metric_filter='resource.type="cloud_run_revision"',
                good_service_filter='response.latency<=2000ms',
                total_service_filter='response.latency>0',
                rolling_period_days=7,
                goal_percentage=95.0
            ),
            "data_freshness": SLI(
                name="data_freshness",
                description="Data freshness in datasets",
                metric_filter='resource.type="bigquery_dataset"',
                good_service_filter='timestamp_diff(current_timestamp(), last_modified_time, HOUR)<=24',
                total_service_filter='last_modified_time IS NOT NULL',
                rolling_period_days=1,
                goal_percentage=90.0
            )
        }
    
    def _define_standard_slos(self) -> Dict[str, SLO]:
        """Define standard SLOs for the platform"""
        slis = self.standard_slis
        
        return {
            "api_availability_slo": SLO(
                name="api_availability_slo",
                description="API must be available 99.9% of the time",
                sli=slis["api_availability"],
                target_percentage=99.9,
                compliance_period_days=30,
                burn_rate_threshold=1.5
            ),
            "query_success_slo": SLO(
                name="query_success_slo",
                description="Queries must succeed 99.5% of the time",
                sli=slis["query_success_rate"],
                target_percentage=99.5,
                compliance_period_days=30,
                burn_rate_threshold=2.0
            ),
            "response_time_slo": SLO(
                name="response_time_slo",
                description="95% of requests must complete within 2 seconds",
                sli=slis["response_time"],
                target_percentage=95.0,
                compliance_period_days=7,
                burn_rate_threshold=3.0
            ),
            "data_freshness_slo": SLO(
                name="data_freshness_slo",
                description="90% of data must be refreshed within 24 hours",
                sli=slis["data_freshness"],
                target_percentage=90.0,
                compliance_period_days=1,
                burn_rate_threshold=5.0
            )
        }
    
    def create_custom_metric(self, metric_def: MetricDefinition, tenant_id: Optional[str] = None) -> str:
        """Create custom metric in Cloud Monitoring"""
        try:
            # Build metric descriptor
            descriptor = monitoring_v3.MetricDescriptor()
            descriptor.type = f"custom.googleapis.com/ai_analyst/{metric_def.name}"
            if tenant_id:
                descriptor.type = f"custom.googleapis.com/ai_analyst/tenant_{tenant_id}/{metric_def.name}"
            
            descriptor.display_name = metric_def.display_name
            descriptor.description = metric_def.description
            descriptor.unit = metric_def.unit
            
            # Set metric kind based on type
            if metric_def.metric_type == MetricType.COUNTER:
                descriptor.metric_kind = monitoring_v3.MetricDescriptor.MetricKind.CUMULATIVE
            elif metric_def.metric_type == MetricType.GAUGE:
                descriptor.metric_kind = monitoring_v3.MetricDescriptor.MetricKind.GAUGE
            else:
                descriptor.metric_kind = monitoring_v3.MetricDescriptor.MetricKind.GAUGE
            
            # Set value type
            if metric_def.value_type == "BOOL":
                descriptor.value_type = monitoring_v3.MetricDescriptor.ValueType.BOOL
            elif metric_def.value_type == "INT64":
                descriptor.value_type = monitoring_v3.MetricDescriptor.ValueType.INT64
            elif metric_def.value_type == "DOUBLE":
                descriptor.value_type = monitoring_v3.MetricDescriptor.ValueType.DOUBLE
            elif metric_def.value_type == "STRING":
                descriptor.value_type = monitoring_v3.MetricDescriptor.ValueType.STRING
            elif metric_def.value_type == "DISTRIBUTION":
                descriptor.value_type = monitoring_v3.MetricDescriptor.ValueType.DISTRIBUTION
            
            # Add labels
            for label_key in metric_def.labels:
                label = monitoring_v3.LabelDescriptor()
                label.key = label_key
                label.value_type = monitoring_v3.LabelDescriptor.ValueType.STRING
                descriptor.labels.append(label)
            
            # Create the metric descriptor
            created_descriptor = self.client.create_metric_descriptor(
                name=self.project_path,
                metric_descriptor=descriptor
            )
            
            logger.info(f"Created custom metric: {created_descriptor.type}")
            return created_descriptor.type
            
        except Exception as e:
            logger.error(f"Failed to create custom metric {metric_def.name}: {e}")
            raise
    
    def write_time_series(self, metric_type: str, value: Union[int, float, bool, str],
                         labels: Dict[str, str] = None, resource_labels: Dict[str, str] = None,
                         timestamp: datetime = None):
        """Write time series data point"""
        try:
            if timestamp is None:
                timestamp = datetime.utcnow()
            
            # Create time series
            series = monitoring_v3.TimeSeries()
            series.metric.type = metric_type
            
            # Add metric labels
            if labels:
                for key, value_str in labels.items():
                    series.metric.labels[key] = str(value_str)
            
            # Set resource
            series.resource.type = "global"
            if resource_labels:
                for key, value_str in resource_labels.items():
                    series.resource.labels[key] = str(value_str)
            
            # Create data point
            point = monitoring_v3.Point()
            
            # Set timestamp
            point.interval.end_time.seconds = int(timestamp.timestamp())
            point.interval.end_time.nanos = int((timestamp.timestamp() % 1) * 1e9)
            
            # Set value based on type
            if isinstance(value, bool):
                point.value.bool_value = value
            elif isinstance(value, int):
                point.value.int64_value = value
            elif isinstance(value, float):
                point.value.double_value = value
            elif isinstance(value, str):
                point.value.string_value = value
            
            series.points = [point]
            
            # Write the time series
            self.client.create_time_series(
                name=self.project_path,
                time_series=[series]
            )
            
            logger.debug(f"Wrote time series data for metric: {metric_type}")
            
        except Exception as e:
            logger.error(f"Failed to write time series for {metric_type}: {e}")
            raise
    
    def create_alert_policy(self, alert_rule: AlertRule, tenant_id: Optional[str] = None) -> str:
        """Create alert policy in Cloud Monitoring"""
        try:
            # Build alert policy
            policy = monitoring_v3.AlertPolicy()
            policy.display_name = alert_rule.display_name
            policy.documentation.content = alert_rule.description
            policy.enabled = alert_rule.enabled
            
            # Add tenant label if specified
            if tenant_id:
                policy.user_labels["tenant_id"] = tenant_id
            
            # Build condition
            condition = monitoring_v3.AlertPolicy.Condition()
            condition.display_name = alert_rule.name
            
            # Threshold condition
            threshold_condition = monitoring_v3.AlertPolicy.Condition.MetricThreshold()
            threshold_condition.filter = alert_rule.condition
            threshold_condition.duration.seconds = alert_rule.duration
            
            # Set comparison
            if alert_rule.comparison == "GREATER_THAN":
                threshold_condition.comparison = monitoring_v3.ComparisonType.COMPARISON_GREATER_THAN
            elif alert_rule.comparison == "LESS_THAN":
                threshold_condition.comparison = monitoring_v3.ComparisonType.COMPARISON_LESS_THAN
            elif alert_rule.comparison == "EQUAL":
                threshold_condition.comparison = monitoring_v3.ComparisonType.COMPARISON_EQUAL
            
            threshold_condition.threshold_value = alert_rule.threshold_value
            
            condition.condition_threshold = threshold_condition
            policy.conditions = [condition]
            
            # Set notification channels
            policy.notification_channels = alert_rule.notification_channels
            
            # Create alert policy
            created_policy = self.alert_client.create_alert_policy(
                name=self.project_path,
                alert_policy=policy
            )
            
            logger.info(f"Created alert policy: {created_policy.name}")
            return created_policy.name
            
        except Exception as e:
            logger.error(f"Failed to create alert policy {alert_rule.name}: {e}")
            raise
    
    def create_notification_channel(self, channel_type: NotificationChannel,
                                  config: Dict[str, str], tenant_id: Optional[str] = None) -> str:
        """Create notification channel"""
        try:
            # Build notification channel
            channel = monitoring_v3.NotificationChannel()
            channel.display_name = config.get("display_name", f"{channel_type.value}_channel")
            channel.description = config.get("description", f"Notification channel for {channel_type.value}")
            
            # Set type and configuration
            if channel_type == NotificationChannel.EMAIL:
                channel.type_ = "email"
                channel.labels["email_address"] = config["email_address"]
            elif channel_type == NotificationChannel.SMS:
                channel.type_ = "sms"
                channel.labels["number"] = config["phone_number"]
            elif channel_type == NotificationChannel.SLACK:
                channel.type_ = "slack"
                channel.labels["channel_name"] = config["channel_name"]
                channel.labels["url"] = config["webhook_url"]
            elif channel_type == NotificationChannel.WEBHOOK:
                channel.type_ = "webhook_tokenauth"
                channel.labels["url"] = config["webhook_url"]
            
            # Add tenant label if specified
            if tenant_id:
                channel.user_labels["tenant_id"] = tenant_id
            
            # Create notification channel
            created_channel = self.notification_client.create_notification_channel(
                name=self.project_path,
                notification_channel=channel
            )
            
            logger.info(f"Created notification channel: {created_channel.name}")
            return created_channel.name
            
        except Exception as e:
            logger.error(f"Failed to create notification channel: {e}")
            raise
    
    def create_dashboard(self, dashboard_config: Dashboard) -> str:
        """Create monitoring dashboard"""
        try:
            # Build dashboard
            dashboard = monitoring_v3.Dashboard()
            dashboard.display_name = dashboard_config.display_name
            
            # Convert widgets to proper format
            for widget_config in dashboard_config.widgets:
                widget = monitoring_v3.Widget()
                widget.title = widget_config.get("title", "Widget")
                
                # Create different widget types based on config
                if widget_config.get("type") == "line_chart":
                    line_chart = monitoring_v3.Widget.XyChart()
                    
                    # Add data sets
                    for dataset_config in widget_config.get("datasets", []):
                        dataset = monitoring_v3.Widget.XyChart.DataSet()
                        dataset.time_series_query.time_series_filter.filter = dataset_config["filter"]
                        line_chart.data_sets.append(dataset)
                    
                    widget.xy_chart = line_chart
                
                elif widget_config.get("type") == "single_value":
                    single_value = monitoring_v3.Widget.Scorecard()
                    single_value.time_series_query.time_series_filter.filter = widget_config["filter"]
                    widget.scorecard = single_value
                
                dashboard.widgets.append(widget)
            
            # Create dashboard
            created_dashboard = self.dashboard_client.create_dashboard(
                parent=self.project_path,
                dashboard=dashboard
            )
            
            logger.info(f"Created dashboard: {created_dashboard.name}")
            return created_dashboard.name
            
        except Exception as e:
            logger.error(f"Failed to create dashboard {dashboard_config.name}: {e}")
            raise
    
    def calculate_sli_value(self, sli: SLI, start_time: datetime, end_time: datetime) -> float:
        """Calculate SLI value for a time period"""
        try:
            # This would implement actual SLI calculation logic
            # For now, return a mock value
            
            # In a real implementation, this would:
            # 1. Query Cloud Logging or Monitoring for good service events
            # 2. Query for total service events
            # 3. Calculate percentage: (good_events / total_events) * 100
            
            import random
            return random.uniform(95.0, 99.95)  # Mock SLI value
            
        except Exception as e:
            logger.error(f"Failed to calculate SLI value for {sli.name}: {e}")
            raise
    
    def check_slo_compliance(self, slo: SLO, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Check SLO compliance for a time period"""
        try:
            # Calculate current SLI value
            current_sli = self.calculate_sli_value(slo.sli, start_time, end_time)
            
            # Calculate error budget
            error_budget = 100.0 - slo.target_percentage
            consumed_budget = max(0, slo.target_percentage - current_sli)
            budget_remaining = max(0, error_budget - consumed_budget)
            
            # Calculate burn rate
            period_hours = (end_time - start_time).total_seconds() / 3600
            expected_burn_rate = consumed_budget / (error_budget * period_hours / (slo.compliance_period_days * 24))
            
            # Determine compliance status
            is_compliant = current_sli >= slo.target_percentage
            is_burning_fast = expected_burn_rate > slo.burn_rate_threshold
            
            return {
                "slo_name": slo.name,
                "target_percentage": slo.target_percentage,
                "current_sli": current_sli,
                "error_budget": error_budget,
                "consumed_budget": consumed_budget,
                "budget_remaining": budget_remaining,
                "burn_rate": expected_burn_rate,
                "is_compliant": is_compliant,
                "is_burning_fast": is_burning_fast,
                "period_start": start_time.isoformat(),
                "period_end": end_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to check SLO compliance for {slo.name}: {e}")
            raise
    
    def generate_slo_report(self, tenant_id: str, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Generate SLO compliance report for tenant"""
        try:
            report = {
                "tenant_id": tenant_id,
                "report_period": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "generated_at": datetime.utcnow().isoformat(),
                "slo_compliance": {},
                "summary": {
                    "total_slos": len(self.standard_slos),
                    "compliant_slos": 0,
                    "non_compliant_slos": 0,
                    "fast_burning_slos": 0
                }
            }
            
            # Check each SLO
            for slo_name, slo in self.standard_slos.items():
                compliance = self.check_slo_compliance(slo, start_time, end_time)
                report["slo_compliance"][slo_name] = compliance
                
                # Update summary
                if compliance["is_compliant"]:
                    report["summary"]["compliant_slos"] += 1
                else:
                    report["summary"]["non_compliant_slos"] += 1
                
                if compliance["is_burning_fast"]:
                    report["summary"]["fast_burning_slos"] += 1
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate SLO report for tenant {tenant_id}: {e}")
            raise
    
    def trigger_alert(self, alert_rule_name: str, tenant_id: str, metric_value: float,
                     details: Dict[str, Any] = None):
        """Trigger an alert based on conditions"""
        try:
            # Create alert instance
            alert = Alert(
                alert_id=str(uuid.uuid4()),
                rule_name=alert_rule_name,
                tenant_id=tenant_id,
                timestamp=datetime.utcnow(),
                severity=AlertSeverity.HIGH,  # Would determine from rule
                state=AlertState.OPEN,
                message=f"Alert triggered for {alert_rule_name}",
                details=details or {},
                metric_value=metric_value,
                threshold_value=0.0  # Would get from rule
            )
            
            # Store active alert
            self.active_alerts[alert.alert_id] = alert
            
            # Send notifications
            self._send_alert_notifications(alert)
            
            logger.warning(f"Alert triggered: {alert.alert_id} for rule: {alert_rule_name}")
            return alert.alert_id
            
        except Exception as e:
            logger.error(f"Failed to trigger alert for rule {alert_rule_name}: {e}")
            raise
    
    def _send_alert_notifications(self, alert: Alert):
        """Send alert notifications through configured channels"""
        try:
            # Publish to Pub/Sub for notification processing
            topic_path = self.publisher.topic_path(self.project_id, "alert-notifications")
            
            notification_data = {
                "alert_id": alert.alert_id,
                "rule_name": alert.rule_name,
                "tenant_id": alert.tenant_id,
                "severity": alert.severity.value,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "details": alert.details
            }
            
            message = json.dumps(notification_data).encode('utf-8')
            future = self.publisher.publish(topic_path, message)
            
            logger.info(f"Sent alert notification: {alert.alert_id}")
            
        except Exception as e:
            logger.error(f"Failed to send alert notifications for {alert.alert_id}: {e}")
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str):
        """Acknowledge an active alert"""
        try:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.state = AlertState.ACKNOWLEDGED
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.utcnow()
                
                logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
            
        except Exception as e:
            logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
    
    def resolve_alert(self, alert_id: str):
        """Resolve an active alert"""
        try:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.state = AlertState.RESOLVED
                alert.resolved_at = datetime.utcnow()
                
                # Remove from active alerts
                del self.active_alerts[alert_id]
                
                logger.info(f"Alert resolved: {alert_id}")
            
        except Exception as e:
            logger.error(f"Failed to resolve alert {alert_id}: {e}")
    
    def get_tenant_metrics(self, tenant_id: str, start_time: datetime, 
                          end_time: datetime) -> Dict[str, Any]:
        """Get monitoring metrics for a tenant"""
        try:
            metrics = {
                "tenant_id": tenant_id,
                "period": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "api_requests": {
                    "total": 10000,  # Mock data
                    "success_rate": 99.8,
                    "avg_response_time": 250,
                    "p95_response_time": 800,
                    "p99_response_time": 1500
                },
                "queries": {
                    "total": 500,
                    "success_rate": 99.2,
                    "avg_duration": 2.5,
                    "data_processed_gb": 15.7
                },
                "storage": {
                    "used_gb": 125.3,
                    "quota_gb": 1000.0,
                    "utilization_percent": 12.5
                },
                "costs": {
                    "compute_cost": 45.67,
                    "storage_cost": 12.34,
                    "network_cost": 5.89,
                    "total_cost": 63.90
                }
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get tenant metrics for {tenant_id}: {e}")
            raise


class TenantMonitoringManager:
    """Tenant-specific monitoring manager"""
    
    def __init__(self, monitoring_manager: CloudMonitoringManager, tenant_id: str):
        self.monitoring_manager = monitoring_manager
        self.tenant_id = tenant_id
    
    def setup_tenant_monitoring(self):
        """Setup monitoring for tenant"""
        try:
            # Create tenant-specific metrics
            self._create_tenant_metrics()
            
            # Create tenant-specific alert rules
            self._create_tenant_alerts()
            
            # Create tenant dashboard
            self._create_tenant_dashboard()
            
            logger.info(f"Setup monitoring for tenant: {self.tenant_id}")
            
        except Exception as e:
            logger.error(f"Failed to setup monitoring for tenant {self.tenant_id}: {e}")
            raise
    
    def _create_tenant_metrics(self):
        """Create tenant-specific custom metrics"""
        metrics = [
            MetricDefinition(
                name="user_sessions",
                display_name="Active User Sessions",
                description="Number of active user sessions",
                metric_type=MetricType.GAUGE,
                unit="sessions",
                labels=["user_id", "session_type"]
            ),
            MetricDefinition(
                name="dataset_queries",
                display_name="Dataset Queries",
                description="Number of queries executed on datasets",
                metric_type=MetricType.COUNTER,
                unit="queries",
                labels=["dataset_id", "query_type", "status"]
            ),
            MetricDefinition(
                name="visualization_renders",
                display_name="Visualization Renders",
                description="Number of visualizations rendered",
                metric_type=MetricType.COUNTER,
                unit="renders",
                labels=["visualization_type", "status"]
            )
        ]
        
        for metric in metrics:
            self.monitoring_manager.create_custom_metric(metric, self.tenant_id)
    
    def _create_tenant_alerts(self):
        """Create tenant-specific alert rules"""
        # Create notification channel first
        email_channel = self.monitoring_manager.create_notification_channel(
            NotificationChannel.EMAIL,
            {
                "display_name": f"Tenant {self.tenant_id} Email Alerts",
                "email_address": f"admin@tenant-{self.tenant_id}.com"
            },
            self.tenant_id
        )
        
        # Create alert rules
        alert_rules = [
            AlertRule(
                name=f"high_error_rate_{self.tenant_id}",
                display_name=f"High Error Rate - Tenant {self.tenant_id}",
                description="Alert when error rate exceeds 5%",
                condition=f'resource.type="cloud_run_revision" AND resource.labels.service_name="ai-analyst-api" AND metric.labels.tenant_id="{self.tenant_id}"',
                severity=AlertSeverity.HIGH,
                notification_channels=[email_channel],
                threshold_value=0.05,
                comparison="GREATER_THAN",
                duration=300
            ),
            AlertRule(
                name=f"slow_response_time_{self.tenant_id}",
                display_name=f"Slow Response Time - Tenant {self.tenant_id}",
                description="Alert when 95th percentile response time exceeds 5 seconds",
                condition=f'resource.type="cloud_run_revision" AND resource.labels.service_name="ai-analyst-api" AND metric.labels.tenant_id="{self.tenant_id}"',
                severity=AlertSeverity.MEDIUM,
                notification_channels=[email_channel],
                threshold_value=5000,
                comparison="GREATER_THAN",
                duration=600
            )
        ]
        
        for rule in alert_rules:
            self.monitoring_manager.create_alert_policy(rule, self.tenant_id)
    
    def _create_tenant_dashboard(self):
        """Create tenant-specific dashboard"""
        dashboard_config = Dashboard(
            name=f"tenant_{self.tenant_id}_dashboard",
            display_name=f"Tenant {self.tenant_id} Dashboard",
            description=f"Monitoring dashboard for tenant {self.tenant_id}",
            tenant_id=self.tenant_id,
            widgets=[
                {
                    "title": "API Request Rate",
                    "type": "line_chart",
                    "datasets": [
                        {
                            "filter": f'resource.type="cloud_run_revision" AND metric.labels.tenant_id="{self.tenant_id}"'
                        }
                    ]
                },
                {
                    "title": "Query Success Rate",
                    "type": "single_value",
                    "filter": f'resource.type="bigquery_project" AND metric.labels.tenant_id="{self.tenant_id}"'
                },
                {
                    "title": "Active Users",
                    "type": "single_value",
                    "filter": f'metric.type="custom.googleapis.com/ai_analyst/tenant_{self.tenant_id}/user_sessions"'
                }
            ],
            layout={"columns": 2, "rows": 2}
        )
        
        self.monitoring_manager.create_dashboard(dashboard_config)
    
    def record_user_session(self, user_id: str, session_type: str = "web"):
        """Record active user session metric"""
        self.monitoring_manager.write_time_series(
            f"custom.googleapis.com/ai_analyst/tenant_{self.tenant_id}/user_sessions",
            1,
            labels={"user_id": user_id, "session_type": session_type}
        )
    
    def record_query_execution(self, dataset_id: str, query_type: str, success: bool):
        """Record query execution metric"""
        self.monitoring_manager.write_time_series(
            f"custom.googleapis.com/ai_analyst/tenant_{self.tenant_id}/dataset_queries",
            1,
            labels={
                "dataset_id": dataset_id,
                "query_type": query_type,
                "status": "success" if success else "failure"
            }
        )
    
    def record_visualization_render(self, viz_type: str, success: bool):
        """Record visualization render metric"""
        self.monitoring_manager.write_time_series(
            f"custom.googleapis.com/ai_analyst/tenant_{self.tenant_id}/visualization_renders",
            1,
            labels={
                "visualization_type": viz_type,
                "status": "success" if success else "failure"
            }
        )


# Example usage
if __name__ == "__main__":
    # Initialize monitoring manager
    monitoring_manager = CloudMonitoringManager("ai-data-analyst-project")
    
    # Initialize tenant monitoring
    tenant_monitor = TenantMonitoringManager(monitoring_manager, "tenant-123")
    
    # Setup tenant monitoring
    tenant_monitor.setup_tenant_monitoring()
    
    # Record some metrics
    tenant_monitor.record_user_session("user-456", "web")
    tenant_monitor.record_query_execution("sales_data", "aggregation", True)
    tenant_monitor.record_visualization_render("bar_chart", True)
    
    # Generate SLO report
    slo_report = monitoring_manager.generate_slo_report(
        tenant_id="tenant-123",
        start_time=datetime.utcnow() - timedelta(days=7),
        end_time=datetime.utcnow()
    )
    
    print(f"SLO Report: {json.dumps(slo_report, indent=2)}")
    
    # Trigger a test alert
    alert_id = monitoring_manager.trigger_alert(
        alert_rule_name="high_error_rate_tenant-123",
        tenant_id="tenant-123",
        metric_value=0.08,
        details={"error_type": "timeout", "service": "api"}
    )
    
    print(f"Triggered alert: {alert_id}")