"""Plotly Visualization Service

This module provides intelligent chart generation using Plotly, with automatic
chart type selection based on data characteristics and query context.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
from datetime import datetime
import base64
import io

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio
from google.cloud import storage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChartType(Enum):
    """Supported chart types."""
    BAR = "bar"
    LINE = "line"
    SCATTER = "scatter"
    PIE = "pie"
    HISTOGRAM = "histogram"
    BOX = "box"
    HEATMAP = "heatmap"
    AREA = "area"
    VIOLIN = "violin"
    SUNBURST = "sunburst"
    TREEMAP = "treemap"
    FUNNEL = "funnel"
    SANKEY = "sankey"
    TABLE = "table"


class DataType(Enum):
    """Data type categories."""
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    DATETIME = "datetime"
    TEXT = "text"
    BOOLEAN = "boolean"


@dataclass
class VisualizationRequest:
    """Request for creating a visualization."""
    data: pd.DataFrame
    title: Optional[str] = None
    chart_type: Optional[ChartType] = None
    x_column: Optional[str] = None
    y_column: Optional[str] = None
    color_column: Optional[str] = None
    size_column: Optional[str] = None
    facet_column: Optional[str] = None
    aggregation: Optional[str] = None
    query_context: Optional[Dict[str, Any]] = None
    user_preferences: Optional[Dict[str, Any]] = None


@dataclass
class VisualizationResponse:
    """Response containing the generated visualization."""
    chart_html: str
    chart_json: str
    chart_config: Dict[str, Any]
    chart_type: ChartType
    insights: List[str]
    data_summary: Dict[str, Any]
    export_formats: Dict[str, str]  # format -> base64 encoded data
    metadata: Dict[str, Any]


@dataclass
class DataProfile:
    """Profile of a dataset for visualization recommendation."""
    column_count: int
    row_count: int
    numeric_columns: List[str]
    categorical_columns: List[str]
    datetime_columns: List[str]
    text_columns: List[str]
    column_types: Dict[str, DataType]
    column_stats: Dict[str, Dict[str, Any]]
    correlations: Optional[Dict[str, float]]
    null_counts: Dict[str, int]


class PlotlyVisualizationService:
    """Service for creating intelligent visualizations with Plotly."""
    
    def __init__(
        self,
        project_id: str,
        bucket_name: Optional[str] = None,
        theme: str = "plotly_white"
    ):
        """Initialize the visualization service.
        
        Args:
            project_id: GCP project ID
            bucket_name: GCS bucket for storing chart exports
            theme: Default Plotly theme
        """
        self.project_id = project_id
        self.bucket_name = bucket_name or f"{project_id}-visualizations"
        self.theme = theme
        
        # Initialize GCS client if bucket specified
        if bucket_name:
            self.storage_client = storage.Client(project=project_id)
        else:
            self.storage_client = None
        
        # Configure Plotly
        pio.templates.default = theme
        
        # Chart type mappings based on data characteristics
        self._load_chart_selection_rules()
        
        logger.info(f"Initialized PlotlyVisualizationService with theme: {theme}")
    
    def _load_chart_selection_rules(self) -> None:
        """Load rules for automatic chart type selection."""
        self.chart_rules = [
            # Single numeric column
            {
                "condition": lambda profile: len(profile.numeric_columns) == 1 and profile.row_count > 20,
                "chart_type": ChartType.HISTOGRAM,
                "priority": 1
            },
            # Two numeric columns
            {
                "condition": lambda profile: len(profile.numeric_columns) == 2,
                "chart_type": ChartType.SCATTER,
                "priority": 1
            },
            # Time series data
            {
                "condition": lambda profile: len(profile.datetime_columns) >= 1 and len(profile.numeric_columns) >= 1,
                "chart_type": ChartType.LINE,
                "priority": 1
            },
            # Single categorical with counts
            {
                "condition": lambda profile: len(profile.categorical_columns) == 1 and len(profile.numeric_columns) <= 1,
                "chart_type": ChartType.BAR,
                "priority": 2
            },
            # Categorical + numeric
            {
                "condition": lambda profile: len(profile.categorical_columns) >= 1 and len(profile.numeric_columns) >= 1,
                "chart_type": ChartType.BOX,
                "priority": 2
            },
            # High cardinality categorical
            {
                "condition": lambda profile: any(
                    stats.get("unique_count", 0) > 20 for stats in profile.column_stats.values()
                ),
                "chart_type": ChartType.TREEMAP,
                "priority": 3
            },
            # Default fallback
            {
                "condition": lambda profile: True,
                "chart_type": ChartType.TABLE,
                "priority": 10
            }
        ]
    
    def create_visualization(self, request: VisualizationRequest) -> VisualizationResponse:
        """Create a visualization from data and request parameters.
        
        Args:
            request: Visualization request with data and parameters
            
        Returns:
            Complete visualization response with chart and metadata
        """
        try:
            logger.info(f"Creating visualization for {len(request.data)} rows")
            
            # Profile the data
            data_profile = self._profile_data(request.data)
            
            # Determine chart type if not specified
            chart_type = request.chart_type or self._recommend_chart_type(data_profile, request)
            
            # Generate the chart
            fig = self._create_chart(request.data, chart_type, request, data_profile)
            
            # Apply styling and theming
            fig = self._apply_styling(fig, request)
            
            # Generate insights
            insights = self._generate_insights(request.data, data_profile, chart_type)
            
            # Export to various formats
            chart_html = fig.to_html(include_plotlyjs=True, div_id="chart")
            chart_json = fig.to_json()
            export_formats = self._generate_exports(fig)
            
            # Build response
            response = VisualizationResponse(
                chart_html=chart_html,
                chart_json=chart_json,
                chart_config=self._extract_chart_config(fig),
                chart_type=chart_type,
                insights=insights,
                data_summary=self._create_data_summary(data_profile),
                export_formats=export_formats,
                metadata={
                    "created_at": datetime.now().isoformat(),
                    "data_shape": request.data.shape,
                    "chart_type": chart_type.value,
                    "theme": self.theme,
                    "columns_used": self._get_columns_used(request)
                }
            )
            
            logger.info(f"Successfully created {chart_type.value} visualization")
            return response
            
        except Exception as e:
            logger.error(f"Failed to create visualization: {str(e)}")
            raise
    
    def _profile_data(self, data: pd.DataFrame) -> DataProfile:
        """Profile the dataset to understand its characteristics."""
        try:
            # Basic info
            row_count, column_count = data.shape
            
            # Identify column types
            numeric_columns = []
            categorical_columns = []
            datetime_columns = []
            text_columns = []
            column_types = {}
            column_stats = {}
            null_counts = {}
            
            for col in data.columns:
                null_count = data[col].isnull().sum()
                null_counts[col] = null_count
                
                # Determine column type
                if pd.api.types.is_numeric_dtype(data[col]):
                    numeric_columns.append(col)
                    column_types[col] = DataType.NUMERIC
                    column_stats[col] = {
                        "mean": data[col].mean(),
                        "median": data[col].median(),
                        "std": data[col].std(),
                        "min": data[col].min(),
                        "max": data[col].max(),
                        "unique_count": data[col].nunique()
                    }
                elif pd.api.types.is_datetime64_any_dtype(data[col]):
                    datetime_columns.append(col)
                    column_types[col] = DataType.DATETIME
                    column_stats[col] = {
                        "min_date": data[col].min(),
                        "max_date": data[col].max(),
                        "unique_count": data[col].nunique()
                    }
                elif pd.api.types.is_bool_dtype(data[col]):
                    categorical_columns.append(col)
                    column_types[col] = DataType.BOOLEAN
                    column_stats[col] = {
                        "true_count": data[col].sum(),
                        "false_count": len(data) - data[col].sum(),
                        "unique_count": data[col].nunique()
                    }
                else:
                    unique_count = data[col].nunique()
                    if unique_count / len(data) < 0.5:  # Less than 50% unique values
                        categorical_columns.append(col)
                        column_types[col] = DataType.CATEGORICAL
                    else:
                        text_columns.append(col)
                        column_types[col] = DataType.TEXT
                    
                    column_stats[col] = {
                        "unique_count": unique_count,
                        "most_common": data[col].value_counts().head(5).to_dict()
                    }
            
            # Calculate correlations for numeric columns
            correlations = None
            if len(numeric_columns) > 1:
                corr_matrix = data[numeric_columns].corr()
                correlations = {}
                for i, col1 in enumerate(numeric_columns):
                    for j, col2 in enumerate(numeric_columns):
                        if i < j:
                            correlations[f"{col1}_vs_{col2}"] = corr_matrix.loc[col1, col2]
            
            return DataProfile(
                column_count=column_count,
                row_count=row_count,
                numeric_columns=numeric_columns,
                categorical_columns=categorical_columns,
                datetime_columns=datetime_columns,
                text_columns=text_columns,
                column_types=column_types,
                column_stats=column_stats,
                correlations=correlations,
                null_counts=null_counts
            )
            
        except Exception as e:
            logger.error(f"Failed to profile data: {str(e)}")
            raise
    
    def _recommend_chart_type(self, profile: DataProfile, request: VisualizationRequest) -> ChartType:
        """Recommend the best chart type based on data profile and context."""
        try:
            # Apply rules in priority order
            applicable_rules = []
            for rule in self.chart_rules:
                if rule["condition"](profile):
                    applicable_rules.append(rule)
            
            # Sort by priority and return the best match
            if applicable_rules:
                best_rule = min(applicable_rules, key=lambda r: r["priority"])
                recommended_type = best_rule["chart_type"]
                
                # Consider query context for overrides
                if request.query_context:
                    context_override = self._get_context_chart_override(request.query_context, recommended_type)
                    if context_override:
                        recommended_type = context_override
                
                logger.info(f"Recommended chart type: {recommended_type.value}")
                return recommended_type
            else:
                return ChartType.TABLE
                
        except Exception as e:
            logger.warning(f"Chart recommendation failed, using table: {str(e)}")
            return ChartType.TABLE
    
    def _get_context_chart_override(self, context: Dict[str, Any], default: ChartType) -> Optional[ChartType]:
        """Override chart type based on query context."""
        query_text = context.get("natural_language_query", "").lower()
        
        # Context-based overrides
        if "trend" in query_text or "over time" in query_text:
            return ChartType.LINE
        elif "distribution" in query_text or "histogram" in query_text:
            return ChartType.HISTOGRAM
        elif "compare" in query_text or "comparison" in query_text:
            return ChartType.BAR
        elif "correlation" in query_text or "relationship" in query_text:
            return ChartType.SCATTER
        elif "proportion" in query_text or "percentage" in query_text:
            return ChartType.PIE
        
        return None
    
    def _create_chart(
        self, 
        data: pd.DataFrame, 
        chart_type: ChartType, 
        request: VisualizationRequest,
        profile: DataProfile
    ) -> go.Figure:
        """Create the actual chart based on type and parameters."""
        try:
            # Determine columns to use
            x_col, y_col, color_col = self._determine_columns(data, request, profile)
            
            if chart_type == ChartType.BAR:
                return self._create_bar_chart(data, x_col, y_col, color_col, request)
            elif chart_type == ChartType.LINE:
                return self._create_line_chart(data, x_col, y_col, color_col, request)
            elif chart_type == ChartType.SCATTER:
                return self._create_scatter_chart(data, x_col, y_col, color_col, request)
            elif chart_type == ChartType.PIE:
                return self._create_pie_chart(data, x_col, y_col, request)
            elif chart_type == ChartType.HISTOGRAM:
                return self._create_histogram(data, x_col, request)
            elif chart_type == ChartType.BOX:
                return self._create_box_plot(data, x_col, y_col, request)
            elif chart_type == ChartType.HEATMAP:
                return self._create_heatmap(data, request)
            elif chart_type == ChartType.AREA:
                return self._create_area_chart(data, x_col, y_col, color_col, request)
            elif chart_type == ChartType.TREEMAP:
                return self._create_treemap(data, x_col, y_col, request)
            elif chart_type == ChartType.TABLE:
                return self._create_table(data, request)
            else:
                # Fallback to table
                return self._create_table(data, request)
                
        except Exception as e:
            logger.error(f"Failed to create {chart_type.value} chart: {str(e)}")
            # Fallback to table
            return self._create_table(data, request)
    
    def _determine_columns(
        self, 
        data: pd.DataFrame, 
        request: VisualizationRequest, 
        profile: DataProfile
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Determine which columns to use for x, y, and color."""
        x_col = request.x_column
        y_col = request.y_column
        color_col = request.color_column
        
        # Auto-select columns if not specified
        if not x_col and profile.categorical_columns:
            x_col = profile.categorical_columns[0]
        elif not x_col and profile.datetime_columns:
            x_col = profile.datetime_columns[0]
        elif not x_col and profile.numeric_columns:
            x_col = profile.numeric_columns[0]
        
        if not y_col and profile.numeric_columns:
            # Find a numeric column different from x_col
            for col in profile.numeric_columns:
                if col != x_col:
                    y_col = col
                    break
        
        if not color_col and len(profile.categorical_columns) > 1:
            # Use a categorical column different from x_col
            for col in profile.categorical_columns:
                if col != x_col:
                    color_col = col
                    break
        
        return x_col, y_col, color_col
    
    def _create_bar_chart(
        self, 
        data: pd.DataFrame, 
        x_col: str, 
        y_col: Optional[str], 
        color_col: Optional[str],
        request: VisualizationRequest
    ) -> go.Figure:
        """Create a bar chart."""
        if y_col:
            # Aggregate data if needed
            if request.aggregation == "sum":
                plot_data = data.groupby(x_col)[y_col].sum().reset_index()
            elif request.aggregation == "mean":
                plot_data = data.groupby(x_col)[y_col].mean().reset_index()
            elif request.aggregation == "count":
                plot_data = data.groupby(x_col).size().reset_index(name='count')
                y_col = 'count'
            else:
                plot_data = data
            
            fig = px.bar(
                plot_data, 
                x=x_col, 
                y=y_col,
                color=color_col,
                title=request.title or f"{y_col} by {x_col}"
            )
        else:
            # Count plot
            value_counts = data[x_col].value_counts()
            fig = px.bar(
                x=value_counts.index,
                y=value_counts.values,
                title=request.title or f"Count of {x_col}"
            )
        
        return fig
    
    def _create_line_chart(
        self, 
        data: pd.DataFrame, 
        x_col: str, 
        y_col: str, 
        color_col: Optional[str],
        request: VisualizationRequest
    ) -> go.Figure:
        """Create a line chart."""
        fig = px.line(
            data, 
            x=x_col, 
            y=y_col,
            color=color_col,
            title=request.title or f"{y_col} over {x_col}"
        )
        return fig
    
    def _create_scatter_chart(
        self, 
        data: pd.DataFrame, 
        x_col: str, 
        y_col: str, 
        color_col: Optional[str],
        request: VisualizationRequest
    ) -> go.Figure:
        """Create a scatter plot."""
        fig = px.scatter(
            data, 
            x=x_col, 
            y=y_col,
            color=color_col,
            size=request.size_column,
            title=request.title or f"{y_col} vs {x_col}"
        )
        return fig
    
    def _create_pie_chart(
        self, 
        data: pd.DataFrame, 
        x_col: str, 
        y_col: Optional[str],
        request: VisualizationRequest
    ) -> go.Figure:
        """Create a pie chart."""
        if y_col:
            # Aggregate data
            plot_data = data.groupby(x_col)[y_col].sum()
        else:
            # Count data
            plot_data = data[x_col].value_counts()
        
        fig = px.pie(
            values=plot_data.values,
            names=plot_data.index,
            title=request.title or f"Distribution of {x_col}"
        )
        return fig
    
    def _create_histogram(
        self, 
        data: pd.DataFrame, 
        x_col: str,
        request: VisualizationRequest
    ) -> go.Figure:
        """Create a histogram."""
        fig = px.histogram(
            data, 
            x=x_col,
            title=request.title or f"Distribution of {x_col}"
        )
        return fig
    
    def _create_box_plot(
        self, 
        data: pd.DataFrame, 
        x_col: str, 
        y_col: str,
        request: VisualizationRequest
    ) -> go.Figure:
        """Create a box plot."""
        fig = px.box(
            data, 
            x=x_col, 
            y=y_col,
            title=request.title or f"{y_col} distribution by {x_col}"
        )
        return fig
    
    def _create_heatmap(
        self, 
        data: pd.DataFrame,
        request: VisualizationRequest
    ) -> go.Figure:
        """Create a correlation heatmap."""
        # Get numeric columns only
        numeric_data = data.select_dtypes(include=[np.number])
        correlation_matrix = numeric_data.corr()
        
        fig = px.imshow(
            correlation_matrix,
            title=request.title or "Correlation Heatmap",
            color_continuous_scale="RdBu"
        )
        return fig
    
    def _create_area_chart(
        self, 
        data: pd.DataFrame, 
        x_col: str, 
        y_col: str, 
        color_col: Optional[str],
        request: VisualizationRequest
    ) -> go.Figure:
        """Create an area chart."""
        fig = px.area(
            data, 
            x=x_col, 
            y=y_col,
            color=color_col,
            title=request.title or f"{y_col} over {x_col}"
        )
        return fig
    
    def _create_treemap(
        self, 
        data: pd.DataFrame, 
        x_col: str, 
        y_col: Optional[str],
        request: VisualizationRequest
    ) -> go.Figure:
        """Create a treemap."""
        if y_col:
            plot_data = data.groupby(x_col)[y_col].sum().reset_index()
            fig = px.treemap(
                plot_data,
                path=[x_col],
                values=y_col,
                title=request.title or f"Treemap of {y_col} by {x_col}"
            )
        else:
            value_counts = data[x_col].value_counts().reset_index()
            value_counts.columns = [x_col, 'count']
            fig = px.treemap(
                value_counts,
                path=[x_col],
                values='count',
                title=request.title or f"Treemap of {x_col}"
            )
        return fig
    
    def _create_table(
        self, 
        data: pd.DataFrame,
        request: VisualizationRequest
    ) -> go.Figure:
        """Create a table visualization."""
        # Limit to first 100 rows for display
        display_data = data.head(100)
        
        fig = go.Figure(data=[go.Table(
            header=dict(values=list(display_data.columns)),
            cells=dict(values=[display_data[col] for col in display_data.columns])
        )])
        
        fig.update_layout(title=request.title or "Data Table")
        return fig
    
    def _apply_styling(self, fig: go.Figure, request: VisualizationRequest) -> go.Figure:
        """Apply styling and theming to the chart."""
        # Update layout with better styling
        fig.update_layout(
            template=self.theme,
            font=dict(size=12),
            title_font_size=16,
            showlegend=True,
            height=500,
            margin=dict(l=50, r=50, t=50, b=50)
        )
        
        # Add user preferences if specified
        if request.user_preferences:
            if "height" in request.user_preferences:
                fig.update_layout(height=request.user_preferences["height"])
            if "color_scheme" in request.user_preferences:
                # Apply custom color scheme
                pass
        
        return fig
    
    def _generate_insights(
        self, 
        data: pd.DataFrame, 
        profile: DataProfile, 
        chart_type: ChartType
    ) -> List[str]:
        """Generate automatic insights about the data and visualization."""
        insights = []
        
        try:
            # Basic data insights
            insights.append(f"Dataset contains {profile.row_count:,} rows and {profile.column_count} columns")
            
            # Column type insights
            if profile.numeric_columns:
                insights.append(f"Found {len(profile.numeric_columns)} numeric columns: {', '.join(profile.numeric_columns[:3])}")
            
            if profile.categorical_columns:
                insights.append(f"Found {len(profile.categorical_columns)} categorical columns")
            
            # Data quality insights
            high_null_columns = [col for col, count in profile.null_counts.items() if count > profile.row_count * 0.1]
            if high_null_columns:
                insights.append(f"Columns with >10% missing values: {', '.join(high_null_columns)}")
            
            # Statistical insights for numeric data
            for col in profile.numeric_columns[:2]:  # Limit to first 2 columns
                stats = profile.column_stats.get(col, {})
                if stats:
                    insights.append(f"{col}: mean={stats.get('mean', 0):.2f}, std={stats.get('std', 0):.2f}")
            
            # Correlation insights
            if profile.correlations:
                strong_correlations = {k: v for k, v in profile.correlations.items() if abs(v) > 0.7}
                if strong_correlations:
                    insights.append(f"Strong correlations found: {list(strong_correlations.keys())[:2]}")
            
            return insights[:5]  # Limit to 5 insights
            
        except Exception as e:
            logger.warning(f"Failed to generate insights: {str(e)}")
            return ["Visualization created successfully"]
    
    def _create_data_summary(self, profile: DataProfile) -> Dict[str, Any]:
        """Create a summary of the data characteristics."""
        return {
            "rows": profile.row_count,
            "columns": profile.column_count,
            "numeric_columns": len(profile.numeric_columns),
            "categorical_columns": len(profile.categorical_columns),
            "datetime_columns": len(profile.datetime_columns),
            "missing_data": sum(profile.null_counts.values()),
            "data_types": {col: dtype.value for col, dtype in profile.column_types.items()}
        }
    
    def _generate_exports(self, fig: go.Figure) -> Dict[str, str]:
        """Generate chart in multiple export formats."""
        exports = {}
        
        try:
            # PNG export
            png_bytes = fig.to_image(format="png", width=800, height=600)
            exports["png"] = base64.b64encode(png_bytes).decode()
            
            # SVG export
            svg_string = fig.to_image(format="svg", width=800, height=600)
            exports["svg"] = base64.b64encode(svg_string).decode()
            
            # HTML export
            html_string = fig.to_html(include_plotlyjs=True)
            exports["html"] = base64.b64encode(html_string.encode()).decode()
            
        except Exception as e:
            logger.warning(f"Failed to generate some exports: {str(e)}")
        
        return exports
    
    def _extract_chart_config(self, fig: go.Figure) -> Dict[str, Any]:
        """Extract configuration from the figure."""
        return {
            "chart_type": "plotly",
            "data_traces": len(fig.data),
            "layout": {
                "title": fig.layout.title.text if fig.layout.title else None,
                "xaxis_title": fig.layout.xaxis.title.text if fig.layout.xaxis.title else None,
                "yaxis_title": fig.layout.yaxis.title.text if fig.layout.yaxis.title else None,
                "theme": self.theme
            }
        }
    
    def _get_columns_used(self, request: VisualizationRequest) -> List[str]:
        """Get list of columns used in the visualization."""
        columns_used = []
        if request.x_column:
            columns_used.append(request.x_column)
        if request.y_column:
            columns_used.append(request.y_column)
        if request.color_column:
            columns_used.append(request.color_column)
        if request.size_column:
            columns_used.append(request.size_column)
        return columns_used
    
    def save_chart_to_gcs(self, chart_html: str, filename: str) -> str:
        """Save chart HTML to Google Cloud Storage."""
        if not self.storage_client:
            raise ValueError("GCS client not initialized")
        
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(f"charts/{filename}")
            blob.upload_from_string(chart_html, content_type="text/html")
            
            return f"gs://{self.bucket_name}/charts/{filename}"
            
        except Exception as e:
            logger.error(f"Failed to save chart to GCS: {str(e)}")
            raise


# Example usage and testing
if __name__ == "__main__":
    # Example configuration
    PROJECT_ID = "your-project-id"
    
    # Initialize service
    service = PlotlyVisualizationService(PROJECT_ID)
    
    # Create sample data
    sample_data = pd.DataFrame({
        'category': ['A', 'B', 'C', 'D', 'E'] * 20,
        'value': np.random.normal(100, 15, 100),
        'date': pd.date_range('2023-01-01', periods=100),
        'group': np.random.choice(['X', 'Y'], 100)
    })
    
    # Create visualization request
    request = VisualizationRequest(
        data=sample_data,
        title="Sample Data Analysis",
        query_context={
            "natural_language_query": "Show me the distribution of values by category"
        }
    )
    
    try:
        # Generate visualization
        response = service.create_visualization(request)
        
        print(f"Chart type: {response.chart_type.value}")
        print(f"Insights: {response.insights}")
        print(f"Data summary: {response.data_summary}")
        print(f"Export formats available: {list(response.export_formats.keys())}")
        
        # Save HTML to file for testing
        with open("sample_chart.html", "w") as f:
            f.write(response.chart_html)
        print("Chart saved to sample_chart.html")
        
    except Exception as e:
        print(f"Error: {e}")