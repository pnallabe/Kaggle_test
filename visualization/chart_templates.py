"""Chart Templates and Automatic Selection System

This module provides intelligent chart templates and automatic chart type
selection based on data characteristics, query intent, and visualization best practices.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
from datetime import datetime
import re

from .plotly_service import ChartType, DataType, DataProfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VisualizationIntent(Enum):
    """Intent categories for visualizations."""
    COMPARISON = "comparison"
    DISTRIBUTION = "distribution"
    RELATIONSHIP = "relationship"
    COMPOSITION = "composition"
    TREND = "trend"
    RANKING = "ranking"
    PART_TO_WHOLE = "part_to_whole"
    DEVIATION = "deviation"
    GEOGRAPHIC = "geographic"
    FLOW = "flow"


@dataclass
class ChartTemplate:
    """Template definition for chart creation."""
    chart_type: ChartType
    intent: VisualizationIntent
    data_requirements: Dict[str, Any]
    recommended_conditions: List[Callable[[DataProfile], bool]]
    priority: int
    description: str
    best_practices: List[str]
    customization_options: Dict[str, Any]


@dataclass
class ChartRecommendation:
    """Recommendation for chart type with reasoning."""
    chart_type: ChartType
    intent: VisualizationIntent
    confidence_score: float
    reasoning: List[str]
    template: ChartTemplate
    suggested_columns: Dict[str, str]  # role -> column_name
    customizations: Dict[str, Any]


class ChartTemplateEngine:
    """Engine for chart template management and recommendation."""
    
    def __init__(self):
        """Initialize the chart template engine."""
        self.templates = {}
        self.intent_keywords = {}
        self._load_templates()
        self._load_intent_keywords()
        
        logger.info("Initialized ChartTemplateEngine with {} templates".format(
            len(self.templates)
        ))
    
    def _load_templates(self) -> None:
        """Load predefined chart templates."""
        self.templates = {
            # Comparison Charts
            ChartType.BAR: ChartTemplate(
                chart_type=ChartType.BAR,
                intent=VisualizationIntent.COMPARISON,
                data_requirements={
                    "min_categorical": 1,
                    "min_numeric": 0,
                    "max_categories": 20
                },
                recommended_conditions=[
                    lambda p: len(p.categorical_columns) >= 1,
                    lambda p: p.row_count < 1000,
                    lambda p: any(p.column_stats.get(col, {}).get("unique_count", 0) <= 20 
                                for col in p.categorical_columns)
                ],
                priority=1,
                description="Compare values across categories",
                best_practices=[
                    "Limit to 20 or fewer categories",
                    "Sort bars by value for better readability",
                    "Use horizontal bars for long category names",
                    "Consider color coding for subcategories"
                ],
                customization_options={
                    "orientation": ["vertical", "horizontal"],
                    "sort_by": ["value", "alphabetical", "custom"],
                    "color_scheme": ["categorical", "sequential"],
                    "show_values": True
                }
            ),
            
            # Distribution Charts
            ChartType.HISTOGRAM: ChartTemplate(
                chart_type=ChartType.HISTOGRAM,
                intent=VisualizationIntent.DISTRIBUTION,
                data_requirements={
                    "min_numeric": 1,
                    "min_rows": 10
                },
                recommended_conditions=[
                    lambda p: len(p.numeric_columns) >= 1,
                    lambda p: p.row_count >= 10,
                    lambda p: any(p.column_stats.get(col, {}).get("unique_count", 0) > 5 
                                for col in p.numeric_columns)
                ],
                priority=1,
                description="Show distribution of numeric values",
                best_practices=[
                    "Choose appropriate bin size",
                    "Consider log scale for skewed data",
                    "Add normal curve overlay if relevant",
                    "Use consistent bin widths"
                ],
                customization_options={
                    "bins": "auto",
                    "density": False,
                    "cumulative": False,
                    "overlay_curve": None
                }
            ),
            
            ChartType.BOX: ChartTemplate(
                chart_type=ChartType.BOX,
                intent=VisualizationIntent.DISTRIBUTION,
                data_requirements={
                    "min_numeric": 1,
                    "min_categorical": 1
                },
                recommended_conditions=[
                    lambda p: len(p.numeric_columns) >= 1 and len(p.categorical_columns) >= 1,
                    lambda p: any(p.column_stats.get(col, {}).get("unique_count", 0) <= 10 
                                for col in p.categorical_columns)
                ],
                priority=2,
                description="Compare distributions across categories",
                best_practices=[
                    "Limit categories to avoid clutter",
                    "Show outliers for data quality insights",
                    "Consider violin plots for detailed distributions",
                    "Order categories meaningfully"
                ],
                customization_options={
                    "show_outliers": True,
                    "notch": False,
                    "show_mean": False,
                    "orientation": "vertical"
                }
            ),
            
            # Relationship Charts
            ChartType.SCATTER: ChartTemplate(
                chart_type=ChartType.SCATTER,
                intent=VisualizationIntent.RELATIONSHIP,
                data_requirements={
                    "min_numeric": 2
                },
                recommended_conditions=[
                    lambda p: len(p.numeric_columns) >= 2,
                    lambda p: p.row_count <= 10000,  # Performance consideration
                    lambda p: p.correlations and any(abs(corr) > 0.3 for corr in p.correlations.values())
                ],
                priority=1,
                description="Show relationship between two numeric variables",
                best_practices=[
                    "Add trend line if correlation exists",
                    "Use transparency for overlapping points",
                    "Consider size mapping for third dimension",
                    "Add marginal plots for distributions"
                ],
                customization_options={
                    "trend_line": "ols",
                    "size_column": None,
                    "opacity": 0.7,
                    "marginal": None
                }
            ),
            
            # Trend Charts
            ChartType.LINE: ChartTemplate(
                chart_type=ChartType.LINE,
                intent=VisualizationIntent.TREND,
                data_requirements={
                    "min_datetime": 1,
                    "min_numeric": 1
                },
                recommended_conditions=[
                    lambda p: len(p.datetime_columns) >= 1,
                    lambda p: len(p.numeric_columns) >= 1,
                    lambda p: p.row_count >= 3  # Need at least 3 points for trend
                ],
                priority=1,
                description="Show trends over time",
                best_practices=[
                    "Ensure time axis is properly formatted",
                    "Use markers for sparse data",
                    "Consider multiple y-axes for different scales",
                    "Add annotations for important events"
                ],
                customization_options={
                    "markers": True,
                    "smooth_line": False,
                    "fill_area": False,
                    "multiple_series": True
                }
            ),
            
            ChartType.AREA: ChartTemplate(
                chart_type=ChartType.AREA,
                intent=VisualizationIntent.TREND,
                data_requirements={
                    "min_datetime": 1,
                    "min_numeric": 1
                },
                recommended_conditions=[
                    lambda p: len(p.datetime_columns) >= 1,
                    lambda p: len(p.numeric_columns) >= 1,
                    lambda p: all(p.column_stats.get(col, {}).get("min", 0) >= 0 
                                for col in p.numeric_columns)  # Non-negative values
                ],
                priority=2,
                description="Show cumulative trends over time",
                best_practices=[
                    "Use for cumulative or stacked data",
                    "Ensure all values are non-negative",
                    "Consider stacking for multiple series",
                    "Use transparency for overlapping areas"
                ],
                customization_options={
                    "stacked": False,
                    "normalize": False,
                    "opacity": 0.7
                }
            ),
            
            # Composition Charts
            ChartType.PIE: ChartTemplate(
                chart_type=ChartType.PIE,
                intent=VisualizationIntent.PART_TO_WHOLE,
                data_requirements={
                    "min_categorical": 1,
                    "max_categories": 8
                },
                recommended_conditions=[
                    lambda p: len(p.categorical_columns) >= 1,
                    lambda p: any(p.column_stats.get(col, {}).get("unique_count", 0) <= 8 
                                for col in p.categorical_columns),
                    lambda p: p.row_count >= 3
                ],
                priority=3,  # Lower priority, often not the best choice
                description="Show parts of a whole",
                best_practices=[
                    "Limit to 8 or fewer categories",
                    "Start largest slice at 12 o'clock",
                    "Consider donut chart for better readability",
                    "Avoid 3D effects"
                ],
                customization_options={
                    "donut": False,
                    "show_percentages": True,
                    "sort_by": "value",
                    "explode_largest": False
                }
            ),
            
            ChartType.TREEMAP: ChartTemplate(
                chart_type=ChartType.TREEMAP,
                intent=VisualizationIntent.COMPOSITION,
                data_requirements={
                    "min_categorical": 1,
                    "hierarchical": False
                },
                recommended_conditions=[
                    lambda p: len(p.categorical_columns) >= 1,
                    lambda p: any(p.column_stats.get(col, {}).get("unique_count", 0) > 8 
                                for col in p.categorical_columns),
                    lambda p: p.row_count >= 10
                ],
                priority=2,
                description="Show hierarchical composition with size encoding",
                best_practices=[
                    "Good for many categories",
                    "Use color for additional dimension",
                    "Ensure adequate space for labels",
                    "Consider drill-down capabilities"
                ],
                customization_options={
                    "color_scale": "sequential",
                    "show_labels": True,
                    "hierarchical": False
                }
            ),
            
            # Correlation Chart
            ChartType.HEATMAP: ChartTemplate(
                chart_type=ChartType.HEATMAP,
                intent=VisualizationIntent.RELATIONSHIP,
                data_requirements={
                    "min_numeric": 2,
                    "correlation_analysis": True
                },
                recommended_conditions=[
                    lambda p: len(p.numeric_columns) >= 3,
                    lambda p: p.correlations is not None,
                    lambda p: len(p.numeric_columns) <= 20  # Readability limit
                ],
                priority=2,
                description="Show correlation matrix between variables",
                best_practices=[
                    "Use diverging color scale",
                    "Include correlation coefficients",
                    "Order variables by similarity",
                    "Consider clustering for many variables"
                ],
                customization_options={
                    "color_scale": "RdBu",
                    "show_values": True,
                    "cluster": False,
                    "mask_diagonal": True
                }
            )
        }
    
    def _load_intent_keywords(self) -> None:
        """Load keywords that indicate visualization intent."""
        self.intent_keywords = {
            VisualizationIntent.COMPARISON: [
                "compare", "comparison", "versus", "vs", "difference", "better", "worse",
                "higher", "lower", "more", "less", "rank", "top", "bottom"
            ],
            VisualizationIntent.DISTRIBUTION: [
                "distribution", "spread", "range", "histogram", "frequency", "normal",
                "bell curve", "outliers", "quartile", "percentile", "median", "variation"
            ],
            VisualizationIntent.RELATIONSHIP: [
                "relationship", "correlation", "association", "connection", "related",
                "depends", "affects", "influence", "scatter", "pattern", "linear"
            ],
            VisualizationIntent.TREND: [
                "trend", "over time", "temporal", "change", "growth", "decline",
                "increase", "decrease", "progression", "evolution", "timeline", "series"
            ],
            VisualizationIntent.COMPOSITION: [
                "composition", "breakdown", "part", "whole", "proportion", "percentage",
                "share", "makeup", "constitute", "component", "segment"
            ],
            VisualizationIntent.RANKING: [
                "rank", "ranking", "order", "sort", "top", "bottom", "best", "worst",
                "highest", "lowest", "leading", "trailing", "first", "last"
            ]
        }
    
    def recommend_chart(
        self, 
        data_profile: DataProfile, 
        query_context: Optional[Dict[str, Any]] = None,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> List[ChartRecommendation]:
        """Recommend chart types based on data profile and context.
        
        Args:
            data_profile: Profile of the dataset
            query_context: Context from the original query
            user_preferences: User preferences and constraints
            
        Returns:
            List of chart recommendations ordered by confidence
        """
        try:
            recommendations = []
            
            # Detect intent from query context
            detected_intent = self._detect_intent(query_context)
            
            # Evaluate each template
            for chart_type, template in self.templates.items():
                # Check data requirements
                if not self._check_data_requirements(data_profile, template):
                    continue
                
                # Calculate confidence score
                confidence = self._calculate_confidence(
                    data_profile, template, detected_intent, query_context
                )
                
                if confidence > 0.1:  # Minimum threshold
                    # Generate reasoning
                    reasoning = self._generate_reasoning(
                        data_profile, template, detected_intent, confidence
                    )
                    
                    # Suggest column mappings
                    suggested_columns = self._suggest_columns(data_profile, template)
                    
                    # Generate customizations
                    customizations = self._suggest_customizations(
                        data_profile, template, user_preferences
                    )
                    
                    recommendation = ChartRecommendation(
                        chart_type=chart_type,
                        intent=template.intent,
                        confidence_score=confidence,
                        reasoning=reasoning,
                        template=template,
                        suggested_columns=suggested_columns,
                        customizations=customizations
                    )
                    
                    recommendations.append(recommendation)
            
            # Sort by confidence score
            recommendations.sort(key=lambda r: r.confidence_score, reverse=True)
            
            logger.info(f"Generated {len(recommendations)} chart recommendations")
            return recommendations[:5]  # Return top 5
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {str(e)}")
            return []
    
    def _detect_intent(self, query_context: Optional[Dict[str, Any]]) -> Optional[VisualizationIntent]:
        """Detect visualization intent from query context."""
        if not query_context or "natural_language_query" not in query_context:
            return None
        
        query_text = query_context["natural_language_query"].lower()
        
        # Score each intent based on keyword matches
        intent_scores = {}
        for intent, keywords in self.intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query_text)
            if score > 0:
                intent_scores[intent] = score
        
        # Return the highest scoring intent
        if intent_scores:
            return max(intent_scores, key=intent_scores.get)
        
        return None
    
    def _check_data_requirements(self, profile: DataProfile, template: ChartTemplate) -> bool:
        """Check if data meets template requirements."""
        requirements = template.data_requirements
        
        # Check minimum columns by type
        if requirements.get("min_numeric", 0) > len(profile.numeric_columns):
            return False
        
        if requirements.get("min_categorical", 0) > len(profile.categorical_columns):
            return False
        
        if requirements.get("min_datetime", 0) > len(profile.datetime_columns):
            return False
        
        # Check maximum categories
        if "max_categories" in requirements:
            max_cats = requirements["max_categories"]
            if any(profile.column_stats.get(col, {}).get("unique_count", 0) > max_cats 
                   for col in profile.categorical_columns):
                return False
        
        # Check minimum rows
        if requirements.get("min_rows", 0) > profile.row_count:
            return False
        
        return True
    
    def _calculate_confidence(
        self, 
        profile: DataProfile, 
        template: ChartTemplate, 
        detected_intent: Optional[VisualizationIntent],
        query_context: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate confidence score for a template."""
        confidence = 0.0
        
        # Base confidence from template priority (inverse)
        confidence += (5 - template.priority) * 0.2
        
        # Bonus for matching intent
        if detected_intent and detected_intent == template.intent:
            confidence += 0.4
        
        # Check recommended conditions
        conditions_met = sum(1 for condition in template.recommended_conditions 
                           if condition(profile))
        condition_score = conditions_met / len(template.recommended_conditions)
        confidence += condition_score * 0.3
        
        # Data fit bonus
        data_fit = self._calculate_data_fit(profile, template)
        confidence += data_fit * 0.1
        
        # Penalize if data is too large for chart type
        if template.chart_type in [ChartType.SCATTER, ChartType.PIE] and profile.row_count > 1000:
            confidence -= 0.2
        
        return max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
    
    def _calculate_data_fit(self, profile: DataProfile, template: ChartTemplate) -> float:
        """Calculate how well the data fits the template."""
        fit_score = 0.0
        
        # Perfect matches get higher scores
        if template.chart_type == ChartType.SCATTER and len(profile.numeric_columns) == 2:
            fit_score += 0.8
        elif template.chart_type == ChartType.LINE and len(profile.datetime_columns) == 1:
            fit_score += 0.8
        elif template.chart_type == ChartType.BAR and len(profile.categorical_columns) == 1:
            fit_score += 0.6
        
        # Data quality considerations
        if profile.null_counts:
            total_nulls = sum(profile.null_counts.values())
            null_rate = total_nulls / (profile.row_count * profile.column_count)
            if null_rate < 0.05:  # Less than 5% missing data
                fit_score += 0.2
        
        return min(1.0, fit_score)
    
    def _generate_reasoning(
        self, 
        profile: DataProfile, 
        template: ChartTemplate, 
        detected_intent: Optional[VisualizationIntent],
        confidence: float
    ) -> List[str]:
        """Generate human-readable reasoning for the recommendation."""
        reasoning = []
        
        # Base reasoning
        reasoning.append(f"Recommended for {template.intent.value} visualization")
        
        # Data-based reasoning
        if template.chart_type == ChartType.BAR:
            reasoning.append(f"Good for comparing {len(profile.categorical_columns)} categorical variable(s)")
        elif template.chart_type == ChartType.SCATTER:
            reasoning.append(f"Shows relationship between {len(profile.numeric_columns)} numeric variables")
        elif template.chart_type == ChartType.LINE:
            reasoning.append(f"Ideal for time series with {len(profile.datetime_columns)} date column(s)")
        elif template.chart_type == ChartType.HISTOGRAM:
            reasoning.append(f"Shows distribution of numeric data ({profile.row_count} data points)")
        
        # Intent matching
        if detected_intent and detected_intent == template.intent:
            reasoning.append("Matches detected query intent")
        
        # Confidence explanation
        if confidence > 0.8:
            reasoning.append("High confidence recommendation")
        elif confidence > 0.6:
            reasoning.append("Good fit for your data")
        else:
            reasoning.append("Alternative visualization option")
        
        return reasoning
    
    def _suggest_columns(self, profile: DataProfile, template: ChartTemplate) -> Dict[str, str]:
        """Suggest column mappings for the template."""
        suggestions = {}
        
        if template.chart_type in [ChartType.BAR, ChartType.PIE]:
            if profile.categorical_columns:
                suggestions["x"] = profile.categorical_columns[0]
            if profile.numeric_columns:
                suggestions["y"] = profile.numeric_columns[0]
                
        elif template.chart_type == ChartType.SCATTER:
            if len(profile.numeric_columns) >= 2:
                suggestions["x"] = profile.numeric_columns[0]
                suggestions["y"] = profile.numeric_columns[1]
            if profile.categorical_columns:
                suggestions["color"] = profile.categorical_columns[0]
                
        elif template.chart_type == ChartType.LINE:
            if profile.datetime_columns:
                suggestions["x"] = profile.datetime_columns[0]
            if profile.numeric_columns:
                suggestions["y"] = profile.numeric_columns[0]
            if len(profile.categorical_columns) > 0:
                suggestions["color"] = profile.categorical_columns[0]
                
        elif template.chart_type == ChartType.HISTOGRAM:
            if profile.numeric_columns:
                suggestions["x"] = profile.numeric_columns[0]
                
        elif template.chart_type == ChartType.BOX:
            if profile.categorical_columns:
                suggestions["x"] = profile.categorical_columns[0]
            if profile.numeric_columns:
                suggestions["y"] = profile.numeric_columns[0]
        
        return suggestions
    
    def _suggest_customizations(
        self, 
        profile: DataProfile, 
        template: ChartTemplate,
        user_preferences: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Suggest customizations based on data characteristics."""
        customizations = template.customization_options.copy()
        
        # Data-driven customizations
        if template.chart_type == ChartType.BAR:
            # Use horizontal bars for long category names
            if profile.categorical_columns:
                col = profile.categorical_columns[0]
                if col in profile.column_stats:
                    # This is a simplified check - in practice, you'd analyze text length
                    if profile.column_stats[col].get("unique_count", 0) > 10:
                        customizations["orientation"] = "horizontal"
        
        elif template.chart_type == ChartType.SCATTER:
            # Use transparency for large datasets
            if profile.row_count > 1000:
                customizations["opacity"] = 0.5
            # Add trend line if strong correlation
            if profile.correlations:
                max_corr = max(abs(corr) for corr in profile.correlations.values())
                if max_corr > 0.7:
                    customizations["trend_line"] = "ols"
        
        elif template.chart_type == ChartType.HISTOGRAM:
            # Adjust bins based on data size
            if profile.row_count < 50:
                customizations["bins"] = 10
            elif profile.row_count > 1000:
                customizations["bins"] = 50
        
        # Apply user preferences
        if user_preferences:
            customizations.update(user_preferences)
        
        return customizations
    
    def get_template(self, chart_type: ChartType) -> Optional[ChartTemplate]:
        """Get template for a specific chart type."""
        return self.templates.get(chart_type)
    
    def get_templates_by_intent(self, intent: VisualizationIntent) -> List[ChartTemplate]:
        """Get all templates for a specific intent."""
        return [template for template in self.templates.values() 
                if template.intent == intent]
    
    def validate_chart_config(
        self, 
        chart_type: ChartType, 
        data_profile: DataProfile, 
        config: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Validate a chart configuration against best practices."""
        template = self.get_template(chart_type)
        if not template:
            return False, ["Unknown chart type"]
        
        warnings = []
        
        # Check data requirements
        if not self._check_data_requirements(data_profile, template):
            warnings.append("Data doesn't meet chart requirements")
        
        # Chart-specific validations
        if chart_type == ChartType.PIE:
            categories = config.get("categories", 0)
            if categories > 8:
                warnings.append("Pie charts with >8 categories are hard to read")
        
        elif chart_type == ChartType.SCATTER:
            if data_profile.row_count > 10000:
                warnings.append("Large datasets may cause performance issues")
        
        elif chart_type == ChartType.BAR:
            categories = config.get("categories", 0)
            if categories > 20:
                warnings.append("Too many categories may cause clutter")
        
        is_valid = len(warnings) == 0
        return is_valid, warnings


# Example usage and testing
if __name__ == "__main__":
    # Initialize template engine
    engine = ChartTemplateEngine()
    
    # Create sample data profile
    sample_profile = DataProfile(
        column_count=4,
        row_count=1000,
        numeric_columns=["sales", "profit"],
        categorical_columns=["category", "region"],
        datetime_columns=["date"],
        text_columns=[],
        column_types={
            "sales": DataType.NUMERIC,
            "profit": DataType.NUMERIC,
            "category": DataType.CATEGORICAL,
            "region": DataType.CATEGORICAL,
            "date": DataType.DATETIME
        },
        column_stats={
            "sales": {"mean": 1000, "std": 200, "unique_count": 800},
            "category": {"unique_count": 5},
            "region": {"unique_count": 4}
        },
        correlations={"sales_vs_profit": 0.8},
        null_counts={"sales": 0, "profit": 2, "category": 0, "region": 0, "date": 0}
    )
    
    # Test recommendations
    query_context = {
        "natural_language_query": "Show me sales trends over time by region"
    }
    
    recommendations = engine.recommend_chart(sample_profile, query_context)
    
    print("Chart Recommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec.chart_type.value.upper()}")
        print(f"   Intent: {rec.intent.value}")
        print(f"   Confidence: {rec.confidence_score:.2f}")
        print(f"   Reasoning: {', '.join(rec.reasoning)}")
        print(f"   Columns: {rec.suggested_columns}")
    
    # Test template retrieval
    bar_template = engine.get_template(ChartType.BAR)
    if bar_template:
        print(f"\nBar Chart Template:")
        print(f"Description: {bar_template.description}")
        print(f"Best Practices: {bar_template.best_practices[:2]}")
        
    # Test validation
    is_valid, warnings = engine.validate_chart_config(
        ChartType.PIE, 
        sample_profile, 
        {"categories": 12}
    )
    print(f"\nValidation: {'Valid' if is_valid else 'Invalid'}")
    if warnings:
        print(f"Warnings: {warnings}")