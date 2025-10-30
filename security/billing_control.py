"""
Billing Metering and Cost Control Module

This module provides comprehensive billing and cost management including:
- Multi-tenant cost allocation and tracking
- Resource quotas and usage monitoring
- Budget controls and alerting
- Cost optimization recommendations
- Integration with Google Cloud Billing
- Chargeback and showback reporting
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import uuid
import math

from google.cloud import billing_v1
from google.cloud import monitoring_v3
from google.cloud import bigquery
from google.cloud import resource_manager
from google.cloud import pubsub_v1

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Types of billable resources"""
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORK = "network"
    BIGQUERY = "bigquery"
    VERTEX_AI = "vertex_ai"
    CLOUD_FUNCTIONS = "cloud_functions"
    CLOUD_RUN = "cloud_run"
    CLOUD_SQL = "cloud_sql"
    PUBSUB = "pubsub"
    SECRET_MANAGER = "secret_manager"


class BillingPeriod(Enum):
    """Billing period types"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class CostAllocationMethod(Enum):
    """Cost allocation methods"""
    EQUAL_SPLIT = "equal_split"
    USAGE_BASED = "usage_based"
    RESOURCE_BASED = "resource_based"
    WEIGHTED = "weighted"


class BudgetAlertType(Enum):
    """Budget alert types"""
    ACTUAL_SPEND = "actual_spend"
    FORECASTED_SPEND = "forecasted_spend"
    QUOTA_UTILIZATION = "quota_utilization"


@dataclass
class ResourceQuota:
    """Resource quota definition"""
    tenant_id: str
    resource_type: ResourceType
    quota_value: float
    quota_unit: str
    current_usage: float = 0.0
    utilization_percent: float = 0.0
    last_updated: Optional[datetime] = None
    soft_limit_percent: float = 80.0
    hard_limit_percent: float = 95.0
    
    def __post_init__(self):
        if self.quota_value > 0:
            self.utilization_percent = (self.current_usage / self.quota_value) * 100


@dataclass
class CostCenter:
    """Cost center for allocation"""
    id: str
    name: str
    description: str
    tenant_id: str
    allocation_weights: Dict[ResourceType, float]
    budget_limit: Optional[float] = None
    current_spend: float = 0.0
    
    def __post_init__(self):
        if isinstance(list(self.allocation_weights.keys())[0], str):
            # Convert string keys to ResourceType enum
            new_weights = {}
            for k, v in self.allocation_weights.items():
                if isinstance(k, str):
                    new_weights[ResourceType(k)] = v
                else:
                    new_weights[k] = v
            self.allocation_weights = new_weights


@dataclass
class Budget:
    """Budget configuration"""
    id: str
    name: str
    description: str
    tenant_id: str
    amount: float
    currency: str
    period: BillingPeriod
    start_date: datetime
    end_date: Optional[datetime]
    alert_thresholds: List[float]  # Percentage thresholds for alerts
    current_spend: float = 0.0
    forecasted_spend: float = 0.0
    remaining_budget: float = 0.0
    
    def __post_init__(self):
        self.remaining_budget = max(0, self.amount - self.current_spend)


@dataclass
class BillingEvent:
    """Individual billing event"""
    event_id: str
    timestamp: datetime
    tenant_id: str
    user_id: Optional[str]
    resource_type: ResourceType
    resource_id: str
    service_name: str
    sku_description: str
    quantity: float
    unit: str
    unit_price: float
    total_cost: float
    currency: str
    project_id: str
    location: str
    labels: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        if isinstance(self.resource_type, str):
            self.resource_type = ResourceType(self.resource_type)


@dataclass
class CostAllocation:
    """Cost allocation result"""
    tenant_id: str
    cost_center_id: str
    resource_type: ResourceType
    allocated_cost: float
    allocation_method: CostAllocationMethod
    allocation_percentage: float
    billing_period: str
    created_at: datetime


class BillingManager:
    """Comprehensive billing and cost management"""
    
    def __init__(self, project_id: str, billing_account_id: str):
        self.project_id = project_id
        self.billing_account_id = billing_account_id
        
        # Initialize clients
        self.billing_client = billing_v1.CloudBillingClient()
        self.catalog_client = billing_v1.CloudCatalogClient()
        self.monitoring_client = monitoring_v3.MetricServiceClient()
        self.bigquery_client = bigquery.Client(project=project_id)
        self.publisher = pubsub_v1.PublisherClient()
        
        # Setup billing data export
        self._setup_billing_export()
        
        # Default quotas for new tenants
        self.default_quotas = {
            ResourceType.COMPUTE: ResourceQuota("", ResourceType.COMPUTE, 100.0, "vCPU-hours"),
            ResourceType.STORAGE: ResourceQuota("", ResourceType.STORAGE, 1000.0, "GB"),
            ResourceType.BIGQUERY: ResourceQuota("", ResourceType.BIGQUERY, 10.0, "TB"),
            ResourceType.VERTEX_AI: ResourceQuota("", ResourceType.VERTEX_AI, 50.0, "training-hours"),
            ResourceType.NETWORK: ResourceQuota("", ResourceType.NETWORK, 100.0, "GB")
        }
    
    def _setup_billing_export(self):
        """Setup BigQuery export for billing data"""
        try:
            # Create billing dataset
            dataset_id = f"{self.project_id}.billing_data"
            dataset = bigquery.Dataset(dataset_id)
            dataset.location = "US"
            dataset.description = "Billing and cost allocation data"
            
            try:
                self.bigquery_client.create_dataset(dataset)
                logger.info("Created billing dataset")
            except Exception:
                pass  # Dataset already exists
            
            # Create billing events table
            table_id = f"{self.project_id}.billing_data.billing_events"
            schema = [
                bigquery.SchemaField("event_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
                bigquery.SchemaField("tenant_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("user_id", "STRING"),
                bigquery.SchemaField("resource_type", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("resource_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("service_name", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("sku_description", "STRING"),
                bigquery.SchemaField("quantity", "FLOAT64", mode="REQUIRED"),
                bigquery.SchemaField("unit", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("unit_price", "FLOAT64", mode="REQUIRED"),
                bigquery.SchemaField("total_cost", "FLOAT64", mode="REQUIRED"),
                bigquery.SchemaField("currency", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("project_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("location", "STRING"),
                bigquery.SchemaField("labels", "JSON")
            ]
            
            table = bigquery.Table(table_id, schema=schema)
            table.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY,
                field="timestamp"
            )
            
            try:
                self.bigquery_client.create_table(table)
                logger.info("Created billing events table")
            except Exception:
                pass  # Table already exists
            
        except Exception as e:
            logger.error(f"Failed to setup billing export: {e}")
            raise
    
    def create_tenant_budget(self, tenant_id: str, budget_config: Dict[str, Any]) -> Budget:
        """Create budget for tenant"""
        try:
            budget = Budget(
                id=str(uuid.uuid4()),
                name=budget_config["name"],
                description=budget_config.get("description", ""),
                tenant_id=tenant_id,
                amount=budget_config["amount"],
                currency=budget_config.get("currency", "USD"),
                period=BillingPeriod(budget_config.get("period", "monthly")),
                start_date=budget_config.get("start_date", datetime.utcnow().replace(day=1)),
                end_date=budget_config.get("end_date"),
                alert_thresholds=budget_config.get("alert_thresholds", [50, 80, 90, 100])
            )
            
            # Create Cloud Billing budget
            self._create_cloud_budget(budget)
            
            logger.info(f"Created budget for tenant {tenant_id}: {budget.name}")
            return budget
            
        except Exception as e:
            logger.error(f"Failed to create budget for tenant {tenant_id}: {e}")
            raise
    
    def _create_cloud_budget(self, budget: Budget):
        """Create budget in Google Cloud Billing"""
        try:
            # This would create an actual Cloud Billing budget
            # For now, we'll store the configuration
            
            budget_data = {
                "display_name": budget.name,
                "budget_filter": {
                    "projects": [f"projects/{self.project_id}"],
                    "labels": [{"key": "tenant_id", "value": budget.tenant_id}]
                },
                "amount": {
                    "specified_amount": {
                        "currency_code": budget.currency,
                        "units": str(int(budget.amount))
                    }
                },
                "threshold_rules": [
                    {
                        "threshold_percent": threshold / 100,
                        "spend_basis": "CURRENT_SPEND"
                    }
                    for threshold in budget.alert_thresholds
                ]
            }
            
            logger.info(f"Would create Cloud Billing budget: {budget_data}")
            
        except Exception as e:
            logger.error(f"Failed to create Cloud Billing budget: {e}")
            raise
    
    def set_resource_quotas(self, tenant_id: str, quotas: Dict[ResourceType, ResourceQuota]):
        """Set resource quotas for tenant"""
        try:
            for resource_type, quota in quotas.items():
                quota.tenant_id = tenant_id
                quota.last_updated = datetime.utcnow()
                
                # Store quota configuration
                self._store_quota(quota)
                
                # Create monitoring alerts for quota utilization
                self._create_quota_alerts(quota)
            
            logger.info(f"Set resource quotas for tenant {tenant_id}")
            
        except Exception as e:
            logger.error(f"Failed to set resource quotas for tenant {tenant_id}: {e}")
            raise
    
    def _store_quota(self, quota: ResourceQuota):
        """Store quota configuration"""
        try:
            # Store in BigQuery for analytics
            table_id = f"{self.project_id}.billing_data.resource_quotas"
            
            # Create table if it doesn't exist
            schema = [
                bigquery.SchemaField("tenant_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("resource_type", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("quota_value", "FLOAT64", mode="REQUIRED"),
                bigquery.SchemaField("quota_unit", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("current_usage", "FLOAT64"),
                bigquery.SchemaField("utilization_percent", "FLOAT64"),
                bigquery.SchemaField("last_updated", "TIMESTAMP"),
                bigquery.SchemaField("soft_limit_percent", "FLOAT64"),
                bigquery.SchemaField("hard_limit_percent", "FLOAT64")
            ]
            
            table = bigquery.Table(table_id, schema=schema)
            
            try:
                self.bigquery_client.create_table(table)
                logger.info("Created resource quotas table")
            except Exception:
                pass  # Table already exists
            
            # Insert quota record
            row = {
                "tenant_id": quota.tenant_id,
                "resource_type": quota.resource_type.value,
                "quota_value": quota.quota_value,
                "quota_unit": quota.quota_unit,
                "current_usage": quota.current_usage,
                "utilization_percent": quota.utilization_percent,
                "last_updated": quota.last_updated,
                "soft_limit_percent": quota.soft_limit_percent,
                "hard_limit_percent": quota.hard_limit_percent
            }
            
            errors = self.bigquery_client.insert_rows_json(
                self.bigquery_client.get_table(table_id),
                [row]
            )
            
            if errors:
                logger.error(f"Failed to store quota: {errors}")
            
        except Exception as e:
            logger.error(f"Failed to store quota: {e}")
            raise
    
    def _create_quota_alerts(self, quota: ResourceQuota):
        """Create monitoring alerts for quota utilization"""
        try:
            # This would create actual monitoring alerts
            # For now, we'll log the configuration
            
            alert_config = {
                "name": f"quota_alert_{quota.tenant_id}_{quota.resource_type.value}",
                "condition": f"quota_utilization > {quota.soft_limit_percent}",
                "threshold": quota.soft_limit_percent,
                "severity": "warning"
            }
            
            logger.info(f"Would create quota alert: {alert_config}")
            
        except Exception as e:
            logger.error(f"Failed to create quota alerts: {e}")
    
    def record_billing_event(self, event: BillingEvent):
        """Record a billing event"""
        try:
            # Store in BigQuery
            table_id = f"{self.project_id}.billing_data.billing_events"
            
            row = {
                "event_id": event.event_id,
                "timestamp": event.timestamp,
                "tenant_id": event.tenant_id,
                "user_id": event.user_id,
                "resource_type": event.resource_type.value,
                "resource_id": event.resource_id,
                "service_name": event.service_name,
                "sku_description": event.sku_description,
                "quantity": event.quantity,
                "unit": event.unit,
                "unit_price": event.unit_price,
                "total_cost": event.total_cost,
                "currency": event.currency,
                "project_id": event.project_id,
                "location": event.location,
                "labels": json.dumps(event.labels)
            }
            
            errors = self.bigquery_client.insert_rows_json(
                self.bigquery_client.get_table(table_id),
                [row]
            )
            
            if errors:
                logger.error(f"Failed to record billing event: {errors}")
            else:
                logger.debug(f"Recorded billing event: {event.event_id}")
            
            # Update tenant costs
            self._update_tenant_costs(event.tenant_id, event.total_cost)
            
            # Check budget alerts
            self._check_budget_alerts(event.tenant_id)
            
        except Exception as e:
            logger.error(f"Failed to record billing event: {e}")
            raise
    
    def allocate_costs(self, cost_centers: List[CostCenter], 
                      allocation_method: CostAllocationMethod = CostAllocationMethod.USAGE_BASED,
                      billing_period: str = "monthly") -> List[CostAllocation]:
        """Allocate costs across cost centers"""
        try:
            allocations = []
            
            # Get total costs by resource type for the period
            total_costs = self._get_period_costs(billing_period)
            
            for resource_type, total_cost in total_costs.items():
                if total_cost <= 0:
                    continue
                
                # Calculate allocation weights
                total_weight = sum(
                    cc.allocation_weights.get(resource_type, 0.0) 
                    for cc in cost_centers
                )
                
                if total_weight <= 0:
                    continue
                
                # Allocate costs
                for cost_center in cost_centers:
                    weight = cost_center.allocation_weights.get(resource_type, 0.0)
                    if weight <= 0:
                        continue
                    
                    allocation_percentage = (weight / total_weight) * 100
                    allocated_cost = total_cost * (weight / total_weight)
                    
                    allocation = CostAllocation(
                        tenant_id=cost_center.tenant_id,
                        cost_center_id=cost_center.id,
                        resource_type=resource_type,
                        allocated_cost=allocated_cost,
                        allocation_method=allocation_method,
                        allocation_percentage=allocation_percentage,
                        billing_period=billing_period,
                        created_at=datetime.utcnow()
                    )
                    
                    allocations.append(allocation)
                    
                    # Update cost center spend
                    cost_center.current_spend += allocated_cost
            
            # Store allocations
            self._store_cost_allocations(allocations)
            
            logger.info(f"Allocated costs for {len(cost_centers)} cost centers")
            return allocations
            
        except Exception as e:
            logger.error(f"Failed to allocate costs: {e}")
            raise
    
    def _get_period_costs(self, billing_period: str) -> Dict[ResourceType, float]:
        """Get total costs by resource type for billing period"""
        try:
            query = f"""
            SELECT 
                resource_type,
                SUM(total_cost) as total_cost
            FROM `{self.project_id}.billing_data.billing_events`
            WHERE DATE(timestamp) = CURRENT_DATE()
            GROUP BY resource_type
            """
            
            if billing_period == "monthly":
                query = query.replace(
                    "DATE(timestamp) = CURRENT_DATE()",
                    "DATE_TRUNC(DATE(timestamp), MONTH) = DATE_TRUNC(CURRENT_DATE(), MONTH)"
                )
            elif billing_period == "weekly":
                query = query.replace(
                    "DATE(timestamp) = CURRENT_DATE()",
                    "DATE_TRUNC(DATE(timestamp), WEEK) = DATE_TRUNC(CURRENT_DATE(), WEEK)"
                )
            
            query_job = self.bigquery_client.query(query)
            results = query_job.result()
            
            costs = {}
            for row in results:
                resource_type = ResourceType(row.resource_type)
                costs[resource_type] = float(row.total_cost)
            
            return costs
            
        except Exception as e:
            logger.error(f"Failed to get period costs: {e}")
            return {}
    
    def _store_cost_allocations(self, allocations: List[CostAllocation]):
        """Store cost allocations in BigQuery"""
        try:
            table_id = f"{self.project_id}.billing_data.cost_allocations"
            
            # Create table if it doesn't exist
            schema = [
                bigquery.SchemaField("tenant_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("cost_center_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("resource_type", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("allocated_cost", "FLOAT64", mode="REQUIRED"),
                bigquery.SchemaField("allocation_method", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("allocation_percentage", "FLOAT64"),
                bigquery.SchemaField("billing_period", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED")
            ]
            
            table = bigquery.Table(table_id, schema=schema)
            table.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY,
                field="created_at"
            )
            
            try:
                self.bigquery_client.create_table(table)
                logger.info("Created cost allocations table")
            except Exception:
                pass  # Table already exists
            
            # Insert allocation records
            rows = []
            for allocation in allocations:
                row = {
                    "tenant_id": allocation.tenant_id,
                    "cost_center_id": allocation.cost_center_id,
                    "resource_type": allocation.resource_type.value,
                    "allocated_cost": allocation.allocated_cost,
                    "allocation_method": allocation.allocation_method.value,
                    "allocation_percentage": allocation.allocation_percentage,
                    "billing_period": allocation.billing_period,
                    "created_at": allocation.created_at
                }
                rows.append(row)
            
            errors = self.bigquery_client.insert_rows_json(
                self.bigquery_client.get_table(table_id),
                rows
            )
            
            if errors:
                logger.error(f"Failed to store cost allocations: {errors}")
            
        except Exception as e:
            logger.error(f"Failed to store cost allocations: {e}")
    
    def generate_cost_report(self, tenant_id: str, start_date: datetime, 
                           end_date: datetime) -> Dict[str, Any]:
        """Generate comprehensive cost report for tenant"""
        try:
            # Query billing data
            query = f"""
            SELECT 
                resource_type,
                service_name,
                SUM(total_cost) as total_cost,
                SUM(quantity) as total_quantity,
                AVG(unit_price) as avg_unit_price,
                COUNT(*) as event_count
            FROM `{self.project_id}.billing_data.billing_events`
            WHERE tenant_id = @tenant_id
            AND timestamp BETWEEN @start_date AND @end_date
            GROUP BY resource_type, service_name
            ORDER BY total_cost DESC
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("tenant_id", "STRING", tenant_id),
                    bigquery.ScalarQueryParameter("start_date", "TIMESTAMP", start_date),
                    bigquery.ScalarQueryParameter("end_date", "TIMESTAMP", end_date)
                ]
            )
            
            query_job = self.bigquery_client.query(query, job_config=job_config)
            results = query_job.result()
            
            # Build report
            report = {
                "tenant_id": tenant_id,
                "report_period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "generated_at": datetime.utcnow().isoformat(),
                "summary": {
                    "total_cost": 0.0,
                    "total_events": 0,
                    "cost_by_resource": {},
                    "cost_by_service": {}
                },
                "details": [],
                "recommendations": []
            }
            
            # Process results
            for row in results:
                cost_detail = {
                    "resource_type": row.resource_type,
                    "service_name": row.service_name,
                    "total_cost": float(row.total_cost),
                    "total_quantity": float(row.total_quantity),
                    "avg_unit_price": float(row.avg_unit_price),
                    "event_count": int(row.event_count)
                }
                
                report["details"].append(cost_detail)
                report["summary"]["total_cost"] += cost_detail["total_cost"]
                report["summary"]["total_events"] += cost_detail["event_count"]
                
                # Aggregate by resource type
                if row.resource_type not in report["summary"]["cost_by_resource"]:
                    report["summary"]["cost_by_resource"][row.resource_type] = 0.0
                report["summary"]["cost_by_resource"][row.resource_type] += cost_detail["total_cost"]
                
                # Aggregate by service
                if row.service_name not in report["summary"]["cost_by_service"]:
                    report["summary"]["cost_by_service"][row.service_name] = 0.0
                report["summary"]["cost_by_service"][row.service_name] += cost_detail["total_cost"]
            
            # Add cost optimization recommendations
            report["recommendations"] = self._generate_cost_recommendations(report)
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate cost report for tenant {tenant_id}: {e}")
            raise
    
    def _generate_cost_recommendations(self, cost_report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate cost optimization recommendations"""
        recommendations = []
        
        # Analyze cost patterns
        total_cost = cost_report["summary"]["total_cost"]
        cost_by_resource = cost_report["summary"]["cost_by_resource"]
        
        # High compute costs recommendation
        compute_cost = cost_by_resource.get("compute", 0.0)
        if compute_cost > total_cost * 0.5:
            recommendations.append({
                "type": "cost_optimization",
                "priority": "high",
                "title": "High Compute Costs Detected",
                "description": f"Compute costs represent {(compute_cost/total_cost)*100:.1f}% of total spend",
                "recommendation": "Consider using preemptible instances or rightsizing compute resources",
                "potential_savings": compute_cost * 0.3
            })
        
        # High storage costs recommendation
        storage_cost = cost_by_resource.get("storage", 0.0)
        if storage_cost > total_cost * 0.3:
            recommendations.append({
                "type": "cost_optimization",
                "priority": "medium",
                "title": "Storage Optimization Opportunity",
                "description": f"Storage costs are {(storage_cost/total_cost)*100:.1f}% of total spend",
                "recommendation": "Review data lifecycle policies and consider cold storage for infrequently accessed data",
                "potential_savings": storage_cost * 0.2
            })
        
        # BigQuery optimization
        bigquery_cost = cost_by_resource.get("bigquery", 0.0)
        if bigquery_cost > total_cost * 0.2:
            recommendations.append({
                "type": "query_optimization",
                "priority": "medium",
                "title": "BigQuery Cost Optimization",
                "description": f"BigQuery costs are ${bigquery_cost:.2f}",
                "recommendation": "Optimize queries, use partitioned tables, and consider BigQuery slots for predictable workloads",
                "potential_savings": bigquery_cost * 0.25
            })
        
        return recommendations
    
    def update_usage_metrics(self, tenant_id: str, resource_type: ResourceType, 
                           usage_value: float):
        """Update resource usage metrics for quota tracking"""
        try:
            # Get current quota
            quota = self._get_tenant_quota(tenant_id, resource_type)
            if not quota:
                return
            
            # Update usage
            quota.current_usage = usage_value
            quota.utilization_percent = (usage_value / quota.quota_value) * 100 if quota.quota_value > 0 else 0
            quota.last_updated = datetime.utcnow()
            
            # Store updated quota
            self._store_quota(quota)
            
            # Check for quota violations
            if quota.utilization_percent >= quota.hard_limit_percent:
                self._trigger_quota_alert(quota, "hard_limit_exceeded")
            elif quota.utilization_percent >= quota.soft_limit_percent:
                self._trigger_quota_alert(quota, "soft_limit_exceeded")
            
            logger.debug(f"Updated usage for tenant {tenant_id}, {resource_type.value}: {usage_value}")
            
        except Exception as e:
            logger.error(f"Failed to update usage metrics: {e}")
    
    def _get_tenant_quota(self, tenant_id: str, resource_type: ResourceType) -> Optional[ResourceQuota]:
        """Get tenant's resource quota"""
        try:
            query = f"""
            SELECT *
            FROM `{self.project_id}.billing_data.resource_quotas`
            WHERE tenant_id = @tenant_id AND resource_type = @resource_type
            ORDER BY last_updated DESC
            LIMIT 1
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("tenant_id", "STRING", tenant_id),
                    bigquery.ScalarQueryParameter("resource_type", "STRING", resource_type.value)
                ]
            )
            
            query_job = self.bigquery_client.query(query, job_config=job_config)
            results = query_job.result()
            
            for row in results:
                return ResourceQuota(
                    tenant_id=row.tenant_id,
                    resource_type=ResourceType(row.resource_type),
                    quota_value=float(row.quota_value),
                    quota_unit=row.quota_unit,
                    current_usage=float(row.current_usage or 0),
                    last_updated=row.last_updated,
                    soft_limit_percent=float(row.soft_limit_percent or 80),
                    hard_limit_percent=float(row.hard_limit_percent or 95)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get tenant quota: {e}")
            return None
    
    def _update_tenant_costs(self, tenant_id: str, cost: float):
        """Update tenant's current spending"""
        # This would update the tenant's current cost tracking
        pass
    
    def _check_budget_alerts(self, tenant_id: str):
        """Check if budget alerts should be triggered"""
        # This would check current spend against budget thresholds
        pass
    
    def _trigger_quota_alert(self, quota: ResourceQuota, alert_type: str):
        """Trigger quota utilization alert"""
        try:
            alert_data = {
                "alert_id": str(uuid.uuid4()),
                "tenant_id": quota.tenant_id,
                "resource_type": quota.resource_type.value,
                "alert_type": alert_type,
                "utilization_percent": quota.utilization_percent,
                "quota_value": quota.quota_value,
                "current_usage": quota.current_usage,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Publish alert
            topic_path = self.publisher.topic_path(self.project_id, "quota-alerts")
            message = json.dumps(alert_data).encode('utf-8')
            future = self.publisher.publish(topic_path, message)
            
            logger.warning(f"Quota alert triggered: {alert_data}")
            
        except Exception as e:
            logger.error(f"Failed to trigger quota alert: {e}")


class TenantBillingManager:
    """Tenant-specific billing manager"""
    
    def __init__(self, billing_manager: BillingManager, tenant_id: str):
        self.billing_manager = billing_manager
        self.tenant_id = tenant_id
    
    def setup_tenant_billing(self, budget_amount: float = 1000.0):
        """Setup billing for tenant"""
        try:
            # Create default budget
            budget = self.billing_manager.create_tenant_budget(
                self.tenant_id,
                {
                    "name": f"Tenant {self.tenant_id} Monthly Budget",
                    "amount": budget_amount,
                    "period": "monthly",
                    "alert_thresholds": [50, 75, 90, 100]
                }
            )
            
            # Set default quotas
            default_quotas = {}
            for resource_type, default_quota in self.billing_manager.default_quotas.items():
                quota = ResourceQuota(
                    tenant_id=self.tenant_id,
                    resource_type=resource_type,
                    quota_value=default_quota.quota_value,
                    quota_unit=default_quota.quota_unit
                )
                default_quotas[resource_type] = quota
            
            self.billing_manager.set_resource_quotas(self.tenant_id, default_quotas)
            
            logger.info(f"Setup billing for tenant: {self.tenant_id}")
            
        except Exception as e:
            logger.error(f"Failed to setup billing for tenant {self.tenant_id}: {e}")
            raise
    
    def record_api_usage(self, endpoint: str, requests_count: int, compute_time_ms: int):
        """Record API usage for billing"""
        # Calculate costs based on usage
        request_cost = requests_count * 0.001  # $0.001 per request
        compute_cost = (compute_time_ms / 1000) * 0.01  # $0.01 per second
        
        event = BillingEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            tenant_id=self.tenant_id,
            user_id=None,
            resource_type=ResourceType.COMPUTE,
            resource_id=endpoint,
            service_name="ai-analyst-api",
            sku_description="API Request Processing",
            quantity=requests_count,
            unit="requests",
            unit_price=0.001,
            total_cost=request_cost + compute_cost,
            currency="USD",
            project_id=self.billing_manager.project_id,
            location="us-central1"
        )
        
        self.billing_manager.record_billing_event(event)
    
    def record_query_usage(self, query_id: str, bytes_processed: int, duration_ms: int):
        """Record BigQuery usage for billing"""
        # Calculate BigQuery costs
        tb_processed = bytes_processed / (1024**4)  # Convert to TB
        query_cost = tb_processed * 5.0  # $5 per TB
        
        event = BillingEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            tenant_id=self.tenant_id,
            user_id=None,
            resource_type=ResourceType.BIGQUERY,
            resource_id=query_id,
            service_name="bigquery",
            sku_description="BigQuery Query Processing",
            quantity=tb_processed,
            unit="TB",
            unit_price=5.0,
            total_cost=query_cost,
            currency="USD",
            project_id=self.billing_manager.project_id,
            location="us-central1"
        )
        
        self.billing_manager.record_billing_event(event)
        
        # Update usage quota
        self.billing_manager.update_usage_metrics(
            self.tenant_id, 
            ResourceType.BIGQUERY, 
            tb_processed
        )
    
    def get_current_spending(self) -> Dict[str, float]:
        """Get current spending summary"""
        end_date = datetime.utcnow()
        start_date = end_date.replace(day=1)  # Start of current month
        
        cost_report = self.billing_manager.generate_cost_report(
            self.tenant_id, start_date, end_date
        )
        
        return {
            "total_cost": cost_report["summary"]["total_cost"],
            "cost_by_resource": cost_report["summary"]["cost_by_resource"],
            "period": "current_month"
        }


# Example usage
if __name__ == "__main__":
    # Initialize billing manager
    billing_manager = BillingManager("ai-data-analyst-project", "billing-account-123")
    
    # Initialize tenant billing
    tenant_billing = TenantBillingManager(billing_manager, "tenant-123")
    
    # Setup tenant billing
    tenant_billing.setup_tenant_billing(budget_amount=5000.0)
    
    # Record some usage
    tenant_billing.record_api_usage("/api/v1/query", 100, 5000)
    tenant_billing.record_query_usage("query-456", 1024**3, 2500)  # 1GB processed
    
    # Get spending summary
    spending = tenant_billing.get_current_spending()
    print(f"Current spending: {json.dumps(spending, indent=2)}")
    
    # Generate cost report
    cost_report = billing_manager.generate_cost_report(
        tenant_id="tenant-123",
        start_date=datetime.utcnow() - timedelta(days=30),
        end_date=datetime.utcnow()
    )
    
    print(f"Cost report: {json.dumps(cost_report, indent=2)}")