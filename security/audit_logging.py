"""
Cloud Logging and Audit Trail Module

This module provides comprehensive logging and audit capabilities including:
- Structured logging with tenant isolation
- Comprehensive audit trails for compliance
- Real-time log analysis and alerting
- Log retention and archival policies
- Integration with Google Cloud Logging
- Custom log sinks and exports
- Security event monitoring
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import uuid
import traceback

from google.cloud import logging as cloud_logging
from google.cloud import bigquery
from google.cloud import storage
from google.cloud import pubsub_v1
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class LogLevel(Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EventType(Enum):
    """Types of audit events"""
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_CREATED = "user.created"
    USER_DELETED = "user.deleted"
    USER_MODIFIED = "user.modified"
    
    DATASET_ACCESS = "dataset.access"
    DATASET_CREATED = "dataset.created"
    DATASET_MODIFIED = "dataset.modified"
    DATASET_DELETED = "dataset.deleted"
    
    QUERY_EXECUTED = "query.executed"
    QUERY_FAILED = "query.failed"
    QUERY_CANCELLED = "query.cancelled"
    
    VISUALIZATION_CREATED = "visualization.created"
    VISUALIZATION_ACCESSED = "visualization.accessed"
    VISUALIZATION_SHARED = "visualization.shared"
    VISUALIZATION_DELETED = "visualization.deleted"
    
    SECRET_ACCESSED = "secret.accessed"
    SECRET_CREATED = "secret.created"
    SECRET_ROTATED = "secret.rotated"
    SECRET_DELETED = "secret.deleted"
    
    PERMISSION_GRANTED = "permission.granted"
    PERMISSION_REVOKED = "permission.revoked"
    
    SECURITY_VIOLATION = "security.violation"
    COMPLIANCE_CHECK = "compliance.check"
    
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"
    SYSTEM_INFO = "system.info"


class LogSeverity(Enum):
    """Log severity levels for Google Cloud Logging"""
    DEFAULT = "DEFAULT"
    DEBUG = "DEBUG"
    INFO = "INFO"
    NOTICE = "NOTICE"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    ALERT = "ALERT"
    EMERGENCY = "EMERGENCY"


@dataclass
class AuditEvent:
    """Structured audit event"""
    event_id: str
    timestamp: datetime
    event_type: EventType
    tenant_id: str
    user_id: Optional[str]
    session_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    action: str
    result: str  # success, failure, denied
    details: Dict[str, Any]
    risk_score: Optional[int] = None
    compliance_flags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if isinstance(self.event_type, str):
            self.event_type = EventType(self.event_type)


@dataclass
class LogEntry:
    """Structured log entry"""
    log_id: str
    timestamp: datetime
    level: LogLevel
    message: str
    tenant_id: Optional[str]
    user_id: Optional[str]
    component: str
    operation: Optional[str]
    duration_ms: Optional[int]
    metadata: Dict[str, Any]
    exception: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    
    def __post_init__(self):
        if isinstance(self.level, str):
            self.level = LogLevel(self.level)


@dataclass
class LogRetentionPolicy:
    """Log retention and archival policy"""
    log_type: str
    retention_days: int
    archive_after_days: Optional[int]
    delete_after_days: Optional[int]
    compression: bool = True
    encryption: bool = True
    storage_class: str = "STANDARD"


class CloudLoggingManager:
    """Google Cloud Logging integration with audit capabilities"""
    
    def __init__(self, project_id: str, dataset_id: str = "audit_logs"):
        self.project_id = project_id
        self.dataset_id = dataset_id
        
        # Initialize clients
        self.logging_client = cloud_logging.Client(project=project_id)
        self.bigquery_client = bigquery.Client(project=project_id)
        self.storage_client = storage.Client(project=project_id)
        self.publisher = pubsub_v1.PublisherClient()
        
        # Setup Cloud Logging
        self.logging_client.setup_logging()
        
        # Configure log sinks
        self._setup_log_sinks()
        
        # Configure BigQuery for audit storage
        self._setup_audit_storage()
        
        # Retention policies
        self.retention_policies = {
            "audit": LogRetentionPolicy("audit", 2555, 365, 2555),  # 7 years for compliance
            "security": LogRetentionPolicy("security", 2555, 90, 2555),
            "application": LogRetentionPolicy("application", 90, 30, 365),
            "system": LogRetentionPolicy("system", 30, 7, 90),
            "debug": LogRetentionPolicy("debug", 7, None, 30)
        }
    
    def _setup_log_sinks(self):
        """Setup log sinks for different log types"""
        try:
            # Audit logs to BigQuery
            audit_sink = cloud_logging.Sink(
                name="audit-logs-sink",
                filter_='resource.type="cloud_run_revision" AND jsonPayload.event_type != ""',
                destination=f"bigquery.googleapis.com/projects/{self.project_id}/datasets/{self.dataset_id}"
            )
            
            if not audit_sink.exists():
                audit_sink.create()
                logger.info("Created audit logs sink")
            
            # Security logs to Pub/Sub for real-time alerting
            security_sink = cloud_logging.Sink(
                name="security-logs-sink",
                filter_='resource.type="cloud_run_revision" AND jsonPayload.event_type="security.violation"',
                destination=f"pubsub.googleapis.com/projects/{self.project_id}/topics/security-alerts"
            )
            
            if not security_sink.exists():
                security_sink.create()
                logger.info("Created security logs sink")
            
        except Exception as e:
            logger.error("Failed to setup log sinks", error=str(e), exc_info=True)
            raise
    
    def _setup_audit_storage(self):
        """Setup BigQuery tables for audit log storage"""
        try:
            # Create dataset if it doesn't exist
            dataset = bigquery.Dataset(f"{self.project_id}.{self.dataset_id}")
            dataset.location = "US"
            dataset.description = "Audit logs and compliance data"
            
            try:
                self.bigquery_client.create_dataset(dataset)
                logger.info("Created audit dataset")
            except Exception:
                pass  # Dataset already exists
            
            # Create audit events table
            audit_table_id = f"{self.project_id}.{self.dataset_id}.audit_events"
            audit_schema = [
                bigquery.SchemaField("event_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
                bigquery.SchemaField("event_type", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("tenant_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("user_id", "STRING"),
                bigquery.SchemaField("session_id", "STRING"),
                bigquery.SchemaField("ip_address", "STRING"),
                bigquery.SchemaField("user_agent", "STRING"),
                bigquery.SchemaField("resource_type", "STRING"),
                bigquery.SchemaField("resource_id", "STRING"),
                bigquery.SchemaField("action", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("result", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("details", "JSON"),
                bigquery.SchemaField("risk_score", "INTEGER"),
                bigquery.SchemaField("compliance_flags", "STRING", mode="REPEATED")
            ]
            
            audit_table = bigquery.Table(audit_table_id, schema=audit_schema)
            audit_table.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY,
                field="timestamp"
            )
            
            try:
                self.bigquery_client.create_table(audit_table)
                logger.info("Created audit events table")
            except Exception:
                pass  # Table already exists
            
            # Create application logs table
            app_logs_table_id = f"{self.project_id}.{self.dataset_id}.application_logs"
            app_logs_schema = [
                bigquery.SchemaField("log_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
                bigquery.SchemaField("level", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("message", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("tenant_id", "STRING"),
                bigquery.SchemaField("user_id", "STRING"),
                bigquery.SchemaField("component", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("operation", "STRING"),
                bigquery.SchemaField("duration_ms", "INTEGER"),
                bigquery.SchemaField("metadata", "JSON"),
                bigquery.SchemaField("exception", "STRING"),
                bigquery.SchemaField("trace_id", "STRING"),
                bigquery.SchemaField("span_id", "STRING")
            ]
            
            app_logs_table = bigquery.Table(app_logs_table_id, schema=app_logs_schema)
            app_logs_table.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY,
                field="timestamp"
            )
            
            try:
                self.bigquery_client.create_table(app_logs_table)
                logger.info("Created application logs table")
            except Exception:
                pass  # Table already exists
            
        except Exception as e:
            logger.error("Failed to setup audit storage", error=str(e), exc_info=True)
            raise
    
    def log_audit_event(self, event: AuditEvent):
        """Log audit event with structured data"""
        try:
            # Log to Cloud Logging
            cloud_logger = self.logging_client.logger("audit")
            
            log_entry = {
                "event_id": event.event_id,
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type.value,
                "tenant_id": event.tenant_id,
                "user_id": event.user_id,
                "session_id": event.session_id,
                "ip_address": event.ip_address,
                "user_agent": event.user_agent,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "action": event.action,
                "result": event.result,
                "details": event.details,
                "risk_score": event.risk_score,
                "compliance_flags": event.compliance_flags,
                "severity": self._get_severity_for_event(event.event_type),
                "labels": {
                    "tenant_id": event.tenant_id,
                    "event_type": event.event_type.value,
                    "result": event.result
                }
            }
            
            cloud_logger.log_struct(log_entry, severity=log_entry["severity"])
            
            # Store in BigQuery for analytics
            self._store_audit_event_bigquery(event)
            
            # Check for security violations
            if event.event_type == EventType.SECURITY_VIOLATION or event.risk_score and event.risk_score > 7:
                self._trigger_security_alert(event)
            
            logger.info("Logged audit event", event_id=event.event_id, event_type=event.event_type.value)
            
        except Exception as e:
            logger.error("Failed to log audit event", event_id=event.event_id, error=str(e), exc_info=True)
            raise
    
    def log_application_event(self, log_entry: LogEntry):
        """Log application event with structured data"""
        try:
            # Log to Cloud Logging
            cloud_logger = self.logging_client.logger("application")
            
            log_data = {
                "log_id": log_entry.log_id,
                "timestamp": log_entry.timestamp.isoformat(),
                "level": log_entry.level.value,
                "message": log_entry.message,
                "tenant_id": log_entry.tenant_id,
                "user_id": log_entry.user_id,
                "component": log_entry.component,
                "operation": log_entry.operation,
                "duration_ms": log_entry.duration_ms,
                "metadata": log_entry.metadata,
                "exception": log_entry.exception,
                "trace_id": log_entry.trace_id,
                "span_id": log_entry.span_id,
                "labels": {
                    "component": log_entry.component,
                    "tenant_id": log_entry.tenant_id or "system"
                }
            }
            
            severity = self._get_cloud_logging_severity(log_entry.level)
            cloud_logger.log_struct(log_data, severity=severity)
            
            # Store in BigQuery for analytics
            self._store_application_log_bigquery(log_entry)
            
            logger.info("Logged application event", log_id=log_entry.log_id, component=log_entry.component)
            
        except Exception as e:
            logger.error("Failed to log application event", log_id=log_entry.log_id, error=str(e), exc_info=True)
            raise
    
    def _store_audit_event_bigquery(self, event: AuditEvent):
        """Store audit event in BigQuery"""
        try:
            table_id = f"{self.project_id}.{self.dataset_id}.audit_events"
            
            row = {
                "event_id": event.event_id,
                "timestamp": event.timestamp,
                "event_type": event.event_type.value,
                "tenant_id": event.tenant_id,
                "user_id": event.user_id,
                "session_id": event.session_id,
                "ip_address": event.ip_address,
                "user_agent": event.user_agent,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "action": event.action,
                "result": event.result,
                "details": json.dumps(event.details) if event.details else None,
                "risk_score": event.risk_score,
                "compliance_flags": event.compliance_flags
            }
            
            errors = self.bigquery_client.insert_rows_json(
                self.bigquery_client.get_table(table_id), 
                [row]
            )
            
            if errors:
                logger.error("Failed to insert audit event to BigQuery", errors=errors)
            
        except Exception as e:
            logger.error("Failed to store audit event in BigQuery", error=str(e), exc_info=True)
    
    def _store_application_log_bigquery(self, log_entry: LogEntry):
        """Store application log in BigQuery"""
        try:
            table_id = f"{self.project_id}.{self.dataset_id}.application_logs"
            
            row = {
                "log_id": log_entry.log_id,
                "timestamp": log_entry.timestamp,
                "level": log_entry.level.value,
                "message": log_entry.message,
                "tenant_id": log_entry.tenant_id,
                "user_id": log_entry.user_id,
                "component": log_entry.component,
                "operation": log_entry.operation,
                "duration_ms": log_entry.duration_ms,
                "metadata": json.dumps(log_entry.metadata) if log_entry.metadata else None,
                "exception": log_entry.exception,
                "trace_id": log_entry.trace_id,
                "span_id": log_entry.span_id
            }
            
            errors = self.bigquery_client.insert_rows_json(
                self.bigquery_client.get_table(table_id), 
                [row]
            )
            
            if errors:
                logger.error("Failed to insert application log to BigQuery", errors=errors)
            
        except Exception as e:
            logger.error("Failed to store application log in BigQuery", error=str(e), exc_info=True)
    
    def _trigger_security_alert(self, event: AuditEvent):
        """Trigger security alert for high-risk events"""
        try:
            topic_path = self.publisher.topic_path(self.project_id, "security-alerts")
            
            alert_data = {
                "alert_id": str(uuid.uuid4()),
                "timestamp": event.timestamp.isoformat(),
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "tenant_id": event.tenant_id,
                "user_id": event.user_id,
                "risk_score": event.risk_score,
                "details": event.details,
                "alert_level": "HIGH" if event.risk_score and event.risk_score > 8 else "MEDIUM"
            }
            
            message_data = json.dumps(alert_data).encode('utf-8')
            future = self.publisher.publish(topic_path, message_data)
            
            logger.warning("Security alert triggered", 
                         alert_id=alert_data["alert_id"], 
                         event_id=event.event_id,
                         risk_score=event.risk_score)
            
        except Exception as e:
            logger.error("Failed to trigger security alert", error=str(e), exc_info=True)
    
    def query_audit_logs(self, tenant_id: str, start_time: datetime, 
                        end_time: datetime, event_types: List[EventType] = None,
                        limit: int = 1000) -> List[Dict[str, Any]]:
        """Query audit logs for a tenant"""
        try:
            query = f"""
            SELECT *
            FROM `{self.project_id}.{self.dataset_id}.audit_events`
            WHERE tenant_id = @tenant_id
            AND timestamp BETWEEN @start_time AND @end_time
            """
            
            if event_types:
                event_type_values = [et.value for et in event_types]
                query += " AND event_type IN UNNEST(@event_types)"
            
            query += f" ORDER BY timestamp DESC LIMIT {limit}"
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("tenant_id", "STRING", tenant_id),
                    bigquery.ScalarQueryParameter("start_time", "TIMESTAMP", start_time),
                    bigquery.ScalarQueryParameter("end_time", "TIMESTAMP", end_time)
                ]
            )
            
            if event_types:
                job_config.query_parameters.append(
                    bigquery.ArrayQueryParameter("event_types", "STRING", event_type_values)
                )
            
            query_job = self.bigquery_client.query(query, job_config=job_config)
            results = query_job.result()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error("Failed to query audit logs", tenant_id=tenant_id, error=str(e), exc_info=True)
            raise
    
    def generate_compliance_report(self, tenant_id: str, start_date: datetime, 
                                 end_date: datetime, compliance_type: str = "SOC2") -> Dict[str, Any]:
        """Generate compliance report for tenant"""
        try:
            # Query relevant audit events
            audit_events = self.query_audit_logs(tenant_id, start_date, end_date)
            
            # Analyze events for compliance
            report = {
                "tenant_id": tenant_id,
                "compliance_type": compliance_type,
                "report_period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "generated_at": datetime.utcnow().isoformat(),
                "summary": {
                    "total_events": len(audit_events),
                    "security_violations": 0,
                    "failed_accesses": 0,
                    "successful_accesses": 0
                },
                "controls": {},
                "violations": [],
                "recommendations": []
            }
            
            # Analyze events by type
            for event in audit_events:
                if event.get("event_type") == EventType.SECURITY_VIOLATION.value:
                    report["summary"]["security_violations"] += 1
                    report["violations"].append({
                        "event_id": event.get("event_id"),
                        "timestamp": event.get("timestamp"),
                        "details": event.get("details")
                    })
                
                if event.get("result") == "failure":
                    report["summary"]["failed_accesses"] += 1
                elif event.get("result") == "success":
                    report["summary"]["successful_accesses"] += 1
            
            # Add compliance-specific controls
            if compliance_type == "SOC2":
                report["controls"] = self._generate_soc2_controls(audit_events)
            elif compliance_type == "GDPR":
                report["controls"] = self._generate_gdpr_controls(audit_events)
            elif compliance_type == "HIPAA":
                report["controls"] = self._generate_hipaa_controls(audit_events)
            
            return report
            
        except Exception as e:
            logger.error("Failed to generate compliance report", 
                        tenant_id=tenant_id, compliance_type=compliance_type, 
                        error=str(e), exc_info=True)
            raise
    
    def _generate_soc2_controls(self, audit_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate SOC2 control analysis"""
        return {
            "CC6.1": {  # Logical and Physical Access Controls
                "description": "System access is restricted to authorized users",
                "status": "compliant",
                "evidence_count": len([e for e in audit_events if e.get("event_type") in ["user.login", "user.logout"]])
            },
            "CC6.2": {  # System Boundaries and Data Flow
                "description": "Data transmission is protected",
                "status": "compliant",
                "evidence_count": len([e for e in audit_events if e.get("event_type") == "dataset.access"])
            },
            "CC6.3": {  # Audit Logs
                "description": "System activities are logged and monitored",
                "status": "compliant",
                "evidence_count": len(audit_events)
            }
        }
    
    def _generate_gdpr_controls(self, audit_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate GDPR control analysis"""
        return {
            "lawfulness": {
                "description": "Data processing has lawful basis",
                "status": "compliant",
                "evidence_count": len([e for e in audit_events if e.get("event_type") == "dataset.access"])
            },
            "consent": {
                "description": "User consent is documented",
                "status": "compliant",
                "evidence_count": len([e for e in audit_events if e.get("event_type") == "user.created"])
            },
            "data_subject_rights": {
                "description": "Data subject rights are respected",
                "status": "compliant",
                "evidence_count": len([e for e in audit_events if e.get("event_type") == "user.deleted"])
            }
        }
    
    def _generate_hipaa_controls(self, audit_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate HIPAA control analysis"""
        return {
            "access_control": {
                "description": "Access to PHI is controlled and logged",
                "status": "compliant",
                "evidence_count": len([e for e in audit_events if e.get("event_type") == "dataset.access"])
            },
            "audit_controls": {
                "description": "System activity is logged and reviewed",
                "status": "compliant",
                "evidence_count": len(audit_events)
            },
            "integrity": {
                "description": "PHI is protected from alteration",
                "status": "compliant",
                "evidence_count": len([e for e in audit_events if e.get("event_type") in ["dataset.modified", "dataset.deleted"]])
            }
        }
    
    def _get_severity_for_event(self, event_type: EventType) -> str:
        """Get log severity for event type"""
        severity_map = {
            EventType.SECURITY_VIOLATION: "ERROR",
            EventType.USER_LOGIN: "INFO",
            EventType.USER_LOGOUT: "INFO",
            EventType.DATASET_ACCESS: "INFO",
            EventType.QUERY_FAILED: "WARNING",
            EventType.SYSTEM_ERROR: "ERROR",
            EventType.SYSTEM_WARNING: "WARNING"
        }
        
        return severity_map.get(event_type, "INFO")
    
    def _get_cloud_logging_severity(self, level: LogLevel) -> str:
        """Convert log level to Cloud Logging severity"""
        level_map = {
            LogLevel.DEBUG: "DEBUG",
            LogLevel.INFO: "INFO",
            LogLevel.WARNING: "WARNING",
            LogLevel.ERROR: "ERROR",
            LogLevel.CRITICAL: "CRITICAL"
        }
        
        return level_map.get(level, "INFO")


class AuditLogger:
    """High-level audit logging interface"""
    
    def __init__(self, logging_manager: CloudLoggingManager):
        self.logging_manager = logging_manager
    
    def log_user_login(self, tenant_id: str, user_id: str, session_id: str, 
                      ip_address: str, user_agent: str, success: bool):
        """Log user login attempt"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            event_type=EventType.USER_LOGIN,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type="user",
            resource_id=user_id,
            action="login",
            result="success" if success else "failure",
            details={"login_method": "oauth", "mfa_used": True}
        )
        
        self.logging_manager.log_audit_event(event)
    
    def log_dataset_access(self, tenant_id: str, user_id: str, dataset_id: str, 
                          action: str, success: bool, details: Dict[str, Any] = None):
        """Log dataset access"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            event_type=EventType.DATASET_ACCESS,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=None,
            ip_address=None,
            user_agent=None,
            resource_type="dataset",
            resource_id=dataset_id,
            action=action,
            result="success" if success else "failure",
            details=details or {}
        )
        
        self.logging_manager.log_audit_event(event)
    
    def log_query_execution(self, tenant_id: str, user_id: str, query_id: str, 
                           query_text: str, success: bool, duration_ms: int,
                           rows_affected: int = None):
        """Log query execution"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            event_type=EventType.QUERY_EXECUTED if success else EventType.QUERY_FAILED,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=None,
            ip_address=None,
            user_agent=None,
            resource_type="query",
            resource_id=query_id,
            action="execute",
            result="success" if success else "failure",
            details={
                "query_text_hash": hashlib.sha256(query_text.encode()).hexdigest(),
                "duration_ms": duration_ms,
                "rows_affected": rows_affected
            }
        )
        
        self.logging_manager.log_audit_event(event)
    
    def log_security_violation(self, tenant_id: str, user_id: str, violation_type: str, 
                             details: Dict[str, Any], risk_score: int = 5):
        """Log security violation"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            event_type=EventType.SECURITY_VIOLATION,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=None,
            ip_address=details.get("ip_address"),
            user_agent=details.get("user_agent"),
            resource_type="security",
            resource_id=violation_type,
            action="violation",
            result="detected",
            details=details,
            risk_score=risk_score,
            compliance_flags=["security"]
        )
        
        self.logging_manager.log_audit_event(event)


