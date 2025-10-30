"""FastAPI Endpoints for Visualization and Dashboard Services

This module provides REST API endpoints for chart generation, dashboard management,
insight delivery, and all visualization services.
"""

from fastapi import FastAPI, HTTPException, Depends, Query, Body, Path, File, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.background import BackgroundTasks
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import uuid
import json
import asyncio
import logging
import io
import zipfile
from contextlib import asynccontextmanager

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import desc, and_, or_

# Import our services and models
from .plotly_service import PlotlyVisualizationService
from .chart_templates import ChartTemplateEngine
from .looker_studio import LookerStudioService
from .ai_narrative import NarrativeGenerator
from .cache_service import MemorystoreCache, CacheManager, CacheType, CacheLevel
from .models import (
    Base, User, Chart, Dashboard, InsightNarrative, DataSource, 
    UserPreferences, QueryCache, AuditLog, SystemMetrics,
    ChartType, DashboardType, InsightType, VisualizationStatus, ShareLevel
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Global services (will be initialized in lifespan)
plotly_service = None
template_engine = None
looker_service = None
narrative_generator = None
cache_service = None
cache_manager = None


# Pydantic models for request/response
class ChartCreateRequest(BaseModel):
    """Request model for creating a chart."""
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    chart_type: ChartType
    data_query: str
    data_source_id: Optional[str] = None
    styling: Optional[Dict[str, Any]] = {}
    layout_config: Optional[Dict[str, Any]] = {}
    share_level: ShareLevel = ShareLevel.PRIVATE
    auto_generate: bool = True  # Use AI to optimize chart


class ChartUpdateRequest(BaseModel):
    """Request model for updating a chart."""
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    styling: Optional[Dict[str, Any]] = None
    layout_config: Optional[Dict[str, Any]] = None
    share_level: Optional[ShareLevel] = None


class ChartResponse(BaseModel):
    """Response model for chart data."""
    id: str
    title: str
    description: Optional[str]
    chart_type: ChartType
    config: Dict[str, Any]
    styling: Dict[str, Any]
    status: VisualizationStatus
    share_level: ShareLevel
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime]
    view_count: int
    ai_confidence_score: Optional[float]


class DashboardCreateRequest(BaseModel):
    """Request model for creating a dashboard."""
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    dashboard_type: DashboardType = DashboardType.CUSTOM
    layout_config: Dict[str, Any]
    theme_config: Optional[Dict[str, Any]] = {}
    filter_config: Optional[Dict[str, Any]] = {}
    chart_ids: List[str] = []
    share_level: ShareLevel = ShareLevel.PRIVATE
    auto_generate_from_query: Optional[str] = None  # Natural language query


class DashboardResponse(BaseModel):
    """Response model for dashboard data."""
    id: str
    title: str
    description: Optional[str]
    dashboard_type: DashboardType
    layout_config: Dict[str, Any]
    theme_config: Dict[str, Any]
    status: VisualizationStatus
    share_level: ShareLevel
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime]
    view_count: int
    chart_count: int
    looker_embed_url: Optional[str]


class InsightGenerationRequest(BaseModel):
    """Request model for generating insights."""
    data_source: Union[str, Dict[str, Any]]  # Query or data directly
    query_context: Optional[Dict[str, Any]] = {}
    narrative_style: str = "executive"
    target_audience: str = "business_stakeholders"
    length: str = "standard"
    include_statistics: bool = True
    include_recommendations: bool = True
    focus_areas: List[str] = []


class InsightResponse(BaseModel):
    """Response model for generated insights."""
    id: str
    title: str
    executive_summary: str
    key_insights: List[Dict[str, Any]]
    detailed_narrative: str
    action_items: List[str]
    viz_recommendations: List[Dict[str, Any]]
    confidence_scores: Dict[str, float]
    created_by: str
    created_at: datetime
    status: VisualizationStatus


