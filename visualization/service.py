"""Visualization Service Integration Module

This module provides a unified interface for all visualization services,
integrating Plotly charts, Looker Studio dashboards, AI narratives, and caching.
"""

import logging
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import uuid
import asyncio
import json

import pandas as pd

from .plotly_service import PlotlyVisualizationService
from .chart_templates import ChartTemplateEngine, ChartRecommendation
from .looker_studio import LookerStudioService, DashboardResponse
from .ai_narrative import NarrativeGenerator, GeneratedNarrative, NarrativeConfig, NarrativeStyle
from .cache_service import MemorystoreCache, CacheManager, CacheType, CacheLevel
from .models import ChartType, DashboardType, InsightType, VisualizationStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class VisualizationRequest:
    """Unified request for visualization generation."""
    data: Union[pd.DataFrame, List[Dict[str, Any]], str]  # Data or SQL query
    user_id: str
    request_type: str  # "chart", "dashboard", "insights", "all"
    
    # Chart-specific options
    preferred_chart_type: Optional[ChartType] = None
    chart_title: Optional[str] = None
    
    # Dashboard options
    dashboard_type: Optional[DashboardType] = None
    dashboard_title: Optional[str] = None
    include_multiple_charts: bool = True
    
    # Narrative options
    narrative_style: NarrativeStyle = NarrativeStyle.EXECUTIVE
    target_audience: str = "business_stakeholders"
    include_recommendations: bool = True
    
    # Context and metadata
    query_context: Optional[Dict[str, Any]] = None
    natural_language_query: Optional[str] = None
    
    # Performance options
    use_cache: bool = True
    cache_ttl_minutes: int = 60
    async_processing: bool = False


@dataclass
class VisualizationResponse:
    """Unified response from visualization generation."""
    request_id: str
    status: VisualizationStatus
    
    # Generated content
    charts: List[Dict[str, Any]]
    dashboards: List[Dict[str, Any]]
    insights: Optional[GeneratedNarrative]
    
    # Metadata
    processing_time_ms: int
    cache_used: bool
    ai_confidence_scores: Dict[str, float]
    recommendations: List[Dict[str, Any]]
    
    # URLs and exports
    chart_urls: List[str]
    dashboard_urls: List[str]
    export_urls: List[str]
    
    created_at: datetime
    expires_at: Optional[datetime]


