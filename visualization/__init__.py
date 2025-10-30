"""AI Data Analyst - Visualization Module

This module provides comprehensive visualization and dashboard generation capabilities
using AI-powered chart recommendations, interactive Plotly visualizations, enterprise
Looker Studio dashboards, automated insight narratives, and high-performance caching.

Main Components:
- PlotlyVisualizationService: Interactive chart generation with auto-styling
- ChartTemplateEngine: AI-powered chart type recommendations  
- LookerStudioService: Enterprise dashboard creation and embedding
- NarrativeGenerator: AI-generated insights and data storytelling
- MemorystoreCache: High-performance Redis caching layer
- VisualizationService: Unified service integrating all components
- FastAPI endpoints: REST API for all visualization services

Usage:
    from visualization import VisualizationService, VisualizationRequest
    from visualization.models import ChartType, DashboardType
    
    # Initialize service
    service = VisualizationService(project_id="my-project")
    
    # Create visualization request
    request = VisualizationRequest(
        data=my_dataframe,
        user_id="user123",
        request_type="all"
    )
    
    # Generate comprehensive visualization
    response = await service.generate_visualization(request)
"""

from .service import (
    VisualizationService,
    VisualizationRequest, 
    VisualizationResponse,
    create_quick_chart,
    create_dashboard_from_query
)

from .plotly_service import (
    PlotlyVisualizationService,
    ChartConfig,
    ExportConfig
)

from .chart_templates import (
    ChartTemplateEngine,
    ChartRecommendation,
    ChartTemplate,
    DataProfile
)

from .looker_studio import (
    LookerStudioService,
    DashboardTemplate,
    DashboardResponse,
    DataSourceConfig
)

from .ai_narrative import (
    NarrativeGenerator,
    GeneratedNarrative,
    NarrativeConfig,
    DataInsight,
    InsightType,
    NarrativeStyle
)

from .cache_service import (
    MemorystoreCache,
    CacheManager,
    CacheType,
    CacheLevel,
    CacheEntry,
    CacheStats
)

from .models import (
    # Enums
    ChartType,
    DashboardType,
    VisualizationStatus,
    ShareLevel,
    
    # Models
    User,
    Chart,
    Dashboard,
    InsightNarrative,
    DataSource,
    UserPreferences,
    QueryCache,
    AuditLog,
    SystemMetrics
)

# Version info
__version__ = "1.0.0"
__author__ = "AI Data Analyst Team"
__description__ = "Comprehensive AI-powered data visualization and dashboard generation"

# Export main classes
__all__ = [
    # Main service
    "VisualizationService",
    "VisualizationRequest",
    "VisualizationResponse",
    
    # Core services
    "PlotlyVisualizationService", 
    "ChartTemplateEngine",
    "LookerStudioService",
    "NarrativeGenerator",
    "MemorystoreCache",
    "CacheManager",
    
    # Configuration classes
    "ChartConfig",
    "ExportConfig", 
    "ChartRecommendation",
    "ChartTemplate",
    "DataProfile",
    "DashboardTemplate",
    "DashboardResponse",
    "DataSourceConfig",
    "GeneratedNarrative",
    "NarrativeConfig",
    "DataInsight",
    "CacheEntry",
    "CacheStats",
    
    # Enums
    "ChartType",
    "DashboardType", 
    "InsightType",
    "NarrativeStyle",
    "VisualizationStatus",
    "ShareLevel",
    "CacheType",
    "CacheLevel",
    
    # Database models
    "User",
    "Chart", 
    "Dashboard",
    "InsightNarrative",
    "DataSource",
    "UserPreferences",
    "QueryCache",
    "AuditLog",
    "SystemMetrics",
    
    # Utility functions
    "create_quick_chart",
    "create_dashboard_from_query"
]


def get_version():
    """Get version information."""
    return {
        "version": __version__,
        "author": __author__, 
        "description": __description__
    }


def health_check():
    """Perform basic module health check."""
    try:
        # Test imports
        from .service import VisualizationService
        from .models import ChartType
        
        return {
            "status": "healthy",
            "module_version": __version__,
            "imports_successful": True
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "imports_successful": False
        }