class DataQueryRequest(BaseModel):
    """Request model for data queries."""
    query: str
    use_cache: bool = True
    cache_ttl_minutes: int = 60
    limit: Optional[int] = None


class ExportRequest(BaseModel):
    """Request model for exporting visualizations."""
    resource_ids: List[str]
    export_format: str = "png"  # png, pdf, html, json
    include_data: bool = False
    quality: str = "high"  # low, medium, high


# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    # Startup
    global plotly_service, template_engine, looker_service, narrative_generator, cache_service, cache_manager
    
    logger.info("Initializing visualization services...")
    
    try:
        # Initialize services (these would use environment variables in production)
        PROJECT_ID = "your-project-id"
        
        plotly_service = PlotlyVisualizationService(
            project_id=PROJECT_ID,
            bucket_name="visualization-exports"
        )
        
        template_engine = ChartTemplateEngine()
        
        looker_service = LookerStudioService(PROJECT_ID)
        
        narrative_generator = NarrativeGenerator(
            project_id=PROJECT_ID,
            location="us-central1"
        )
        
        cache_service = MemorystoreCache(
            redis_host="localhost",
            redis_port=6379,
            key_prefix="ai_data_analyst_api"
        )
        
        cache_manager = CacheManager(cache_service)
        
        logger.info("All services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down visualization services...")