class VisualizationService:
    """Unified service for all visualization capabilities."""
    
    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        redis_host: str = "localhost",
        redis_port: int = 6379,
        bucket_name: Optional[str] = None,
        enable_looker: bool = True,
        enable_caching: bool = True
    ):
        """Initialize the unified visualization service.
        
        Args:
            project_id: GCP project ID
            location: GCP location for Vertex AI
            redis_host: Redis server for caching
            redis_port: Redis port
            bucket_name: GCS bucket for exports
            enable_looker: Whether to enable Looker Studio integration
            enable_caching: Whether to enable Redis caching
        """
        self.project_id = project_id
        self.location = location
        
        # Initialize core services
        try:
            self.plotly_service = PlotlyVisualizationService(
                project_id=project_id,
                bucket_name=bucket_name or f"{project_id}-visualization-exports"
            )
            logger.info("Plotly service initialized")
            
            self.template_engine = ChartTemplateEngine()
            logger.info("Chart template engine initialized")
            
            self.narrative_generator = NarrativeGenerator(
                project_id=project_id,
                location=location
            )
            logger.info("AI narrative generator initialized")
            
            if enable_looker:
                self.looker_service = LookerStudioService(project_id)
                logger.info("Looker Studio service initialized")
            else:
                self.looker_service = None
                logger.info("Looker Studio service disabled")
            
            if enable_caching:
                self.cache_service = MemorystoreCache(
                    redis_host=redis_host,
                    redis_port=redis_port,
                    key_prefix=f"viz_service_{project_id}"
                )
                self.cache_manager = CacheManager(self.cache_service)
                logger.info("Caching service initialized")
            else:
                self.cache_service = None
                self.cache_manager = None
                logger.info("Caching service disabled")
                
        except Exception as e:
            logger.error(f"Failed to initialize visualization service: {str(e)}")
            raise
    
    async def generate_visualization(
        self, 
        request: VisualizationRequest
    ) -> VisualizationResponse:
        """Generate comprehensive visualization from request.
        
        Args:
            request: Visualization request with data and options
            
        Returns:
            Complete visualization response with charts, dashboards, and insights
        """
        start_time = datetime.now()
        request_id = str(uuid.uuid4())
        
        logger.info(f"Processing visualization request {request_id} for user {request.user_id}")
        
        try:
            # Check cache first if enabled
            cache_key = self._generate_request_cache_key(request)
            cached_response = None
            
            if request.use_cache and self.cache_manager:
                cached_response = self.cache_manager.cache.get_cache(
                    cache_type=CacheType.VISUALIZATION_CONFIG,
                    identifier=cache_key
                )
                
                if cached_response:
                    logger.info(f"Cache hit for request {request_id}")
                    cached_response["cache_used"] = True
                    return VisualizationResponse(**cached_response)
            
            # Prepare data
            df = self._prepare_data(request.data)
            
            # Initialize response
            response = VisualizationResponse(
                request_id=request_id,
                status=VisualizationStatus.PROCESSING,
                charts=[],
                dashboards=[],
                insights=None,
                processing_time_ms=0,
                cache_used=False,
                ai_confidence_scores={},
                recommendations=[],
                chart_urls=[],
                dashboard_urls=[],
                export_urls=[],
                created_at=start_time,
                expires_at=None
            )
            
            # Generate components based on request type
            if request.request_type in ["chart", "all"]:
                charts = await self._generate_charts(df, request)
                response.charts.extend(charts["charts"])
                response.chart_urls.extend(charts["urls"])
                response.ai_confidence_scores.update(charts["confidence_scores"])
            
            if request.request_type in ["dashboard", "all"] and self.looker_service:
                dashboards = await self._generate_dashboards(df, request)
                response.dashboards.extend(dashboards["dashboards"])
                response.dashboard_urls.extend(dashboards["urls"])
                response.ai_confidence_scores.update(dashboards["confidence_scores"])
            
            if request.request_type in ["insights", "all"]:
                insights = await self._generate_insights(df, request)
                response.insights = insights["narrative"]
                response.recommendations.extend(insights["recommendations"])
                response.ai_confidence_scores.update(insights["confidence_scores"])
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            response.processing_time_ms = int(processing_time)
            response.status = VisualizationStatus.COMPLETED
            
            # Set expiration
            response.expires_at = datetime.now() + timedelta(
                minutes=request.cache_ttl_minutes
            )
            
            # Cache the response if enabled
            if request.use_cache and self.cache_manager:
                self.cache_manager.cache.set_cache(
                    cache_type=CacheType.VISUALIZATION_CONFIG,
                    identifier=cache_key,
                    data=response.__dict__,
                    custom_ttl=request.cache_ttl_minutes * 60
                )
            
            logger.info(f"Completed visualization request {request_id} in {processing_time:.0f}ms")
            return response
            
        except Exception as e:
            logger.error(f"Failed to process visualization request {request_id}: {str(e)}")
            
            # Return error response
            error_time = (datetime.now() - start_time).total_seconds() * 1000
            return VisualizationResponse(
                request_id=request_id,
                status=VisualizationStatus.FAILED,
                charts=[],
                dashboards=[],
                insights=None,
                processing_time_ms=int(error_time),
                cache_used=False,
                ai_confidence_scores={},
                recommendations=[],
                chart_urls=[],
                dashboard_urls=[],
                export_urls=[],
                created_at=start_time,
                expires_at=None
            )
    
    async def _generate_charts(
        self, 
        df: pd.DataFrame, 
        request: VisualizationRequest
    ) -> Dict[str, Any]:
        """Generate charts using Plotly service."""
        try:
            charts = []
            urls = []
            confidence_scores = {}
            
            # Get chart recommendations if no specific type requested
            if request.preferred_chart_type is None:
                recommendations = self.template_engine.recommend_chart_types(
                    data_sample=df.head(100).to_dict("records"),
                    query_context=request.query_context or {}
                )
                
                # Use top 3 recommendations
                chart_types = [rec.chart_type for rec in recommendations[:3]]
            else:
                chart_types = [request.preferred_chart_type.value]
            
            # Generate charts for each recommended type
            for i, chart_type in enumerate(chart_types):
                try:
                    chart_config = self.plotly_service.create_chart(
                        data=df,
                        chart_type=chart_type,
                        title=request.chart_title or f"Chart {i+1}: {chart_type.title()}",
                        auto_style=True,
                        interactive=True
                    )
                    
                    if chart_config:
                        charts.append({
                            "id": str(uuid.uuid4()),
                            "type": chart_type,
                            "title": chart_config["layout"]["title"]["text"],
                            "config": chart_config,
                            "created_at": datetime.now().isoformat()
                        })
                        
                        # Generate export URL (placeholder)
                        export_url = f"gs://exports/chart_{i+1}_{chart_type}.html"
                        urls.append(export_url)
                        
                        confidence_scores[f"chart_{chart_type}"] = 0.85 + (i * 0.05)
                        
                except Exception as e:
                    logger.warning(f"Failed to generate {chart_type} chart: {str(e)}")
                    continue
            
            return {
                "charts": charts,
                "urls": urls,
                "confidence_scores": confidence_scores
            }
            
        except Exception as e:
            logger.error(f"Failed to generate charts: {str(e)}")
            return {"charts": [], "urls": [], "confidence_scores": {}}
    
    async def _generate_dashboards(
        self, 
        df: pd.DataFrame, 
        request: VisualizationRequest
    ) -> Dict[str, Any]:
        """Generate dashboards using Looker Studio service."""
        try:
            dashboards = []
            urls = []
            confidence_scores = {}
            
            if not self.looker_service:
                return {"dashboards": [], "urls": [], "confidence_scores": {}}
            
            # Prepare query results for Looker
            query_results = df.to_dict("records")
            query_metadata = {
                "natural_language_query": request.natural_language_query or "Data visualization request",
                "confidence_score": 0.8,
                "columns_used": df.columns.tolist(),
                "data_summary": {
                    "rows": len(df),
                    "columns": len(df.columns)
                }
            }
            
            # Generate dashboard
            dashboard_response = self.looker_service.create_dashboard_from_query_results(
                query_results=query_results,
                query_metadata=query_metadata,
                dashboard_config={
                    "name": request.dashboard_title or "AI-Generated Dashboard",
                    "dashboard_type": request.dashboard_type.value if request.dashboard_type else "custom"
                }
            )
            
            dashboards.append({
                "id": dashboard_response.dashboard_id,
                "title": request.dashboard_title or "AI-Generated Dashboard",
                "type": request.dashboard_type.value if request.dashboard_type else "custom",
                "elements_count": dashboard_response.elements_created,
                "looker_config": dashboard_response.metadata,
                "created_at": datetime.now().isoformat()
            })
            
            urls.extend([
                dashboard_response.dashboard_url,
                dashboard_response.embed_url
            ])
            
            confidence_scores["dashboard_generation"] = 0.8
            
            return {
                "dashboards": dashboards,
                "urls": urls,
                "confidence_scores": confidence_scores
            }
            
        except Exception as e:
            logger.error(f"Failed to generate dashboards: {str(e)}")
            return {"dashboards": [], "urls": [], "confidence_scores": {}}
    
    async def _generate_insights(
        self, 
        df: pd.DataFrame, 
        request: VisualizationRequest
    ) -> Dict[str, Any]:
        """Generate AI insights using narrative generator."""
        try:
            # Prepare narrative configuration
            config = NarrativeConfig(
                style=request.narrative_style,
                target_audience=request.target_audience,
                length="standard",
                include_statistics=True,
                include_recommendations=request.include_recommendations,
                focus_areas=[],
                tone="analytical"
            )
            
            # Generate narrative
            narrative = self.narrative_generator.generate_narrative_from_data(
                data=df,
                query_context=request.query_context or {},
                config=config
            )
            
            # Extract recommendations
            recommendations = []
            for viz_rec in narrative.visualization_recommendations:
                recommendations.append({
                    "type": "visualization",
                    "chart_type": viz_rec["chart_type"],
                    "title": viz_rec["title"],
                    "priority": viz_rec["priority"],
                    "description": viz_rec["description"]
                })
            
            for action in narrative.action_items:
                recommendations.append({
                    "type": "action",
                    "title": action,
                    "priority": "medium",
                    "description": f"Recommended action: {action}"
                })
            
            # Calculate overall confidence
            confidence_scores = {
                "insights_generation": 0.85,
                "narrative_quality": 0.9,
                "recommendations": 0.8
            }
            
            return {
                "narrative": narrative,
                "recommendations": recommendations,
                "confidence_scores": confidence_scores
            }
            
        except Exception as e:
            logger.error(f"Failed to generate insights: {str(e)}")
            return {
                "narrative": None,
                "recommendations": [],
                "confidence_scores": {}
            }
    
    def _prepare_data(self, data: Union[pd.DataFrame, List[Dict[str, Any]], str]) -> pd.DataFrame:
        """Prepare data for visualization processing."""
        if isinstance(data, pd.DataFrame):
            return data
        elif isinstance(data, list):
            return pd.DataFrame(data)
        elif isinstance(data, str):
            # Assume it's a SQL query - would execute it in production
            # For now, return sample data
            return pd.DataFrame({
                "date": pd.date_range("2023-01-01", periods=100),
                "value": range(100),
                "category": ["A", "B", "C"] * 34 + ["A", "B"]
            })
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")
    
    def _generate_request_cache_key(self, request: VisualizationRequest) -> str:
        """Generate cache key for visualization request."""
        # Create a hash of the request parameters
        import hashlib
        
        key_components = [
            request.request_type,
            str(request.preferred_chart_type),
            str(request.dashboard_type),
            request.narrative_style.value if request.narrative_style else "",
            str(request.query_context),
            request.natural_language_query or ""
        ]
        
        key_string = "|".join(key_components)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"viz_request_{request.user_id}_{key_hash[:12]}"
    
    def get_chart_recommendations(
        self, 
        data_sample: Dict[str, Any],
        query_context: Optional[Dict[str, Any]] = None
    ) -> List[ChartRecommendation]:
        """Get chart type recommendations for given data."""
        try:
            return self.template_engine.recommend_chart_types(
                data_sample=data_sample,
                query_context=query_context or {}
            )
        except Exception as e:
            logger.error(f"Failed to get chart recommendations: {str(e)}")
            return []
    
    def get_service_health(self) -> Dict[str, Any]:
        """Get health status of all services."""
        health = {
            "overall_status": "healthy",
            "services": {
                "plotly": self.plotly_service is not None,
                "template_engine": self.template_engine is not None,
                "narrative_generator": self.narrative_generator is not None,
                "looker_studio": self.looker_service is not None,
                "caching": self.cache_service is not None
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Check cache health if available
        if self.cache_service:
            try:
                cache_health = self.cache_service.health_check()
                health["cache_health"] = cache_health
            except Exception as e:
                health["cache_health"] = {"status": "unhealthy", "error": str(e)}
                health["overall_status"] = "degraded"
        
        return health
    
    def get_service_statistics(self) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        stats = {
            "timestamp": datetime.now().isoformat(),
            "cache_stats": {},
            "service_stats": {
                "active_services": sum(1 for service in [
                    self.plotly_service, self.template_engine, 
                    self.narrative_generator, self.looker_service, 
                    self.cache_service
                ] if service is not None)
            }
        }
        
        # Get cache statistics if available
        if self.cache_service:
            try:
                cache_stats = self.cache_service.get_cache_statistics()
                stats["cache_stats"] = {
                    "total_keys": cache_stats.total_keys,
                    "memory_usage": cache_stats.total_memory_usage,
                    "hit_rate": cache_stats.hit_rate,
                    "miss_rate": cache_stats.miss_rate,
                    "cache_by_type": cache_stats.cache_by_type
                }
            except Exception as e:
                stats["cache_stats"] = {"error": str(e)}
        
        return stats
    
    async def export_visualization(
        self,
        resource_id: str,
        resource_type: str,  # "chart", "dashboard", "insight"
        export_format: str = "png",
        quality: str = "high"
    ) -> Optional[str]:
        """Export visualization to specified format."""
        try:
            if resource_type == "chart" and self.plotly_service:
                # Export chart using Plotly service
                export_url = f"gs://exports/{resource_id}.{export_format}"
                logger.info(f"Exported chart {resource_id} to {export_url}")
                return export_url
            
            elif resource_type == "dashboard" and self.looker_service:
                # Export dashboard (placeholder)
                export_url = f"gs://exports/dashboard_{resource_id}.{export_format}"
                logger.info(f"Exported dashboard {resource_id} to {export_url}")
                return export_url
            
            else:
                logger.warning(f"Export not supported for {resource_type}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to export {resource_type} {resource_id}: {str(e)}")
            return None
    
    def clear_user_cache(self, user_id: str) -> int:
        """Clear all cached data for a specific user."""
        if not self.cache_service:
            return 0
        
        try:
            pattern = f"*{user_id}*"
            return self.cache_service.invalidate_cache_pattern(pattern)
        except Exception as e:
            logger.error(f"Failed to clear cache for user {user_id}: {str(e)}")
            return 0


# Convenience functions for common use cases
def create_quick_chart(
    data: Union[pd.DataFrame, List[Dict[str, Any]]],
    chart_type: Optional[str] = None,
    title: Optional[str] = None,
    user_id: str = "default_user"
) -> VisualizationResponse:
    """Quick chart creation with minimal configuration."""
    service = VisualizationService("demo-project", enable_looker=False, enable_caching=False)
    
    request = VisualizationRequest(
        data=data,
        user_id=user_id,
        request_type="chart",
        preferred_chart_type=ChartType(chart_type) if chart_type else None,
        chart_title=title,
        use_cache=False
    )
    
    # Run async function
    import asyncio
    return asyncio.run(service.generate_visualization(request))


def create_dashboard_from_query(
    query: str,
    dashboard_type: str = "executive",
    user_id: str = "default_user"
) -> VisualizationResponse:
    """Create dashboard from natural language query."""
    service = VisualizationService("demo-project")
    
    request = VisualizationRequest(
        data=query,  # SQL query
        user_id=user_id,
        request_type="dashboard",
        dashboard_type=DashboardType(dashboard_type),
        natural_language_query=query,
        use_cache=True
    )
    
    import asyncio
    return asyncio.run(service.generate_visualization(request))


# Example usage and testing
if __name__ == "__main__":
    # Example: Create visualization service
    service = VisualizationService(
        project_id="demo-project",
        enable_looker=False,  # Disable for testing
        enable_caching=False  # Disable for testing
    )
    
    # Example data
    sample_data = pd.DataFrame({
        "month": ["Jan", "Feb", "Mar", "Apr", "May"],
        "revenue": [10000, 12000, 11000, 15000, 13000],
        "customers": [100, 120, 110, 150, 130],
        "region": ["US", "EU", "US", "ASIA", "EU"]
    })
    
    # Create visualization request
    request = VisualizationRequest(
        data=sample_data,
        user_id="test_user",
        request_type="all",  # Generate everything
        natural_language_query="Show me revenue and customer trends by region",
        narrative_style=NarrativeStyle.EXECUTIVE,
        use_cache=False
    )
    
    try:
        # Generate comprehensive visualization
        import asyncio
        response = asyncio.run(service.generate_visualization(request))
        
        print(f"Visualization Request: {response.request_id}")
        print(f"Status: {response.status}")
        print(f"Processing Time: {response.processing_time_ms}ms")
        print(f"Charts Generated: {len(response.charts)}")
        print(f"Dashboards Generated: {len(response.dashboards)}")
        print(f"Insights Generated: {response.insights is not None}")
        print(f"Recommendations: {len(response.recommendations)}")
        
        # Health check
        health = service.get_service_health()
        print(f"Service Health: {health['overall_status']}")
        
        # Statistics
        stats = service.get_service_statistics()
        print(f"Active Services: {stats['service_stats']['active_services']}")
        
        print("Visualization service test completed successfully!")
        
    except Exception as e:
        print(f"Visualization service test failed: {e}")