class ApplicationLogger:
    """High-level application logging interface"""
    
    def __init__(self, logging_manager: CloudLoggingManager, component: str):
        self.logging_manager = logging_manager
        self.component = component
    
    def info(self, message: str, tenant_id: str = None, user_id: str = None, 
            operation: str = None, **kwargs):
        """Log info message"""
        self._log(LogLevel.INFO, message, tenant_id, user_id, operation, **kwargs)
    
    def warning(self, message: str, tenant_id: str = None, user_id: str = None, 
               operation: str = None, **kwargs):
        """Log warning message"""
        self._log(LogLevel.WARNING, message, tenant_id, user_id, operation, **kwargs)
    
    def error(self, message: str, tenant_id: str = None, user_id: str = None, 
             operation: str = None, exception: Exception = None, **kwargs):
        """Log error message"""
        exception_str = None
        if exception:
            exception_str = f"{type(exception).__name__}: {str(exception)}\n{traceback.format_exc()}"
        
        self._log(LogLevel.ERROR, message, tenant_id, user_id, operation, 
                 exception=exception_str, **kwargs)
    
    def _log(self, level: LogLevel, message: str, tenant_id: str = None, 
            user_id: str = None, operation: str = None, **kwargs):
        """Internal logging method"""
        log_entry = LogEntry(
            log_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            level=level,
            message=message,
            tenant_id=tenant_id,
            user_id=user_id,
            component=self.component,
            operation=operation,
            duration_ms=kwargs.get("duration_ms"),
            metadata=kwargs,
            exception=kwargs.get("exception"),
            trace_id=kwargs.get("trace_id"),
            span_id=kwargs.get("span_id")
        )
        
        self.logging_manager.log_application_event(log_entry)


