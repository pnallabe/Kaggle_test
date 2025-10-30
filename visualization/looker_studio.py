"""Looker Studio Integration Service

This module provides integration with Google Looker Studio for advanced
dashboard creation, embedding, and enterprise-grade visualization capabilities.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import uuid
import base64

from google.cloud import bigquery
from google.oauth2 import service_account
import requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DashboardType(Enum):
    """Types of Looker Studio dashboards."""
    EXECUTIVE = "executive"
    OPERATIONAL = "operational"
    ANALYTICAL = "analytical"
    KPI = "kpi"
    CUSTOM = "custom"


class VisualizationType(Enum):
    """Visualization types supported in Looker Studio."""
    TABLE = "table"
    SCORECARD = "scorecard"
    TIME_SERIES = "time_series"
    BAR_CHART = "bar_chart"
    COLUMN_CHART = "column_chart"
    PIE_CHART = "pie_chart"
    GEO_CHART = "geo_chart"
    SCATTER_CHART = "scatter_chart"
    LINE_CHART = "line_chart"
    AREA_CHART = "area_chart"
    COMBO_CHART = "combo_chart"
    BULLET_CHART = "bullet_chart"
    GAUGE = "gauge"
    TREEMAP = "treemap"


@dataclass
class DataSourceConfig:
    """Configuration for Looker Studio data source."""
    source_type: str  # "bigquery", "sheets", "mysql", etc.
    connection_params: Dict[str, Any]
    schema_info: Dict[str, Any]
    refresh_schedule: Optional[str] = None
    cache_duration: Optional[int] = None


@dataclass
class DashboardElement:
    """Element configuration for dashboard."""
    element_id: str
    element_type: VisualizationType
    title: str
    position: Dict[str, int]  # x, y, width, height
    data_source: str
    fields: Dict[str, List[str]]  # dimensions, metrics, filters
    styling: Dict[str, Any]
    interactions: Dict[str, Any]


@dataclass
class DashboardTemplate:
    """Template for creating Looker Studio dashboards."""
    template_id: str
    name: str
    description: str
    dashboard_type: DashboardType
    elements: List[DashboardElement]
    layout: Dict[str, Any]
    theme: Dict[str, Any]
    filters: List[Dict[str, Any]]
    data_sources: List[DataSourceConfig]


@dataclass
class DashboardResponse:
    """Response from dashboard creation."""
    dashboard_id: str
    dashboard_url: str
    embed_url: str
    edit_url: str
    data_sources: List[str]
    elements_created: int
    status: str
    metadata: Dict[str, Any]


class LookerStudioService:
    """Service for creating and managing Looker Studio dashboards."""
    
    def __init__(
        self,
        project_id: str,
        service_account_path: Optional[str] = None,
        credentials: Optional[service_account.Credentials] = None
    ):
        """Initialize Looker Studio service.
        
        Args:
            project_id: GCP project ID
            service_account_path: Path to service account JSON
            credentials: Service account credentials object
        """
        self.project_id = project_id
        
        # Initialize credentials
        if credentials:
            self.credentials = credentials
        elif service_account_path:
            self.credentials = service_account.Credentials.from_service_account_file(
                service_account_path,
                scopes=[
                    'https://www.googleapis.com/auth/analytics.readonly',
                    'https://www.googleapis.com/auth/bigquery',
                    'https://www.googleapis.com/auth/drive'
                ]
            )
        else:
            # Use default credentials
            from google.auth import default
            self.credentials, _ = default()
        
        # Initialize BigQuery client
        self.bq_client = bigquery.Client(
            project=project_id, 
            credentials=self.credentials
        )
        
        # Looker Studio API endpoints
        self.base_url = "https://datastudio.googleapis.com/v1"
        
        # Load dashboard templates
        self._load_templates()
        
        logger.info(f"Initialized LookerStudioService for project {project_id}")
    
    def _load_templates(self) -> None:
        """Load predefined dashboard templates."""
        self.templates = {
            DashboardType.EXECUTIVE: DashboardTemplate(
                template_id="executive_overview",
                name="Executive Overview",
                description="High-level KPIs and executive summary",
                dashboard_type=DashboardType.EXECUTIVE,
                elements=[
                    DashboardElement(
                        element_id="revenue_scorecard",
                        element_type=VisualizationType.SCORECARD,
                        title="Total Revenue",
                        position={"x": 0, "y": 0, "width": 200, "height": 100},
                        data_source="main_data",
                        fields={
                            "metrics": ["revenue"],
                            "dimensions": [],
                            "filters": []
                        },
                        styling={"color": "#1f77b4", "font_size": "large"},
                        interactions={}
                    ),
                    DashboardElement(
                        element_id="revenue_trend",
                        element_type=VisualizationType.LINE_CHART,
                        title="Revenue Trend",
                        position={"x": 0, "y": 120, "width": 600, "height": 300},
                        data_source="main_data",
                        fields={
                            "metrics": ["revenue"],
                            "dimensions": ["date"],
                            "filters": []
                        },
                        styling={"color_scheme": "default"},
                        interactions={"enable_zoom": True}
                    ),
                    DashboardElement(
                        element_id="top_products",
                        element_type=VisualizationType.BAR_CHART,
                        title="Top Products by Revenue",
                        position={"x": 620, "y": 120, "width": 400, "height": 300},
                        data_source="main_data",
                        fields={
                            "metrics": ["revenue"],
                            "dimensions": ["product"],
                            "filters": []
                        },
                        styling={"sort_descending": True},
                        interactions={"enable_drill_down": True}
                    )
                ],
                layout={"width": 1024, "height": 768, "grid_size": 20},
                theme={"primary_color": "#1f77b4", "background": "white"},
                filters=[
                    {"field": "date", "type": "date_range", "default": "last_30_days"}
                ],
                data_sources=[]
            ),
            
            DashboardType.ANALYTICAL: DashboardTemplate(
                template_id="analytical_deep_dive",
                name="Analytical Deep Dive",
                description="Detailed analysis with multiple visualizations",
                dashboard_type=DashboardType.ANALYTICAL,
                elements=[
                    DashboardElement(
                        element_id="correlation_matrix",
                        element_type=VisualizationType.TABLE,
                        title="Correlation Analysis",
                        position={"x": 0, "y": 0, "width": 500, "height": 250},
                        data_source="main_data",
                        fields={
                            "metrics": ["correlation_coefficient"],
                            "dimensions": ["variable_1", "variable_2"],
                            "filters": []
                        },
                        styling={"conditional_formatting": True},
                        interactions={}
                    ),
                    DashboardElement(
                        element_id="distribution_chart",
                        element_type=VisualizationType.COLUMN_CHART,
                        title="Value Distribution",
                        position={"x": 520, "y": 0, "width": 500, "height": 250},
                        data_source="main_data",
                        fields={
                            "metrics": ["count"],
                            "dimensions": ["value_bucket"],
                            "filters": []
                        },
                        styling={"show_data_labels": True},
                        interactions={}
                    ),
                    DashboardElement(
                        element_id="time_series_comparison",
                        element_type=VisualizationType.COMBO_CHART,
                        title="Multi-Metric Time Series",
                        position={"x": 0, "y": 270, "width": 1020, "height": 350},
                        data_source="main_data",
                        fields={
                            "metrics": ["metric_1", "metric_2"],
                            "dimensions": ["date"],
                            "filters": []
                        },
                        styling={"dual_axis": True},
                        interactions={"enable_zoom": True}
                    )
                ],
                layout={"width": 1024, "height": 768, "grid_size": 20},
                theme={"primary_color": "#ff7f0e", "background": "white"},
                filters=[
                    {"field": "date", "type": "date_range", "default": "last_90_days"},
                    {"field": "category", "type": "multi_select", "default": "all"}
                ],
                data_sources=[]
            )
        }
    
    def create_dashboard_from_query_results(
        self,
        query_results: List[Dict[str, Any]],
        query_metadata: Dict[str, Any],
        dashboard_config: Optional[Dict[str, Any]] = None
    ) -> DashboardResponse:
        """Create a Looker Studio dashboard from query results.
        
        Args:
            query_results: Results from conversational query
            query_metadata: Metadata about the query and results
            dashboard_config: Configuration overrides
            
        Returns:
            Dashboard creation response
        """
        try:
            logger.info("Creating dashboard from query results")
            
            # Create temporary BigQuery table from results
            temp_table_id = self._create_temp_table(query_results, query_metadata)
            
            # Create data source configuration
            data_source_config = self._create_bigquery_data_source(temp_table_id)
            
            # Determine dashboard type and template
            dashboard_type = self._determine_dashboard_type(query_metadata, dashboard_config)
            template = self._get_or_create_template(dashboard_type, query_metadata)
            
            # Create the dashboard
            dashboard_response = self._create_dashboard(
                template, 
                [data_source_config], 
                dashboard_config
            )
            
            logger.info(f"Created dashboard: {dashboard_response.dashboard_id}")
            return dashboard_response
            
        except Exception as e:
            logger.error(f"Failed to create dashboard: {str(e)}")
            raise
    
    def create_dashboard_from_template(
        self,
        template_type: DashboardType,
        data_sources: List[DataSourceConfig],
        customizations: Optional[Dict[str, Any]] = None
    ) -> DashboardResponse:
        """Create dashboard from predefined template.
        
        Args:
            template_type: Type of dashboard template
            data_sources: Data source configurations
            customizations: Template customizations
            
        Returns:
            Dashboard creation response
        """
        try:
            template = self.templates.get(template_type)
            if not template:
                raise ValueError(f"Template not found: {template_type}")
            
            return self._create_dashboard(template, data_sources, customizations)
            
        except Exception as e:
            logger.error(f"Failed to create template dashboard: {str(e)}")
            raise
    
    def _create_temp_table(
        self, 
        query_results: List[Dict[str, Any]], 
        metadata: Dict[str, Any]
    ) -> str:
        """Create temporary BigQuery table from query results."""
        try:
            # Generate unique table name
            table_id = f"temp_dashboard_{uuid.uuid4().hex[:8]}"
            full_table_id = f"{self.project_id}.temp_dashboards.{table_id}"
            
            # Create dataset if it doesn't exist
            dataset_id = "temp_dashboards"
            try:
                self.bq_client.get_dataset(dataset_id)
            except:
                dataset = bigquery.Dataset(f"{self.project_id}.{dataset_id}")
                dataset.location = "US"
                dataset.default_table_expiration_ms = 24 * 60 * 60 * 1000  # 24 hours
                self.bq_client.create_dataset(dataset)
            
            # Create table schema from first result
            if query_results:
                schema = []
                first_row = query_results[0]
                for key, value in first_row.items():
                    if isinstance(value, bool):
                        field_type = "BOOLEAN"
                    elif isinstance(value, int):
                        field_type = "INTEGER"
                    elif isinstance(value, float):
                        field_type = "FLOAT"
                    elif isinstance(value, datetime):
                        field_type = "TIMESTAMP"
                    else:
                        field_type = "STRING"
                    
                    schema.append(bigquery.SchemaField(key, field_type))
                
                # Create table
                table = bigquery.Table(full_table_id, schema=schema)
                table.expires = datetime.now() + timedelta(hours=24)
                table = self.bq_client.create_table(table)
                
                # Load data
                job_config = bigquery.LoadJobConfig(
                    source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
                    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
                )
                
                # Convert results to JSON lines
                json_rows = [json.dumps(row, default=str) for row in query_results]
                job = self.bq_client.load_table_from_json(
                    json_rows, table, job_config=job_config
                )
                job.result()  # Wait for completion
                
                logger.info(f"Created temporary table: {full_table_id}")
                return full_table_id
            else:
                raise ValueError("No query results to create table from")
                
        except Exception as e:
            logger.error(f"Failed to create temp table: {str(e)}")
            raise
    
    def _create_bigquery_data_source(self, table_id: str) -> DataSourceConfig:
        """Create BigQuery data source configuration."""
        return DataSourceConfig(
            source_type="bigquery",
            connection_params={
                "project_id": self.project_id,
                "table_id": table_id
            },
            schema_info={
                "table": table_id,
                "fields": self._get_table_schema(table_id)
            },
            refresh_schedule="on_demand",
            cache_duration=3600  # 1 hour
        )
    
    def _get_table_schema(self, table_id: str) -> List[Dict[str, Any]]:
        """Get schema information for BigQuery table."""
        try:
            table = self.bq_client.get_table(table_id)
            schema_info = []
            
            for field in table.schema:
                schema_info.append({
                    "name": field.name,
                    "type": field.field_type,
                    "mode": field.mode,
                    "description": field.description
                })
            
            return schema_info
            
        except Exception as e:
            logger.warning(f"Failed to get table schema: {str(e)}")
            return []
    
    def _determine_dashboard_type(
        self, 
        query_metadata: Dict[str, Any], 
        config: Optional[Dict[str, Any]]
    ) -> DashboardType:
        """Determine appropriate dashboard type."""
        # Check explicit configuration
        if config and "dashboard_type" in config:
            return DashboardType(config["dashboard_type"])
        
        # Analyze query metadata
        query_text = query_metadata.get("natural_language_query", "").lower()
        
        if any(word in query_text for word in ["kpi", "metric", "performance", "summary"]):
            return DashboardType.EXECUTIVE
        elif any(word in query_text for word in ["analysis", "correlation", "detailed", "deep"]):
            return DashboardType.ANALYTICAL
        elif any(word in query_text for word in ["operations", "daily", "monitoring"]):
            return DashboardType.OPERATIONAL
        else:
            return DashboardType.CUSTOM
    
    def _get_or_create_template(
        self, 
        dashboard_type: DashboardType, 
        metadata: Dict[str, Any]
    ) -> DashboardTemplate:
        """Get existing template or create custom one."""
        if dashboard_type in self.templates:
            return self.templates[dashboard_type]
        else:
            # Create custom template based on metadata
            return self._create_custom_template(metadata)
    
    def _create_custom_template(self, metadata: Dict[str, Any]) -> DashboardTemplate:
        """Create custom dashboard template based on query metadata."""
        # Analyze data characteristics
        data_summary = metadata.get("data_summary", {})
        columns = metadata.get("columns_used", [])
        
        elements = []
        
        # Create basic elements based on data
        if "date" in [col.lower() for col in columns]:
            # Add time series chart
            elements.append(DashboardElement(
                element_id="time_series",
                element_type=VisualizationType.LINE_CHART,
                title="Trend Over Time",
                position={"x": 0, "y": 0, "width": 600, "height": 300},
                data_source="main_data",
                fields={
                    "metrics": [col for col in columns if col.lower() not in ["date", "time"]],
                    "dimensions": [col for col in columns if col.lower() in ["date", "time"]],
                    "filters": []
                },
                styling={"color_scheme": "default"},
                interactions={"enable_zoom": True}
            ))
        
        # Add summary table
        elements.append(DashboardElement(
            element_id="summary_table",
            element_type=VisualizationType.TABLE,
            title="Data Summary",
            position={"x": 0, "y": 320, "width": 1000, "height": 300},
            data_source="main_data",
            fields={
                "metrics": [],
                "dimensions": columns[:10],  # Limit columns
                "filters": []
            },
            styling={"alternating_rows": True},
            interactions={"enable_sorting": True}
        ))
        
        return DashboardTemplate(
            template_id="custom_" + uuid.uuid4().hex[:8],
            name="Custom Dashboard",
            description="Auto-generated dashboard from query",
            dashboard_type=DashboardType.CUSTOM,
            elements=elements,
            layout={"width": 1024, "height": 768, "grid_size": 20},
            theme={"primary_color": "#2ca02c", "background": "white"},
            filters=[],
            data_sources=[]
        )
    
    def _create_dashboard(
        self,
        template: DashboardTemplate,
        data_sources: List[DataSourceConfig],
        customizations: Optional[Dict[str, Any]]
    ) -> DashboardResponse:
        """Create the actual Looker Studio dashboard."""
        try:
            # Generate unique dashboard ID
            dashboard_id = f"dashboard_{uuid.uuid4().hex[:12]}"
            
            # Simulate dashboard creation (In production, use actual Looker Studio API)
            dashboard_config = {
                "id": dashboard_id,
                "name": customizations.get("name", template.name) if customizations else template.name,
                "description": template.description,
                "template_id": template.template_id,
                "data_sources": [ds.connection_params for ds in data_sources],
                "elements": len(template.elements),
                "layout": template.layout,
                "theme": template.theme,
                "filters": template.filters,
                "created_at": datetime.now().isoformat()
            }
            
            # Generate URLs (In production, these would be real Looker Studio URLs)
            base_url = "https://datastudio.google.com/reporting"
            dashboard_url = f"{base_url}/{dashboard_id}"
            embed_url = f"{base_url}/embed/{dashboard_id}"
            edit_url = f"{base_url}/{dashboard_id}/edit"
            
            # Create response
            response = DashboardResponse(
                dashboard_id=dashboard_id,
                dashboard_url=dashboard_url,
                embed_url=embed_url,
                edit_url=edit_url,
                data_sources=[ds.connection_params.get("table_id", "") for ds in data_sources],
                elements_created=len(template.elements),
                status="created",
                metadata={
                    "template_used": template.template_id,
                    "dashboard_type": template.dashboard_type.value,
                    "created_at": datetime.now().isoformat(),
                    "config": dashboard_config
                }
            )
            
            logger.info(f"Dashboard created successfully: {dashboard_id}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to create dashboard: {str(e)}")
            raise
    
    def get_dashboard_embed_config(
        self, 
        dashboard_id: str, 
        user_permissions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get configuration for embedding dashboard."""
        try:
            embed_config = {
                "dashboard_id": dashboard_id,
                "embed_url": f"https://datastudio.google.com/reporting/embed/{dashboard_id}",
                "iframe_config": {
                    "width": "100%",
                    "height": "600px",
                    "frameborder": "0",
                    "allowfullscreen": True
                },
                "permissions": user_permissions or {
                    "can_view": True,
                    "can_edit": False,
                    "can_share": False
                },
                "parameters": {
                    "embed": "true",
                    "rm": "minimal"  # Remove UI elements
                }
            }
            
            return embed_config
            
        except Exception as e:
            logger.error(f"Failed to get embed config: {str(e)}")
            raise
    
    def update_dashboard_data_source(
        self, 
        dashboard_id: str, 
        new_data_source: DataSourceConfig
    ) -> bool:
        """Update dashboard data source."""
        try:
            # In production, this would use the actual Looker Studio API
            logger.info(f"Updated data source for dashboard {dashboard_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update data source: {str(e)}")
            return False
    
    def get_dashboard_analytics(self, dashboard_id: str, days: int = 30) -> Dict[str, Any]:
        """Get analytics for dashboard usage."""
        try:
            # In production, this would fetch real analytics
            analytics = {
                "dashboard_id": dashboard_id,
                "period_days": days,
                "total_views": 150,
                "unique_viewers": 45,
                "avg_session_duration": 180,  # seconds
                "most_viewed_elements": [
                    {"element_id": "revenue_trend", "views": 89},
                    {"element_id": "top_products", "views": 76}
                ],
                "popular_filters": [
                    {"filter": "date_range", "usage_count": 134},
                    {"filter": "category", "usage_count": 67}
                ]
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get analytics: {str(e)}")
            return {}
    
    def list_available_templates(self) -> List[Dict[str, Any]]:
        """List all available dashboard templates."""
        templates_info = []
        
        for dashboard_type, template in self.templates.items():
            templates_info.append({
                "type": dashboard_type.value,
                "id": template.template_id,
                "name": template.name,
                "description": template.description,
                "elements_count": len(template.elements),
                "data_sources_required": len(template.data_sources)
            })
        
        return templates_info


# Example usage and testing
if __name__ == "__main__":
    # Example configuration
    PROJECT_ID = "your-project-id"
    
    # Initialize service
    service = LookerStudioService(PROJECT_ID)
    
    # Example query results
    sample_results = [
        {"date": "2023-01-01", "revenue": 1000, "product": "A", "region": "US"},
        {"date": "2023-01-02", "revenue": 1200, "product": "B", "region": "EU"},
        {"date": "2023-01-03", "revenue": 800, "product": "A", "region": "US"},
    ]
    
    sample_metadata = {
        "natural_language_query": "Show me revenue trends by product and region",
        "confidence_score": 0.85,
        "columns_used": ["date", "revenue", "product", "region"],
        "data_summary": {"rows": 3, "columns": 4}
    }
    
    try:
        # Create dashboard from query results
        dashboard = service.create_dashboard_from_query_results(
            sample_results, 
            sample_metadata,
            {"name": "Revenue Analysis Dashboard"}
        )
        
        print(f"Dashboard created: {dashboard.dashboard_id}")
        print(f"Dashboard URL: {dashboard.dashboard_url}")
        print(f"Embed URL: {dashboard.embed_url}")
        print(f"Elements created: {dashboard.elements_created}")
        
        # Get embed configuration
        embed_config = service.get_dashboard_embed_config(dashboard.dashboard_id)
        print(f"Embed config: {embed_config}")
        
        # List available templates
        templates = service.list_available_templates()
        print(f"Available templates: {len(templates)}")
        for template in templates:
            print(f"  - {template['name']}: {template['description']}")
            
    except Exception as e:
        print(f"Error: {e}")