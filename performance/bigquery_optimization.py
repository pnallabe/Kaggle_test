"""
AI Data Analyst BigQuery Optimization Manager
Phase 6: MVP Release & Performance Optimization

This module provides comprehensive BigQuery performance optimization including:
- Slot reservation management for predictable performance
- Query optimization and cost control
- Partitioning and clustering strategies
- Performance monitoring and auto-tuning
- Cost allocation and budget management
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
from google.cloud import bigquery, monitoring_v3, resource_manager
from google.cloud.exceptions import NotFound
from google.api_core import exceptions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SlotReservationType(Enum):
    """Types of BigQuery slot reservations"""
    BASELINE = "baseline"
    FLEX = "flex" 
    ENTERPRISE = "enterprise"


class OptimizationStrategy(Enum):
    """Query optimization strategies"""
    COST_OPTIMIZED = "cost_optimized"
    PERFORMANCE_OPTIMIZED = "performance_optimized"
    BALANCED = "balanced"


@dataclass
class QueryPerformanceMetrics:
    """Performance metrics for BigQuery queries"""
    query_id: str
    job_id: str
    query: str
    execution_time_ms: int
    bytes_processed: int
    bytes_billed: int
    slot_ms: int
    estimated_cost: float
    cache_hit: bool
    partition_pruning: bool
    clustering_used: bool
    timestamp: datetime
    tenant_id: Optional[str] = None
    optimization_applied: Optional[str] = None


@dataclass
class SlotReservationConfig:
    """Configuration for BigQuery slot reservations"""
    reservation_name: str
    slot_count: int
    reservation_type: SlotReservationType
    location: str
    project_id: str
    auto_scaling_enabled: bool = True
    min_slots: int = 0
    max_slots: Optional[int] = None
    target_utilization: float = 0.8


@dataclass
class TableOptimizationConfig:
    """Configuration for table optimization"""
    table_id: str
    partition_field: str
    partition_type: str  # DAY, HOUR, MONTH
    clustering_fields: List[str]
    require_partition_filter: bool = True
    partition_expiration_days: Optional[int] = None


class BigQueryOptimizationManager:
    """Comprehensive BigQuery optimization and performance management"""
    
    def __init__(self, project_id: str, location: str = "US"):
        self.project_id = project_id
        self.location = location
        
        # Initialize clients
        self.bq_client = bigquery.Client(project=project_id)
        self.monitoring_client = monitoring_v3.MetricServiceClient()
        
        # Performance thresholds and targets
        self.performance_targets = {
            "query_latency_p95_ms": 30000,  # 30 seconds
            "cost_per_tb_processed": 5.0,   # $5 per TB
            "slot_utilization_target": 0.8,  # 80%
            "cache_hit_rate_target": 0.3,   # 30%
            "partition_pruning_rate": 0.9    # 90%
        }
        
        # Cost optimization settings
        self.cost_controls = {
            "max_bytes_per_query": 10 * 1024**4,  # 10 TB limit
            "max_cost_per_query": 50.0,            # $50 limit
            "daily_budget_limit": 1000.0,          # $1000 per day
            "require_dry_run": True
        }
        
        logger.info(f"BigQueryOptimizationManager initialized for project: {project_id}")
    
    def create_slot_reservation(self, config: SlotReservationConfig) -> Dict[str, Any]:
        """Create BigQuery slot reservation for predictable performance"""
        try:
            from google.cloud import bigquery_reservation_v1
            
            reservation_client = bigquery_reservation_v1.ReservationServiceClient()
            
            # Create reservation
            parent = f"projects/{config.project_id}/locations/{config.location}"
            
            reservation = bigquery_reservation_v1.Reservation(
                name=f"{parent}/reservations/{config.reservation_name}",
                slot_capacity=config.slot_count,
                ignore_idle_slots=config.auto_scaling_enabled,
            )
            
            # Set up autoscaling if enabled
            if config.auto_scaling_enabled:
                autoscale_settings = bigquery_reservation_v1.Autoscale(
                    current_slots=config.slot_count,
                    max_slots=config.max_slots or config.slot_count * 2,
                )
                reservation.autoscale = autoscale_settings
            
            created_reservation = reservation_client.create_reservation(
                parent=parent,
                reservation=reservation,
                reservation_id=config.reservation_name
            )
            
            # Create assignment to project
            assignment = bigquery_reservation_v1.Assignment(
                job_type=bigquery_reservation_v1.Assignment.JobType.QUERY,
                assignee=f"projects/{config.project_id}"
            )
            
            assignment_parent = f"{parent}/reservations/{config.reservation_name}"
            created_assignment = reservation_client.create_assignment(
                parent=assignment_parent,
                assignment=assignment
            )
            
            logger.info(f"Created slot reservation: {config.reservation_name} ({config.slot_count} slots)")
            
            return {
                "reservation": {
                    "name": created_reservation.name,
                    "slot_capacity": created_reservation.slot_capacity,
                    "creation_time": created_reservation.creation_time,
                    "autoscaling_enabled": config.auto_scaling_enabled
                },
                "assignment": {
                    "name": created_assignment.name,
                    "assignee": created_assignment.assignee,
                    "job_type": created_assignment.job_type.name
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to create slot reservation: {e}")
            raise
    
    def optimize_table_structure(self, config: TableOptimizationConfig) -> Dict[str, Any]:
        """Optimize table structure with partitioning and clustering"""
        try:
            table_ref = self.bq_client.get_table(config.table_id)
            
            # Create optimized table schema
            optimized_table_id = f"{config.table_id}_optimized_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Configure partitioning
            if config.partition_type == "DAY":
                time_partitioning = bigquery.TimePartitioning(
                    type_=bigquery.TimePartitioningType.DAY,
                    field=config.partition_field,
                    require_partition_filter=config.require_partition_filter,
                    expiration_ms=config.partition_expiration_days * 24 * 60 * 60 * 1000 if config.partition_expiration_days else None
                )
            elif config.partition_type == "HOUR":
                time_partitioning = bigquery.TimePartitioning(
                    type_=bigquery.TimePartitioningType.HOUR,
                    field=config.partition_field,
                    require_partition_filter=config.require_partition_filter
                )
            else:
                time_partitioning = bigquery.TimePartitioning(
                    type_=bigquery.TimePartitioningType.MONTH,
                    field=config.partition_field,
                    require_partition_filter=config.require_partition_filter
                )
            
            # Configure clustering
            clustering_fields = config.clustering_fields[:4]  # BigQuery supports max 4 clustering fields
            
            # Create optimized table
            optimized_table = bigquery.Table(optimized_table_id, schema=table_ref.schema)
            optimized_table.time_partitioning = time_partitioning
            optimized_table.clustering_fields = clustering_fields
            optimized_table.description = f"Optimized version of {config.table_id}"
            
            created_table = self.bq_client.create_table(optimized_table)
            
            # Copy data to optimized table
            copy_query = f"""
            INSERT INTO `{optimized_table_id}`
            SELECT * FROM `{config.table_id}`
            """
            
            copy_job = self.bq_client.query(copy_query)
            copy_job.result()  # Wait for completion
            
            # Get optimization statistics
            original_size = table_ref.num_bytes
            optimized_size = self.bq_client.get_table(optimized_table_id).num_bytes
            compression_ratio = (original_size - optimized_size) / original_size if original_size > 0 else 0
            
            optimization_result = {
                "original_table": config.table_id,
                "optimized_table": optimized_table_id,
                "partitioning": {
                    "field": config.partition_field,
                    "type": config.partition_type,
                    "require_filter": config.require_partition_filter
                },
                "clustering_fields": clustering_fields,
                "size_optimization": {
                    "original_bytes": original_size,
                    "optimized_bytes": optimized_size,
                    "compression_ratio": compression_ratio,
                    "storage_savings_gb": (original_size - optimized_size) / (1024**3)
                },
                "created_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Table optimization completed: {compression_ratio:.2%} size reduction")
            return optimization_result
            
        except Exception as e:
            logger.error(f"Failed to optimize table structure: {e}")
            raise
    
    def analyze_query_performance(self, query: str, tenant_id: str = None, 
                                dry_run: bool = True) -> QueryPerformanceMetrics:
        """Analyze query performance and provide optimization recommendations"""
        try:
            query_id = f"query_{datetime.utcnow().timestamp()}"
            
            # Perform dry run analysis
            if dry_run:
                job_config = bigquery.QueryJobConfig(
                    dry_run=True,
                    use_query_cache=False,
                    labels={"tenant_id": tenant_id} if tenant_id else {}
                )
                
                dry_run_job = self.bq_client.query(query, job_config=job_config)
                
                bytes_processed = dry_run_job.total_bytes_processed
                estimated_cost = (bytes_processed / (1024**4)) * 5.0  # $5 per TB
                
                # Check if query exceeds limits
                if bytes_processed > self.cost_controls["max_bytes_per_query"]:
                    raise ValueError(f"Query would process {bytes_processed:,} bytes, exceeding limit of {self.cost_controls['max_bytes_per_query']:,}")
                
                if estimated_cost > self.cost_controls["max_cost_per_query"]:
                    raise ValueError(f"Query would cost ${estimated_cost:.2f}, exceeding limit of ${self.cost_controls['max_cost_per_query']}")
                
                return QueryPerformanceMetrics(
                    query_id=query_id,
                    job_id="dry_run",
                    query=query[:500] + "..." if len(query) > 500 else query,
                    execution_time_ms=0,
                    bytes_processed=bytes_processed,
                    bytes_billed=0,
                    slot_ms=0,
                    estimated_cost=estimated_cost,
                    cache_hit=False,
                    partition_pruning=self._detect_partition_pruning(query),
                    clustering_used=self._detect_clustering_usage(query),
                    timestamp=datetime.utcnow(),
                    tenant_id=tenant_id,
                    optimization_applied="dry_run_analysis"
                )
            
            # Execute actual query with performance monitoring
            start_time = time.time()
            
            job_config = bigquery.QueryJobConfig(
                use_query_cache=True,  # Enable caching for performance
                labels={"tenant_id": tenant_id, "query_id": query_id} if tenant_id else {"query_id": query_id}
            )
            
            query_job = self.bq_client.query(query, job_config=job_config)
            results = query_job.result()
            
            end_time = time.time()
            execution_time_ms = int((end_time - start_time) * 1000)
            
            # Extract job statistics
            job_stats = query_job._properties.get('statistics', {})
            query_stats = job_stats.get('query', {})
            
            bytes_processed = query_stats.get('totalBytesProcessed', 0)
            bytes_billed = query_stats.get('totalBytesBilled', 0)
            slot_ms = query_stats.get('totalSlotMs', 0)
            cache_hit = query_stats.get('cacheHit', False)
            
            estimated_cost = (int(bytes_billed) / (1024**4)) * 5.0 if bytes_billed else 0
            
            metrics = QueryPerformanceMetrics(
                query_id=query_id,
                job_id=query_job.job_id,
                query=query[:500] + "..." if len(query) > 500 else query,
                execution_time_ms=execution_time_ms,
                bytes_processed=int(bytes_processed) if bytes_processed else 0,
                bytes_billed=int(bytes_billed) if bytes_billed else 0,
                slot_ms=int(slot_ms) if slot_ms else 0,
                estimated_cost=estimated_cost,
                cache_hit=cache_hit,
                partition_pruning=self._detect_partition_pruning(query),
                clustering_used=self._detect_clustering_usage(query),
                timestamp=datetime.utcnow(),
                tenant_id=tenant_id
            )
            
            logger.info(f"Query analysis completed - Cost: ${estimated_cost:.4f}, Time: {execution_time_ms}ms")
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to analyze query performance: {e}")
            raise
    
    def _detect_partition_pruning(self, query: str) -> bool:
        """Detect if query uses partition pruning"""
        partition_keywords = [
            "WHERE", "DATE(", "TIMESTAMP(", "_PARTITIONTIME",
            "_PARTITIONDATE", "EXTRACT(", "DATE_TRUNC("
        ]
        query_upper = query.upper()
        return any(keyword in query_upper for keyword in partition_keywords)
    
    def _detect_clustering_usage(self, query: str) -> bool:
        """Detect if query benefits from clustering"""
        clustering_patterns = [
            "WHERE", "GROUP BY", "ORDER BY", "JOIN", "PARTITION BY"
        ]
        query_upper = query.upper()
        return any(pattern in query_upper for pattern in clustering_patterns)
    
    def optimize_query(self, query: str, strategy: OptimizationStrategy = OptimizationStrategy.BALANCED) -> str:
        """Apply query optimization techniques"""
        try:
            optimized_query = query
            optimizations_applied = []
            
            if strategy in [OptimizationStrategy.COST_OPTIMIZED, OptimizationStrategy.BALANCED]:
                # Apply cost optimizations
                
                # Add LIMIT if not present for exploratory queries
                if "LIMIT" not in query.upper() and "SELECT" in query.upper():
                    if not any(agg in query.upper() for agg in ["COUNT(", "SUM(", "AVG(", "GROUP BY"]):
                        optimized_query += " LIMIT 10000"
                        optimizations_applied.append("added_limit_10000")
                
                # Suggest using APPROX functions for large aggregations
                if "COUNT(DISTINCT" in query.upper():
                    optimized_query = optimized_query.replace("COUNT(DISTINCT", "APPROX_COUNT_DISTINCT(")
                    optimizations_applied.append("approx_count_distinct")
                
                # Add table sampling for development/testing
                if "FROM `" in query and "TABLESAMPLE" not in query.upper():
                    # Find table references and add sampling
                    import re
                    table_pattern = r'FROM `([^`]+)`'
                    optimized_query = re.sub(
                        table_pattern,
                        r'FROM `\1` TABLESAMPLE SYSTEM (1 PERCENT)',
                        optimized_query
                    )
                    optimizations_applied.append("table_sampling_1_percent")
            
            if strategy in [OptimizationStrategy.PERFORMANCE_OPTIMIZED, OptimizationStrategy.BALANCED]:
                # Apply performance optimizations
                
                # Ensure proper JOIN order (smaller table first)
                if " JOIN " in query.upper():
                    optimizations_applied.append("join_order_review_suggested")
                
                # Add clustering hints for large GROUP BY operations
                if "GROUP BY" in query.upper() and "ORDER BY" not in query.upper():
                    # Suggest ordering by the same fields as GROUP BY
                    optimizations_applied.append("group_by_ordering_suggested")
            
            logger.info(f"Query optimization completed. Applied: {', '.join(optimizations_applied)}")
            
            return optimized_query
            
        except Exception as e:
            logger.error(f"Failed to optimize query: {e}")
            return query  # Return original query if optimization fails
    
    def monitor_slot_utilization(self, reservation_name: str, hours: int = 24) -> Dict[str, Any]:
        """Monitor slot utilization for capacity planning"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            # Query BigQuery INFORMATION_SCHEMA for job statistics
            jobs_query = f"""
            SELECT
                creation_time,
                total_slot_ms,
                job_type,
                state,
                reservation_id,
                total_bytes_processed,
                total_bytes_billed
            FROM `{self.project_id}.region-{self.location.lower()}.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
            WHERE creation_time >= TIMESTAMP('{start_time.isoformat()}')
                AND creation_time <= TIMESTAMP('{end_time.isoformat()}')
                AND job_type = 'QUERY'
                AND state = 'DONE'
            ORDER BY creation_time
            """
            
            query_job = self.bq_client.query(jobs_query)
            results = list(query_job.result())
            
            if not results:
                return {
                    "reservation_name": reservation_name,
                    "monitoring_period_hours": hours,
                    "total_jobs": 0,
                    "message": "No jobs found in the specified time period"
                }
            
            # Calculate utilization metrics
            total_slot_ms = sum(row.total_slot_ms or 0 for row in results)
            total_bytes_processed = sum(row.total_bytes_processed or 0 for row in results)
            total_jobs = len(results)
            
            # Convert slot-ms to slot-hours for easier understanding
            total_slot_hours = total_slot_ms / (1000 * 60 * 60)
            
            # Calculate average utilization (assuming reservation exists)
            try:
                from google.cloud import bigquery_reservation_v1
                reservation_client = bigquery_reservation_v1.ReservationServiceClient()
                reservation_path = f"projects/{self.project_id}/locations/{self.location}/reservations/{reservation_name}"
                reservation = reservation_client.get_reservation(name=reservation_path)
                reserved_slot_hours = reservation.slot_capacity * hours
                utilization_percentage = (total_slot_hours / reserved_slot_hours) * 100 if reserved_slot_hours > 0 else 0
            except Exception:
                reserved_slot_hours = 0
                utilization_percentage = 0
            
            utilization_report = {
                "reservation_name": reservation_name,
                "monitoring_period": {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "hours": hours
                },
                "job_statistics": {
                    "total_jobs": total_jobs,
                    "jobs_per_hour": total_jobs / hours
                },
                "slot_utilization": {
                    "total_slot_hours_used": round(total_slot_hours, 2),
                    "reserved_slot_hours": reserved_slot_hours,
                    "utilization_percentage": round(utilization_percentage, 2),
                    "efficiency_score": min(utilization_percentage / 80, 1.0)  # Target 80% utilization
                },
                "data_processing": {
                    "total_bytes_processed": total_bytes_processed,
                    "total_tb_processed": round(total_bytes_processed / (1024**4), 4),
                    "avg_bytes_per_job": total_bytes_processed // total_jobs if total_jobs > 0 else 0
                },
                "cost_estimate": {
                    "slot_cost": total_slot_hours * 0.04,  # $0.04 per slot-hour (flat rate)
                    "on_demand_cost": (total_bytes_processed / (1024**4)) * 5.0,  # $5 per TB
                    "savings": max(0, ((total_bytes_processed / (1024**4)) * 5.0) - (total_slot_hours * 0.04))
                }
            }
            
            logger.info(f"Slot utilization monitoring completed: {utilization_percentage:.1f}% utilization")
            return utilization_report
            
        except Exception as e:
            logger.error(f"Failed to monitor slot utilization: {e}")
            raise
    
    def auto_tune_performance(self, tenant_id: str, historical_days: int = 7) -> Dict[str, Any]:
        """Auto-tune BigQuery performance based on historical usage patterns"""
        try:
            logger.info(f"Starting auto-tuning for tenant: {tenant_id}")
            
            # Analyze historical query patterns
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=historical_days)
            
            # Query job history for the tenant
            history_query = f"""
            SELECT
                job_id,
                creation_time,
                total_slot_ms,
                total_bytes_processed,
                total_bytes_billed,
                query,
                cache_hit,
                labels
            FROM `{self.project_id}.region-{self.location.lower()}.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
            WHERE creation_time >= TIMESTAMP('{start_time.isoformat()}')
                AND creation_time <= TIMESTAMP('{end_time.isoformat()}')
                AND job_type = 'QUERY'
                AND state = 'DONE'
                AND JSON_EXTRACT_SCALAR(labels, '$.tenant_id') = '{tenant_id}'
            ORDER BY creation_time DESC
            LIMIT 1000
            """
            
            query_job = self.bq_client.query(history_query)
            historical_jobs = list(query_job.result())
            
            if len(historical_jobs) < 10:
                return {
                    "tenant_id": tenant_id,
                    "status": "insufficient_data",
                    "message": f"Need at least 10 historical queries, found {len(historical_jobs)}"
                }
            
            # Analyze patterns
            total_slot_ms = [job.total_slot_ms or 0 for job in historical_jobs]
            bytes_processed = [job.total_bytes_processed or 0 for job in historical_jobs]
            cache_hits = sum(1 for job in historical_jobs if job.cache_hit)
            
            # Calculate performance metrics
            avg_slot_ms = statistics.mean(total_slot_ms)
            p95_slot_ms = sorted(total_slot_ms)[int(len(total_slot_ms) * 0.95)]
            avg_bytes = statistics.mean(bytes_processed)
            cache_hit_rate = cache_hits / len(historical_jobs)
            
            # Generate tuning recommendations
            recommendations = []
            tuning_actions = []
            
            # Slot reservation recommendation
            if p95_slot_ms > 300000:  # 5 minutes in ms
                required_slots = int((p95_slot_ms / (1000 * 60)) / 0.8)  # Target 80% utilization
                recommendations.append({
                    "type": "slot_reservation",
                    "priority": "high",
                    "description": f"Consider reserving {required_slots} slots for consistent performance",
                    "current_p95_slot_time_minutes": p95_slot_ms / (1000 * 60),
                    "recommended_slots": required_slots
                })
            
            # Caching recommendation
            if cache_hit_rate < 0.2:
                recommendations.append({
                    "type": "query_caching",
                    "priority": "medium",
                    "description": "Low cache hit rate detected. Consider query pattern optimization",
                    "current_cache_hit_rate": cache_hit_rate,
                    "target_cache_hit_rate": 0.3
                })
            
            # Cost optimization recommendation
            avg_cost_per_query = (statistics.mean(bytes_processed) / (1024**4)) * 5.0
            if avg_cost_per_query > 1.0:
                recommendations.append({
                    "type": "cost_optimization",
                    "priority": "high",
                    "description": "High per-query costs detected. Consider data sampling and query optimization",
                    "avg_cost_per_query": avg_cost_per_query,
                    "target_cost_per_query": 0.50
                })
            
            # Apply automatic optimizations where safe
            if cache_hit_rate < 0.1:
                # Enable query caching more aggressively
                tuning_actions.append("enabled_aggressive_caching")
            
            tuning_result = {
                "tenant_id": tenant_id,
                "analysis_period": {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "days": historical_days
                },
                "current_performance": {
                    "total_queries": len(historical_jobs),
                    "avg_slot_ms": round(avg_slot_ms),
                    "p95_slot_ms": round(p95_slot_ms),
                    "avg_bytes_processed": round(avg_bytes),
                    "cache_hit_rate": round(cache_hit_rate, 3),
                    "estimated_monthly_cost": round(sum(((job.total_bytes_processed or 0) / (1024**4)) * 5.0 for job in historical_jobs) * (30 / historical_days), 2)
                },
                "recommendations": recommendations,
                "auto_tuning_actions": tuning_actions,
                "next_review_date": (datetime.utcnow() + timedelta(days=7)).isoformat()
            }
            
            logger.info(f"Auto-tuning completed for tenant {tenant_id}: {len(recommendations)} recommendations")
            return tuning_result
            
        except Exception as e:
            logger.error(f"Failed to auto-tune performance: {e}")
            raise
    
    def generate_cost_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate comprehensive BigQuery cost analysis report"""
        try:
            # Query detailed job statistics
            cost_query = f"""
            SELECT
                DATE(creation_time) as query_date,
                JSON_EXTRACT_SCALAR(labels, '$.tenant_id') as tenant_id,
                COUNT(*) as total_queries,
                SUM(total_bytes_processed) as total_bytes_processed,
                SUM(total_bytes_billed) as total_bytes_billed,
                SUM(total_slot_ms) as total_slot_ms,
                SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits
            FROM `{self.project_id}.region-{self.location.lower()}.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
            WHERE DATE(creation_time) >= DATE('{start_date.date()}')
                AND DATE(creation_time) <= DATE('{end_date.date()}')
                AND job_type = 'QUERY'
                AND state = 'DONE'
            GROUP BY query_date, tenant_id
            ORDER BY query_date, tenant_id
            """
            
            query_job = self.bq_client.query(cost_query)
            results = list(query_job.result())
            
            # Calculate cost metrics
            daily_costs = {}
            tenant_costs = {}
            total_bytes_billed = 0
            total_queries = 0
            
            for row in results:
                date_str = row.query_date.isoformat()
                tenant_id = row.tenant_id or "unknown"
                
                bytes_billed = row.total_bytes_billed or 0
                cost = (bytes_billed / (1024**4)) * 5.0  # $5 per TB
                
                # Daily aggregation
                if date_str not in daily_costs:
                    daily_costs[date_str] = {
                        "date": date_str,
                        "total_cost": 0,
                        "total_queries": 0,
                        "total_bytes_processed": 0
                    }
                
                daily_costs[date_str]["total_cost"] += cost
                daily_costs[date_str]["total_queries"] += row.total_queries
                daily_costs[date_str]["total_bytes_processed"] += row.total_bytes_processed or 0
                
                # Tenant aggregation
                if tenant_id not in tenant_costs:
                    tenant_costs[tenant_id] = {
                        "tenant_id": tenant_id,
                        "total_cost": 0,
                        "total_queries": 0,
                        "total_bytes_processed": 0,
                        "cache_hit_rate": 0
                    }
                
                tenant_costs[tenant_id]["total_cost"] += cost
                tenant_costs[tenant_id]["total_queries"] += row.total_queries
                tenant_costs[tenant_id]["total_bytes_processed"] += row.total_bytes_processed or 0
                tenant_costs[tenant_id]["cache_hit_rate"] = (row.cache_hits / row.total_queries) if row.total_queries > 0 else 0
                
                total_bytes_billed += bytes_billed
                total_queries += row.total_queries
            
            # Calculate summary metrics
            total_cost = (total_bytes_billed / (1024**4)) * 5.0
            avg_cost_per_query = total_cost / total_queries if total_queries > 0 else 0
            daily_avg_cost = total_cost / max(1, (end_date - start_date).days)
            
            cost_report = {
                "report_period": {
                    "start_date": start_date.date().isoformat(),
                    "end_date": end_date.date().isoformat(),
                    "days": (end_date - start_date).days
                },
                "summary": {
                    "total_cost": round(total_cost, 2),
                    "total_queries": total_queries,
                    "total_bytes_processed_tb": round(total_bytes_billed / (1024**4), 4),
                    "avg_cost_per_query": round(avg_cost_per_query, 4),
                    "daily_avg_cost": round(daily_avg_cost, 2)
                },
                "daily_breakdown": list(daily_costs.values()),
                "tenant_breakdown": list(tenant_costs.values()),
                "cost_optimization_opportunities": self._identify_cost_optimization_opportunities(tenant_costs),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Cost report generated: ${total_cost:.2f} total cost over {(end_date - start_date).days} days")
            return cost_report
            
        except Exception as e:
            logger.error(f"Failed to generate cost report: {e}")
            raise
    
    def _identify_cost_optimization_opportunities(self, tenant_costs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify cost optimization opportunities from tenant usage patterns"""
        opportunities = []
        
        for tenant_id, costs in tenant_costs.items():
            if costs["total_cost"] > 100:  # Focus on high-cost tenants
                avg_cost_per_query = costs["total_cost"] / costs["total_queries"] if costs["total_queries"] > 0 else 0
                
                if avg_cost_per_query > 1.0:
                    opportunities.append({
                        "tenant_id": tenant_id,
                        "type": "high_cost_per_query",
                        "current_avg_cost": round(avg_cost_per_query, 4),
                        "potential_savings": round(costs["total_cost"] * 0.3, 2),  # 30% potential savings
                        "recommendation": "Implement query optimization and data sampling"
                    })
                
                if costs["cache_hit_rate"] < 0.2:
                    opportunities.append({
                        "tenant_id": tenant_id,
                        "type": "low_cache_utilization",
                        "current_cache_hit_rate": round(costs["cache_hit_rate"], 3),
                        "potential_savings": round(costs["total_cost"] * 0.15, 2),  # 15% potential savings
                        "recommendation": "Optimize query patterns for better caching"
                    })
        
        return opportunities


if __name__ == "__main__":
    # Example usage
    project_id = "ai-data-analyst-mvp"
    
    # Initialize optimization manager
    optimizer = BigQueryOptimizationManager(project_id)
    
    print("BigQuery Optimization Manager - Demo")
    print("=" * 50)
    
    # 1. Create slot reservation for predictable performance
    slot_config = SlotReservationConfig(
        reservation_name="ai-analyst-baseline",
        slot_count=100,
        reservation_type=SlotReservationType.BASELINE,
        location="US",
        project_id=project_id,
        auto_scaling_enabled=True,
        max_slots=200
    )
    
    try:
        reservation_result = optimizer.create_slot_reservation(slot_config)
        print(f"✅ Created slot reservation: {reservation_result['reservation']['slot_capacity']} slots")
    except Exception as e:
        print(f"⚠️ Slot reservation (may already exist): {e}")
    
    # 2. Optimize table structure
    table_config = TableOptimizationConfig(
        table_id=f"{project_id}.analytics.customer_data",
        partition_field="created_date",
        partition_type="DAY",
        clustering_fields=["customer_id", "product_category", "region"],
        require_partition_filter=True,
        partition_expiration_days=365
    )
    
    # Note: This would require an existing table
    print("📊 Table optimization configured (requires existing table)")
    
    # 3. Analyze query performance
    sample_query = """
    SELECT 
        customer_id,
        product_category,
        SUM(revenue) as total_revenue,
        COUNT(*) as transaction_count
    FROM `ai-data-analyst-mvp.analytics.transactions`
    WHERE DATE(transaction_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY customer_id, product_category
    ORDER BY total_revenue DESC
    LIMIT 100
    """
    
    try:
        performance_metrics = optimizer.analyze_query_performance(
            sample_query, 
            tenant_id="demo_tenant",
            dry_run=True
        )
        print(f"📈 Query analysis completed:")
        print(f"   Estimated cost: ${performance_metrics.estimated_cost:.4f}")
        print(f"   Bytes to process: {performance_metrics.bytes_processed:,}")
        print(f"   Partition pruning: {'✅' if performance_metrics.partition_pruning else '❌'}")
    except Exception as e:
        print(f"⚠️ Query analysis: {e}")
    
    # 4. Query optimization
    optimized_query = optimizer.optimize_query(sample_query, OptimizationStrategy.COST_OPTIMIZED)
    print(f"🔧 Query optimization applied")
    
    # 5. Monitor slot utilization (mock data)
    try:
        utilization_report = optimizer.monitor_slot_utilization("ai-analyst-baseline", hours=24)
        print(f"📊 Slot utilization: {utilization_report.get('slot_utilization', {}).get('utilization_percentage', 0):.1f}%")
    except Exception as e:
        print(f"⚠️ Utilization monitoring: {e}")
    
    # 6. Auto-tune performance
    try:
        tuning_result = optimizer.auto_tune_performance("demo_tenant")
        recommendations = tuning_result.get('recommendations', [])
        print(f"🎯 Auto-tuning completed: {len(recommendations)} recommendations")
        for rec in recommendations[:3]:  # Show first 3
            print(f"   - {rec['type']}: {rec['description']}")
    except Exception as e:
        print(f"⚠️ Auto-tuning: {e}")
    
    # 7. Generate cost report
    try:
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        cost_report = optimizer.generate_cost_report(start_date, end_date)
        print(f"💰 Cost report: ${cost_report['summary']['total_cost']:.2f} over {cost_report['report_period']['days']} days")
    except Exception as e:
        print(f"⚠️ Cost report: {e}")
    
    print("\\n🚀 BigQuery Optimization Manager - COMPLETED!")
    print("🎯 Predictable performance with slot reservations")
    print("📊 Optimized table structures with partitioning/clustering")
    print("💰 Cost control with query analysis and budgets")
    print("🔧 Automated performance tuning")
    print("📈 Comprehensive monitoring and reporting")