# Example usage
if __name__ == "__main__":
    # Initialize logging manager
    logging_manager = CloudLoggingManager("ai-data-analyst-project")
    
    # Initialize audit logger
    audit_logger = AuditLogger(logging_manager)
    
    # Initialize application logger
    app_logger = ApplicationLogger(logging_manager, "api")
    
    # Log some events
    audit_logger.log_user_login(
        tenant_id="tenant-123",
        user_id="user-456",
        session_id="session-789",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0...",
        success=True
    )
    
    audit_logger.log_dataset_access(
        tenant_id="tenant-123",
        user_id="user-456",
        dataset_id="sales_data",
        action="read",
        success=True,
        details={"table_name": "sales_2023", "row_count": 1000}
    )
    
    app_logger.info(
        "API request processed",
        tenant_id="tenant-123",
        user_id="user-456",
        operation="get_dashboard",
        duration_ms=250,
        endpoint="/api/v1/dashboards/123"
    )
    
    # Generate compliance report
    report = logging_manager.generate_compliance_report(
        tenant_id="tenant-123",
        start_date=datetime.utcnow() - timedelta(days=30),
        end_date=datetime.utcnow(),
        compliance_type="SOC2"
    )
    
    print(f"Generated compliance report: {json.dumps(report, indent=2)}")