# Create FastAPI app
app = FastAPI(
    title="AI Data Analyst - Visualization API",
    description="REST API for intelligent data visualization, dashboard creation, and AI-powered insights",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get database session
def get_db():
    """Get database session."""
    # This would be implemented with your database connection
    # For now, return None as placeholder
    return None


# Dependency to get current user
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current authenticated user."""
    # This would implement JWT token validation
    # For now, return a placeholder user ID
    return "user_123"


# Chart endpoints
@app.post("/api/v1/charts", response_model=ChartResponse)
async def create_chart(
    request: ChartCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new chart with optional AI optimization."""
    try:
        logger.info(f"Creating chart: {request.title}")
        
        # Generate chart ID
        chart_id = str(uuid.uuid4())
        
        if request.auto_generate and plotly_service:
            # Use AI to optimize chart configuration
            background_tasks.add_task(
                generate_optimized_chart,
                chart_id,
                request,
                current_user
            )
            
            # Return initial response
            return ChartResponse(
                id=chart_id,
                title=request.title,
                description=request.description,
                chart_type=request.chart_type,
                config={},
                styling=request.styling or {},
                status=VisualizationStatus.PROCESSING,
                share_level=request.share_level,
                created_by=current_user,
                created_at=datetime.now(),
                updated_at=None,
                view_count=0,
                ai_confidence_score=None
            )
        else:
            # Create chart directly
            chart_config = {
                "chart_type": request.chart_type.value,
                "title": request.title,
                "data_query": request.data_query
            }
            
            return ChartResponse(
                id=chart_id,
                title=request.title,
                description=request.description,
                chart_type=request.chart_type,
                config=chart_config,
                styling=request.styling or {},
                status=VisualizationStatus.COMPLETED,
                share_level=request.share_level,
                created_by=current_user,
                created_at=datetime.now(),
                updated_at=None,
                view_count=0,
                ai_confidence_score=None
            )
            
    except Exception as e:
        logger.error(f"Failed to create chart: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/charts/{chart_id}", response_model=ChartResponse)
async def get_chart(
    chart_id: str = Path(..., description="Chart ID"),
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get chart by ID."""
    try:
        # Check cache first
        if cache_manager:
            cached_chart = cache_manager.cache.get_cache(
                cache_type=CacheType.CHART_DATA,
                identifier=chart_id
            )
            if cached_chart:
                return ChartResponse(**cached_chart)
        
        # Placeholder response (would query database in production)
        return ChartResponse(
            id=chart_id,
            title="Sample Chart",
            description="Sample chart description",
            chart_type=ChartType.BAR,
            config={"type": "bar"},
            styling={},
            status=VisualizationStatus.COMPLETED,
            share_level=ShareLevel.PRIVATE,
            created_by=current_user,
            created_at=datetime.now(),
            updated_at=None,
            view_count=1,
            ai_confidence_score=0.85
        )
        
    except Exception as e:
        logger.error(f"Failed to get chart {chart_id}: {str(e)}")
        raise HTTPException(status_code=404, detail="Chart not found")


@app.put("/api/v1/charts/{chart_id}", response_model=ChartResponse)
async def update_chart(
    chart_id: str,
    request: ChartUpdateRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update chart configuration."""
    try:
        logger.info(f"Updating chart {chart_id}")
        
        # Invalidate cache
        if cache_manager:
            cache_manager.cache.delete_cache(
                cache_type=CacheType.CHART_DATA,
                identifier=chart_id
            )
        
        # Update chart (placeholder response)
        return ChartResponse(
            id=chart_id,
            title=request.title or "Updated Chart",
            description=request.description,
            chart_type=ChartType.BAR,
            config=request.config or {"type": "bar"},
            styling=request.styling or {},
            status=VisualizationStatus.COMPLETED,
            share_level=request.share_level or ShareLevel.PRIVATE,
            created_by=current_user,
            created_at=datetime.now() - timedelta(hours=1),
            updated_at=datetime.now(),
            view_count=5,
            ai_confidence_score=0.9
        )
        
    except Exception as e:
        logger.error(f"Failed to update chart {chart_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/charts/{chart_id}")
async def delete_chart(
    chart_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete chart."""
    try:
        logger.info(f"Deleting chart {chart_id}")
        
        # Invalidate cache
        if cache_manager:
            cache_manager.cache.delete_cache(
                cache_type=CacheType.CHART_DATA,
                identifier=chart_id
            )
        
        return {"message": "Chart deleted successfully"}
        
    except Exception as e:
        logger.error(f"Failed to delete chart {chart_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/charts", response_model=List[ChartResponse])
async def list_charts(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    chart_type: Optional[ChartType] = None,
    status: Optional[VisualizationStatus] = None,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List charts for current user."""
    try:
        # Placeholder response (would query database in production)
        sample_charts = [
            ChartResponse(
                id=str(uuid.uuid4()),
                title=f"Chart {i+1}",
                description=f"Sample chart {i+1}",
                chart_type=ChartType.BAR if i % 2 == 0 else ChartType.LINE,
                config={"type": "bar" if i % 2 == 0 else "line"},
                styling={},
                status=VisualizationStatus.COMPLETED,
                share_level=ShareLevel.PRIVATE,
                created_by=current_user,
                created_at=datetime.now() - timedelta(days=i),
                updated_at=None,
                view_count=i * 3,
                ai_confidence_score=0.8 + (i * 0.02)
            )
            for i in range(min(limit, 5))  # Return max 5 sample charts
        ]
        
        return sample_charts
        
    except Exception as e:
        logger.error(f"Failed to list charts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Dashboard endpoints
@app.post("/api/v1/dashboards", response_model=DashboardResponse)
async def create_dashboard(
    request: DashboardCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new dashboard."""
    try:
        logger.info(f"Creating dashboard: {request.title}")
        
        dashboard_id = str(uuid.uuid4())
        
        if request.auto_generate_from_query and looker_service:
            # Generate dashboard from natural language query
            background_tasks.add_task(
                generate_dashboard_from_query,
                dashboard_id,
                request.auto_generate_from_query,
                current_user
            )
            
            status = VisualizationStatus.PROCESSING
        else:
            status = VisualizationStatus.COMPLETED
        
        return DashboardResponse(
            id=dashboard_id,
            title=request.title,
            description=request.description,
            dashboard_type=request.dashboard_type,
            layout_config=request.layout_config,
            theme_config=request.theme_config or {},
            status=status,
            share_level=request.share_level,
            created_by=current_user,
            created_at=datetime.now(),
            updated_at=None,
            view_count=0,
            chart_count=len(request.chart_ids),
            looker_embed_url=None
        )
        
    except Exception as e:
        logger.error(f"Failed to create dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(
    dashboard_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard by ID."""
    try:
        # Check cache first
        if cache_manager:
            cached_dashboard = cache_manager.cache.get_cache(
                cache_type=CacheType.DASHBOARD_CONFIG,
                identifier=dashboard_id
            )
            if cached_dashboard:
                return DashboardResponse(**cached_dashboard)
        
        # Placeholder response
        return DashboardResponse(
            id=dashboard_id,
            title="Sample Dashboard",
            description="Sample dashboard",
            dashboard_type=DashboardType.EXECUTIVE,
            layout_config={"width": 1200, "height": 800},
            theme_config={"primary_color": "#1f77b4"},
            status=VisualizationStatus.COMPLETED,
            share_level=ShareLevel.PRIVATE,
            created_by=current_user,
            created_at=datetime.now(),
            updated_at=None,
            view_count=10,
            chart_count=3,
            looker_embed_url="https://datastudio.google.com/embed/dashboard123"
        )
        
    except Exception as e:
        logger.error(f"Failed to get dashboard {dashboard_id}: {str(e)}")
        raise HTTPException(status_code=404, detail="Dashboard not found")


# Insight generation endpoints
@app.post("/api/v1/insights/generate", response_model=InsightResponse)
async def generate_insights(
    request: InsightGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate AI-powered insights from data."""
    try:
        logger.info("Generating insights from data")
        
        insight_id = str(uuid.uuid4())
        
        if narrative_generator:
            # Generate insights in background
            background_tasks.add_task(
                generate_narrative_insights,
                insight_id,
                request,
                current_user
            )
            
            return InsightResponse(
                id=insight_id,
                title="Data Analysis in Progress",
                executive_summary="Analyzing data to generate insights...",
                key_insights=[],
                detailed_narrative="Analysis in progress. Please check back shortly.",
                action_items=[],
                viz_recommendations=[],
                confidence_scores={},
                created_by=current_user,
                created_at=datetime.now(),
                status=VisualizationStatus.PROCESSING
            )
        else:
            raise HTTPException(status_code=503, detail="Insight generation service unavailable")
            
    except Exception as e:
        logger.error(f"Failed to generate insights: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/insights/{insight_id}", response_model=InsightResponse)
async def get_insights(
    insight_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get generated insights by ID."""
    try:
        # Check cache first
        if cache_manager:
            cached_insights = cache_manager.cache.get_cache(
                cache_type=CacheType.INSIGHT_NARRATIVE,
                identifier=insight_id
            )
            if cached_insights:
                return InsightResponse(**cached_insights)
        
        # Placeholder response
        return InsightResponse(
            id=insight_id,
            title="Sample Data Analysis",
            executive_summary="The data reveals strong growth trends with seasonal patterns and notable outliers in Q3.",
            key_insights=[
                {
                    "type": "trend",
                    "title": "Revenue Growth Trend",
                    "summary": "Revenue shows 15% month-over-month growth",
                    "confidence": 0.9
                }
            ],
            detailed_narrative="Detailed analysis shows consistent growth patterns...",
            action_items=[
                "Investigate Q3 anomalies",
                "Optimize for seasonal patterns"
            ],
            viz_recommendations=[
                {
                    "chart_type": "line_chart",
                    "title": "Revenue Trend",
                    "priority": "high"
                }
            ],
            confidence_scores={"overall": 0.85, "trend": 0.9},
            created_by=current_user,
            created_at=datetime.now(),
            status=VisualizationStatus.COMPLETED
        )
        
    except Exception as e:
        logger.error(f"Failed to get insights {insight_id}: {str(e)}")
        raise HTTPException(status_code=404, detail="Insights not found")


# Data query endpoints
@app.post("/api/v1/data/query")
async def execute_data_query(
    request: DataQueryRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Execute data query with caching."""
    try:
        logger.info(f"Executing data query for user {current_user}")
        
        # Generate query hash for caching
        import hashlib
        query_hash = hashlib.md5(request.query.encode()).hexdigest()
        
        # Check cache if enabled
        if request.use_cache and cache_manager:
            cached_result = cache_manager.get_cached_query_result(query_hash)
            if cached_result:
                result_data, metadata = cached_result
                return {
                    "data": result_data,
                    "metadata": metadata,
                    "cached": True,
                    "query_hash": query_hash
                }
        
        # Execute query (placeholder)
        result_data = [
            {"id": 1, "name": "Product A", "value": 100},
            {"id": 2, "name": "Product B", "value": 200}
        ]
        
        metadata = {
            "row_count": len(result_data),
            "columns": ["id", "name", "value"],
            "execution_time_ms": 150
        }
        
        # Cache result if enabled
        if request.use_cache and cache_manager:
            cache_manager.cache_query_result(
                query_hash=query_hash,
                result_data=result_data,
                metadata=metadata,
                ttl_minutes=request.cache_ttl_minutes
            )
        
        return {
            "data": result_data,
            "metadata": metadata,
            "cached": False,
            "query_hash": query_hash
        }
        
    except Exception as e:
        logger.error(f"Failed to execute query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Chart recommendation endpoint
@app.post("/api/v1/charts/recommend")
async def recommend_chart_type(
    data_sample: Dict[str, Any] = Body(...),
    query_context: Optional[Dict[str, Any]] = Body(None),
    current_user: str = Depends(get_current_user)
):
    """Get AI recommendations for chart type based on data."""
    try:
        logger.info("Getting chart type recommendations")
        
        if template_engine:
            recommendations = template_engine.recommend_chart_types(
                data_sample=data_sample,
                query_context=query_context or {}
            )
            
            return {
                "recommendations": recommendations,
                "data_profile": template_engine.profile_data(data_sample)
            }
        else:
            # Fallback recommendations
            return {
                "recommendations": [
                    {
                        "chart_type": "bar",
                        "confidence": 0.8,
                        "reasoning": "Good for categorical comparisons"
                    }
                ],
                "data_profile": {"columns": len(data_sample.get("columns", [])), "rows": len(data_sample.get("data", []))}
            }
            
    except Exception as e:
        logger.error(f"Failed to get recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Export endpoints
@app.post("/api/v1/export")
async def export_visualizations(
    request: ExportRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export visualizations in various formats."""
    try:
        logger.info(f"Exporting {len(request.resource_ids)} resources in {request.export_format} format")
        
        if plotly_service:
            # Use Plotly service for export
            export_results = []
            
            for resource_id in request.resource_ids:
                # This would export each chart/dashboard
                export_url = f"gs://exports/{resource_id}.{request.export_format}"
                export_results.append({
                    "resource_id": resource_id,
                    "export_url": export_url,
                    "format": request.export_format,
                    "status": "completed"
                })
            
            return {
                "export_id": str(uuid.uuid4()),
                "exports": export_results,
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(days=7)).isoformat()
            }
        else:
            raise HTTPException(status_code=503, detail="Export service unavailable")
            
    except Exception as e:
        logger.error(f"Failed to export: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# System status endpoints
@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "plotly": plotly_service is not None,
                "template_engine": template_engine is not None,
                "looker": looker_service is not None,
                "narrative": narrative_generator is not None,
                "cache": cache_service is not None
            }
        }
        
        # Check cache health if available
        if cache_service:
            cache_health = cache_service.health_check()
            health_status["cache_health"] = cache_health
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/api/v1/stats")
async def get_system_stats(
    current_user: str = Depends(get_current_user)
):
    """Get system statistics and metrics."""
    try:
        stats = {
            "cache_stats": {},
            "usage_stats": {
                "total_charts": 100,
                "total_dashboards": 25,
                "total_insights": 50,
                "active_users": 15
            },
            "performance_stats": {
                "avg_chart_generation_time_ms": 250,
                "avg_insight_generation_time_ms": 1500,
                "cache_hit_rate": 0.75
            }
        }
        
        # Get cache statistics if available
        if cache_service:
            cache_stats = cache_service.get_cache_statistics()
            stats["cache_stats"] = {
                "total_keys": cache_stats.total_keys,
                "memory_usage": cache_stats.total_memory_usage,
                "hit_rate": cache_stats.hit_rate,
                "cache_by_type": cache_stats.cache_by_type
            }
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Background task functions
async def generate_optimized_chart(chart_id: str, request: ChartCreateRequest, user_id: str):
    """Background task to generate optimized chart using AI."""
    try:
        logger.info(f"Generating optimized chart {chart_id}")
        
        if plotly_service and template_engine:
            # This would use the actual services to optimize the chart
            # For now, just cache a completed result
            optimized_config = {
                "chart_type": request.chart_type.value,
                "title": request.title,
                "data_query": request.data_query,
                "optimizations_applied": ["color_scheme", "layout", "interactions"],
                "ai_confidence": 0.92
            }
            
            if cache_manager:
                cache_manager.cache.set_cache(
                    cache_type=CacheType.CHART_DATA,
                    identifier=chart_id,
                    data={
                        "id": chart_id,
                        "config": optimized_config,
                        "status": VisualizationStatus.COMPLETED.value,
                        "ai_confidence_score": 0.92
                    },
                    cache_level=CacheLevel.PERSISTENT
                )
        
        logger.info(f"Completed chart optimization for {chart_id}")
        
    except Exception as e:
        logger.error(f"Failed to optimize chart {chart_id}: {str(e)}")


async def generate_dashboard_from_query(dashboard_id: str, query: str, user_id: str):
    """Background task to generate dashboard from natural language query."""
    try:
        logger.info(f"Generating dashboard {dashboard_id} from query: {query}")
        
        if looker_service:
            # This would use the actual Looker service
            dashboard_result = {
                "id": dashboard_id,
                "status": VisualizationStatus.COMPLETED.value,
                "looker_embed_url": f"https://datastudio.google.com/embed/{dashboard_id}",
                "charts_created": 3
            }
            
            if cache_manager:
                cache_manager.cache.set_cache(
                    cache_type=CacheType.DASHBOARD_CONFIG,
                    identifier=dashboard_id,
                    data=dashboard_result,
                    cache_level=CacheLevel.PERSISTENT
                )
        
        logger.info(f"Completed dashboard generation for {dashboard_id}")
        
    except Exception as e:
        logger.error(f"Failed to generate dashboard {dashboard_id}: {str(e)}")


async def generate_narrative_insights(insight_id: str, request: InsightGenerationRequest, user_id: str):
    """Background task to generate narrative insights."""
    try:
        logger.info(f"Generating narrative insights {insight_id}")
        
        if narrative_generator:
            # This would use the actual narrative generator
            insights_result = {
                "id": insight_id,
                "title": "AI-Generated Data Insights",
                "executive_summary": "Key patterns and trends identified in the data.",
                "key_insights": [
                    {
                        "type": "trend",
                        "title": "Growth Pattern Detected",
                        "summary": "Strong upward trend observed",
                        "confidence": 0.89
                    }
                ],
                "detailed_narrative": "Comprehensive analysis reveals multiple significant patterns...",
                "status": VisualizationStatus.COMPLETED.value,
                "confidence_scores": {"overall": 0.85}
            }
            
            if cache_manager:
                cache_manager.cache_insight_narrative(
                    narrative_id=insight_id,
                    narrative_data=insights_result,
                    query_context=request.query_context
                )
        
        logger.info(f"Completed insight generation for {insight_id}")
        
    except Exception as e:
        logger.error(f"Failed to generate insights {insight_id}: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    # Run the API server
    uvicorn.run(
        "api_endpoints:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )