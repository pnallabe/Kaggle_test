"""AI Narrative Generation Service

This module provides AI-powered insight generation and data storytelling
capabilities using Vertex AI LLM for automated narrative creation from data.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import numpy as np
from scipy import stats
import vertexai
from vertexai.language_models import TextGenerationModel
from vertexai.generative_models import GenerativeModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InsightType(Enum):
    """Types of insights that can be generated."""
    TREND = "trend"
    ANOMALY = "anomaly"
    CORRELATION = "correlation"
    DISTRIBUTION = "distribution"
    COMPARISON = "comparison"
    FORECAST = "forecast"
    SUMMARY = "summary"
    RECOMMENDATION = "recommendation"


class NarrativeStyle(Enum):
    """Styles for narrative generation."""
    EXECUTIVE = "executive"  # High-level, business-focused
    TECHNICAL = "technical"  # Detailed, analytical
    CASUAL = "casual"       # Easy to understand, conversational
    FORMAL = "formal"       # Professional, structured


@dataclass
class DataInsight:
    """Structure for individual data insights."""
    insight_id: str
    insight_type: InsightType
    title: str
    summary: str
    detailed_analysis: str
    confidence_score: float
    supporting_data: Dict[str, Any]
    statistical_measures: Dict[str, float]
    recommendations: List[str]
    context: Dict[str, Any]


@dataclass
class NarrativeConfig:
    """Configuration for narrative generation."""
    style: NarrativeStyle
    target_audience: str
    length: str  # "brief", "standard", "detailed"
    include_statistics: bool
    include_recommendations: bool
    focus_areas: List[str]
    tone: str  # "positive", "neutral", "analytical"


@dataclass
class GeneratedNarrative:
    """Complete generated narrative with insights."""
    narrative_id: str
    title: str
    executive_summary: str
    key_insights: List[DataInsight]
    detailed_narrative: str
    visualization_recommendations: List[Dict[str, Any]]
    action_items: List[str]
    metadata: Dict[str, Any]
    generated_at: datetime


class NarrativeGenerator:
    """AI-powered narrative generation service."""
    
    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        model_name: str = "gemini-1.5-pro"
    ):
        """Initialize the narrative generator.
        
        Args:
            project_id: GCP project ID
            location: GCP location
            model_name: Vertex AI model name
        """
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)
        
        # Initialize the model
        self.model = GenerativeModel(model_name)
        
        # Statistical analysis thresholds
        self.significance_threshold = 0.05
        self.correlation_threshold = 0.5
        self.trend_threshold = 0.1
        
        logger.info(f"Initialized NarrativeGenerator with model {model_name}")
    
    def generate_narrative_from_data(
        self,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
        query_context: Dict[str, Any],
        config: Optional[NarrativeConfig] = None
    ) -> GeneratedNarrative:
        """Generate complete narrative from data.
        
        Args:
            data: Data to analyze (DataFrame or list of dicts)
            query_context: Context about the original query
            config: Narrative configuration
            
        Returns:
            Generated narrative with insights
        """
        try:
            logger.info("Generating narrative from data")
            
            # Convert data to DataFrame if needed
            if isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = data.copy()
            
            # Set default configuration
            if config is None:
                config = NarrativeConfig(
                    style=NarrativeStyle.EXECUTIVE,
                    target_audience="business_stakeholders",
                    length="standard",
                    include_statistics=True,
                    include_recommendations=True,
                    focus_areas=[],
                    tone="analytical"
                )
            
            # Perform statistical analysis
            insights = self._analyze_data_for_insights(df, query_context)
            
            # Generate narrative components
            title = self._generate_title(df, query_context, insights)
            executive_summary = self._generate_executive_summary(insights, config)
            detailed_narrative = self._generate_detailed_narrative(df, insights, config)
            viz_recommendations = self._generate_visualization_recommendations(df, insights)
            action_items = self._generate_action_items(insights, config)
            
            # Create narrative object
            narrative = GeneratedNarrative(
                narrative_id=f"narrative_{uuid.uuid4().hex[:12]}",
                title=title,
                executive_summary=executive_summary,
                key_insights=insights,
                detailed_narrative=detailed_narrative,
                visualization_recommendations=viz_recommendations,
                action_items=action_items,
                metadata={
                    "data_shape": df.shape,
                    "query_context": query_context,
                    "config": config.__dict__,
                    "model_used": self.model_name
                },
                generated_at=datetime.now()
            )
            
            logger.info(f"Generated narrative: {narrative.narrative_id}")
            return narrative
            
        except Exception as e:
            logger.error(f"Failed to generate narrative: {str(e)}")
            raise
    
    def _analyze_data_for_insights(
        self, 
        df: pd.DataFrame, 
        context: Dict[str, Any]
    ) -> List[DataInsight]:
        """Perform statistical analysis to identify insights."""
        insights = []
        
        # Identify numeric and categorical columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        date_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
        
        # Trend analysis (if date column exists)
        if date_cols and numeric_cols:
            trend_insights = self._analyze_trends(df, date_cols[0], numeric_cols)
            insights.extend(trend_insights)
        
        # Distribution analysis
        if numeric_cols:
            distribution_insights = self._analyze_distributions(df, numeric_cols)
            insights.extend(distribution_insights)
        
        # Correlation analysis
        if len(numeric_cols) >= 2:
            correlation_insights = self._analyze_correlations(df, numeric_cols)
            insights.extend(correlation_insights)
        
        # Categorical analysis
        if categorical_cols and numeric_cols:
            comparison_insights = self._analyze_categorical_comparisons(
                df, categorical_cols, numeric_cols
            )
            insights.extend(comparison_insights)
        
        # Anomaly detection
        if numeric_cols:
            anomaly_insights = self._detect_anomalies(df, numeric_cols)
            insights.extend(anomaly_insights)
        
        # Summary statistics
        summary_insight = self._generate_summary_insight(df, context)
        insights.append(summary_insight)
        
        return insights
    
    def _analyze_trends(
        self, 
        df: pd.DataFrame, 
        date_col: str, 
        numeric_cols: List[str]
    ) -> List[DataInsight]:
        """Analyze trends in time series data."""
        insights = []
        
        for col in numeric_cols:
            try:
                # Sort by date
                df_sorted = df.sort_values(date_col)
                
                # Calculate trend using linear regression
                x = np.arange(len(df_sorted))
                y = df_sorted[col].dropna()
                
                if len(y) > 3:
                    slope, intercept, r_value, p_value, std_err = stats.linregress(
                        x[:len(y)], y
                    )
                    
                    # Determine trend direction and significance
                    if abs(slope) > self.trend_threshold and p_value < self.significance_threshold:
                        trend_direction = "increasing" if slope > 0 else "decreasing"
                        trend_strength = "strong" if abs(r_value) > 0.7 else "moderate"
                        
                        insight = DataInsight(
                            insight_id=f"trend_{col}_{uuid.uuid4().hex[:8]}",
                            insight_type=InsightType.TREND,
                            title=f"{col.title()} Shows {trend_strength.title()} {trend_direction.title()} Trend",
                            summary=f"{col} has a {trend_strength} {trend_direction} trend over time with R² = {r_value**2:.3f}",
                            detailed_analysis=f"Statistical analysis reveals a {trend_direction} trend in {col} with a slope of {slope:.4f} per time unit. The correlation coefficient is {r_value:.3f}, indicating a {trend_strength} linear relationship. This trend is statistically significant (p-value: {p_value:.4f}).",
                            confidence_score=1 - p_value,
                            supporting_data={
                                "slope": slope,
                                "r_squared": r_value**2,
                                "p_value": p_value,
                                "data_points": len(y)
                            },
                            statistical_measures={
                                "slope": slope,
                                "correlation": r_value,
                                "significance": p_value,
                                "r_squared": r_value**2
                            },
                            recommendations=[
                                f"Monitor {col} closely as it shows a clear {trend_direction} pattern",
                                f"Consider forecasting future values based on this {trend_strength} trend"
                            ],
                            context={"column": col, "date_column": date_col}
                        )
                        insights.append(insight)
                        
            except Exception as e:
                logger.warning(f"Failed to analyze trend for {col}: {str(e)}")
        
        return insights
    
    def _analyze_distributions(
        self, 
        df: pd.DataFrame, 
        numeric_cols: List[str]
    ) -> List[DataInsight]:
        """Analyze data distributions."""
        insights = []
        
        for col in numeric_cols:
            try:
                data = df[col].dropna()
                if len(data) > 10:
                    # Calculate distribution statistics
                    mean_val = data.mean()
                    median_val = data.median()
                    std_val = data.std()
                    skewness = stats.skew(data)
                    kurtosis = stats.kurtosis(data)
                    
                    # Identify distribution characteristics
                    distribution_type = "normal"
                    if abs(skewness) > 1:
                        distribution_type = "heavily skewed"
                    elif abs(skewness) > 0.5:
                        distribution_type = "moderately skewed"
                    
                    skew_direction = "right" if skewness > 0 else "left"
                    
                    insight = DataInsight(
                        insight_id=f"dist_{col}_{uuid.uuid4().hex[:8]}",
                        insight_type=InsightType.DISTRIBUTION,
                        title=f"{col.title()} Distribution Analysis",
                        summary=f"{col} has a {distribution_type} distribution with mean {mean_val:.2f} and median {median_val:.2f}",
                        detailed_analysis=f"The distribution of {col} shows: Mean = {mean_val:.2f}, Median = {median_val:.2f}, Standard Deviation = {std_val:.2f}. Skewness = {skewness:.3f} indicates {distribution_type} distribution skewed to the {skew_direction}. Kurtosis = {kurtosis:.3f}.",
                        confidence_score=0.8,
                        supporting_data={
                            "mean": mean_val,
                            "median": median_val,
                            "std": std_val,
                            "min": data.min(),
                            "max": data.max(),
                            "quartiles": data.quantile([0.25, 0.5, 0.75]).tolist()
                        },
                        statistical_measures={
                            "skewness": skewness,
                            "kurtosis": kurtosis,
                            "variance": data.var(),
                            "coefficient_of_variation": std_val / mean_val if mean_val != 0 else 0
                        },
                        recommendations=[
                            f"Consider outlier analysis for {col}" if abs(skewness) > 1 else f"{col} shows normal distribution characteristics",
                            f"Use median as central tendency measure" if abs(skewness) > 0.5 else f"Mean and median are similar for {col}"
                        ],
                        context={"column": col, "distribution_type": distribution_type}
                    )
                    insights.append(insight)
                    
            except Exception as e:
                logger.warning(f"Failed to analyze distribution for {col}: {str(e)}")
        
        return insights
    
    def _analyze_correlations(
        self, 
        df: pd.DataFrame, 
        numeric_cols: List[str]
    ) -> List[DataInsight]:
        """Analyze correlations between numeric columns."""
        insights = []
        
        try:
            # Calculate correlation matrix
            corr_matrix = df[numeric_cols].corr()
            
            # Find significant correlations
            for i, col1 in enumerate(numeric_cols):
                for j, col2 in enumerate(numeric_cols[i+1:], i+1):
                    correlation = corr_matrix.loc[col1, col2]
                    
                    if abs(correlation) > self.correlation_threshold:
                        # Calculate statistical significance
                        n = len(df[[col1, col2]].dropna())
                        t_stat = correlation * np.sqrt((n-2)/(1-correlation**2))
                        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n-2))
                        
                        if p_value < self.significance_threshold:
                            correlation_strength = "strong" if abs(correlation) > 0.7 else "moderate"
                            correlation_direction = "positive" if correlation > 0 else "negative"
                            
                            insight = DataInsight(
                                insight_id=f"corr_{col1}_{col2}_{uuid.uuid4().hex[:8]}",
                                insight_type=InsightType.CORRELATION,
                                title=f"{correlation_strength.title()} {correlation_direction.title()} Correlation: {col1.title()} and {col2.title()}",
                                summary=f"{col1} and {col2} show a {correlation_strength} {correlation_direction} correlation (r = {correlation:.3f})",
                                detailed_analysis=f"Statistical analysis reveals a {correlation_strength} {correlation_direction} correlation between {col1} and {col2} with correlation coefficient r = {correlation:.3f}. This relationship is statistically significant (p-value: {p_value:.4f}, n = {n}).",
                                confidence_score=1 - p_value,
                                supporting_data={
                                    "correlation": correlation,
                                    "p_value": p_value,
                                    "sample_size": n,
                                    "variable_1": col1,
                                    "variable_2": col2
                                },
                                statistical_measures={
                                    "correlation_coefficient": correlation,
                                    "significance": p_value,
                                    "degrees_of_freedom": n-2
                                },
                                recommendations=[
                                    f"Investigate the relationship between {col1} and {col2}",
                                    f"Consider using {col1} to predict {col2}" if correlation > 0.6 else f"Monitor both {col1} and {col2} together"
                                ],
                                context={"column_1": col1, "column_2": col2}
                            )
                            insights.append(insight)
                            
        except Exception as e:
            logger.warning(f"Failed to analyze correlations: {str(e)}")
        
        return insights
    
    def _analyze_categorical_comparisons(
        self, 
        df: pd.DataFrame, 
        categorical_cols: List[str], 
        numeric_cols: List[str]
    ) -> List[DataInsight]:
        """Analyze comparisons across categorical variables."""
        insights = []
        
        for cat_col in categorical_cols[:2]:  # Limit to first 2 categorical columns
            for num_col in numeric_cols[:2]:  # Limit to first 2 numeric columns
                try:
                    # Group by categorical column and analyze numeric column
                    groups = df.groupby(cat_col)[num_col]
                    group_stats = groups.agg(['mean', 'std', 'count']).fillna(0)
                    
                    if len(group_stats) > 1:
                        # Find the category with highest and lowest mean
                        max_group = group_stats['mean'].idxmax()
                        min_group = group_stats['mean'].idxmin()
                        max_value = group_stats.loc[max_group, 'mean']
                        min_value = group_stats.loc[min_group, 'mean']
                        
                        # Calculate percentage difference
                        pct_diff = ((max_value - min_value) / min_value * 100) if min_value != 0 else 0
                        
                        # Perform ANOVA test if more than 2 groups
                        if len(group_stats) > 2:
                            group_data = [group.dropna() for name, group in groups if len(group.dropna()) > 0]
                            if len(group_data) > 2:
                                f_stat, p_value = stats.f_oneway(*group_data)
                                is_significant = p_value < self.significance_threshold
                            else:
                                is_significant = False
                                p_value = 1.0
                        else:
                            # t-test for 2 groups
                            group1 = groups.get_group(max_group).dropna()
                            group2 = groups.get_group(min_group).dropna()
                            if len(group1) > 0 and len(group2) > 0:
                                t_stat, p_value = stats.ttest_ind(group1, group2)
                                is_significant = p_value < self.significance_threshold
                            else:
                                is_significant = False
                                p_value = 1.0
                        
                        if is_significant and abs(pct_diff) > 20:  # Only report significant differences > 20%
                            insight = DataInsight(
                                insight_id=f"comp_{cat_col}_{num_col}_{uuid.uuid4().hex[:8]}",
                                insight_type=InsightType.COMPARISON,
                                title=f"Significant Difference in {num_col.title()} Across {cat_col.title()} Categories",
                                summary=f"{max_group} has {pct_diff:.1f}% higher {num_col} than {min_group} ({max_value:.2f} vs {min_value:.2f})",
                                detailed_analysis=f"Analysis of {num_col} across {cat_col} categories reveals significant differences. {max_group} shows the highest average {num_col} at {max_value:.2f}, while {min_group} has the lowest at {min_value:.2f}, representing a {pct_diff:.1f}% difference. This difference is statistically significant (p-value: {p_value:.4f}).",
                                confidence_score=1 - p_value,
                                supporting_data={
                                    "highest_category": max_group,
                                    "lowest_category": min_group,
                                    "highest_value": max_value,
                                    "lowest_value": min_value,
                                    "percentage_difference": pct_diff,
                                    "group_statistics": group_stats.to_dict()
                                },
                                statistical_measures={
                                    "p_value": p_value,
                                    "effect_size": pct_diff / 100,
                                    "groups_count": len(group_stats)
                                },
                                recommendations=[
                                    f"Investigate why {max_group} performs better in {num_col}",
                                    f"Consider strategies to improve {num_col} for {min_group}"
                                ],
                                context={
                                    "categorical_column": cat_col,
                                    "numeric_column": num_col
                                }
                            )
                            insights.append(insight)
                            
                except Exception as e:
                    logger.warning(f"Failed to analyze comparison {cat_col} vs {num_col}: {str(e)}")
        
        return insights
    
    def _detect_anomalies(
        self, 
        df: pd.DataFrame, 
        numeric_cols: List[str]
    ) -> List[DataInsight]:
        """Detect anomalies in numeric data."""
        insights = []
        
        for col in numeric_cols:
            try:
                data = df[col].dropna()
                if len(data) > 10:
                    # Use IQR method for anomaly detection
                    Q1 = data.quantile(0.25)
                    Q3 = data.quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR
                    
                    anomalies = data[(data < lower_bound) | (data > upper_bound)]
                    anomaly_count = len(anomalies)
                    anomaly_percentage = (anomaly_count / len(data)) * 100
                    
                    if anomaly_count > 0 and anomaly_percentage > 1:  # Only report if > 1% anomalies
                        insight = DataInsight(
                            insight_id=f"anom_{col}_{uuid.uuid4().hex[:8]}",
                            insight_type=InsightType.ANOMALY,
                            title=f"Anomalies Detected in {col.title()}",
                            summary=f"Found {anomaly_count} anomalies in {col} ({anomaly_percentage:.1f}% of data)",
                            detailed_analysis=f"Anomaly detection using IQR method identified {anomaly_count} outliers in {col}. These represent {anomaly_percentage:.1f}% of the data points. Anomalies range from {anomalies.min():.2f} to {anomalies.max():.2f}, while normal range is {lower_bound:.2f} to {upper_bound:.2f}.",
                            confidence_score=min(0.9, anomaly_percentage / 10),  # Higher percentage = higher confidence
                            supporting_data={
                                "anomaly_count": anomaly_count,
                                "anomaly_percentage": anomaly_percentage,
                                "anomaly_values": anomalies.tolist()[:10],  # First 10 anomalies
                                "normal_range": [lower_bound, upper_bound],
                                "quartiles": [Q1, Q3]
                            },
                            statistical_measures={
                                "iqr": IQR,
                                "lower_bound": lower_bound,
                                "upper_bound": upper_bound
                            },
                            recommendations=[
                                f"Investigate the {anomaly_count} anomalous values in {col}",
                                f"Consider data cleaning or separate analysis for outliers"
                            ],
                            context={"column": col}
                        )
                        insights.append(insight)
                        
            except Exception as e:
                logger.warning(f"Failed to detect anomalies for {col}: {str(e)}")
        
        return insights
    
    def _generate_summary_insight(
        self, 
        df: pd.DataFrame, 
        context: Dict[str, Any]
    ) -> DataInsight:
        """Generate overall summary insight."""
        try:
            # Basic data characteristics
            row_count = len(df)
            col_count = len(df.columns)
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            
            # Calculate completeness
            completeness = (df.count().sum() / (row_count * col_count)) * 100
            
            summary_text = f"Dataset contains {row_count:,} rows and {col_count} columns"
            if numeric_cols:
                summary_text += f" with {len(numeric_cols)} numeric variables"
            if categorical_cols:
                summary_text += f" and {len(categorical_cols)} categorical variables"
            
            return DataInsight(
                insight_id=f"summary_{uuid.uuid4().hex[:8]}",
                insight_type=InsightType.SUMMARY,
                title="Dataset Overview",
                summary=summary_text,
                detailed_analysis=f"The dataset comprises {row_count:,} observations across {col_count} variables. Data completeness is {completeness:.1f}%. The dataset includes {len(numeric_cols)} numeric columns ({', '.join(numeric_cols[:5])}) and {len(categorical_cols)} categorical columns ({', '.join(categorical_cols[:5])}).",
                confidence_score=1.0,
                supporting_data={
                    "row_count": row_count,
                    "column_count": col_count,
                    "numeric_columns": numeric_cols,
                    "categorical_columns": categorical_cols,
                    "completeness_percentage": completeness
                },
                statistical_measures={
                    "completeness": completeness / 100,
                    "density": df.count().sum(),
                    "sparsity": df.isnull().sum().sum()
                },
                recommendations=[
                    "Review data quality and completeness",
                    "Consider additional data sources if completeness is low"
                ],
                context=context
            )
            
        except Exception as e:
            logger.warning(f"Failed to generate summary insight: {str(e)}")
            return DataInsight(
                insight_id=f"summary_{uuid.uuid4().hex[:8]}",
                insight_type=InsightType.SUMMARY,
                title="Dataset Overview",
                summary="Basic dataset summary",
                detailed_analysis="Dataset analysis completed.",
                confidence_score=0.5,
                supporting_data={},
                statistical_measures={},
                recommendations=[],
                context=context
            )
    
    def _generate_title(
        self, 
        df: pd.DataFrame, 
        context: Dict[str, Any], 
        insights: List[DataInsight]
    ) -> str:
        """Generate title for the narrative."""
        try:
            # Use the original query if available
            original_query = context.get("natural_language_query", "")
            if original_query:
                # Use AI model to create a more compelling title
                prompt = f"""
                Create a compelling title for a data analysis report based on this query: "{original_query}"
                
                The analysis found these key insights:
                {'; '.join([insight.title for insight in insights[:3]])}
                
                Generate a concise, professional title (max 80 characters) that captures the main focus.
                """
                
                response = self.model.generate_content(prompt)
                title = response.text.strip().strip('"')
                
                if len(title) <= 80:
                    return title
            
            # Fallback to generic title
            return f"Data Analysis Report - {datetime.now().strftime('%B %Y')}"
            
        except Exception as e:
            logger.warning(f"Failed to generate title: {str(e)}")
            return f"Data Analysis Report - {datetime.now().strftime('%B %Y')}"
    
    def _generate_executive_summary(
        self, 
        insights: List[DataInsight], 
        config: NarrativeConfig
    ) -> str:
        """Generate executive summary."""
        try:
            # Prepare key insights for summary
            key_insights_text = []
            for insight in insights[:5]:  # Top 5 insights
                key_insights_text.append(f"• {insight.summary}")
            
            insights_text = "\n".join(key_insights_text)
            
            prompt = f"""
            Create an executive summary for a data analysis report with the following style: {config.style.value}
            Target audience: {config.target_audience}
            Tone: {config.tone}
            Length: {config.length}
            
            Key insights from the analysis:
            {insights_text}
            
            Generate a {config.length} executive summary (2-4 paragraphs) that:
            1. Highlights the most important findings
            2. Uses {config.tone} tone appropriate for {config.target_audience}
            3. Focuses on business implications
            4. Avoids technical jargon if style is executive
            """
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            logger.warning(f"Failed to generate executive summary: {str(e)}")
            return "Analysis completed with key insights identified across multiple data dimensions."
    
    def _generate_detailed_narrative(
        self, 
        df: pd.DataFrame, 
        insights: List[DataInsight], 
        config: NarrativeConfig
    ) -> str:
        """Generate detailed narrative."""
        try:
            # Organize insights by type
            insights_by_type = {}
            for insight in insights:
                insight_type = insight.insight_type.value
                if insight_type not in insights_by_type:
                    insights_by_type[insight_type] = []
                insights_by_type[insight_type].append(insight)
            
            # Create sections for each type
            sections = []
            for insight_type, type_insights in insights_by_type.items():
                section_insights = []
                for insight in type_insights:
                    section_insights.append({
                        "title": insight.title,
                        "analysis": insight.detailed_analysis,
                        "confidence": insight.confidence_score
                    })
                
                sections.append({
                    "type": insight_type,
                    "insights": section_insights
                })
            
            prompt = f"""
            Create a detailed data analysis narrative with the following specifications:
            Style: {config.style.value}
            Target audience: {config.target_audience}
            Length: {config.length}
            Include statistics: {config.include_statistics}
            
            Dataset overview:
            - Shape: {df.shape}
            - Columns: {', '.join(df.columns.tolist()[:10])}
            
            Analysis sections with insights:
            {json.dumps(sections, indent=2)}
            
            Generate a comprehensive narrative that:
            1. Tells a coherent data story
            2. Connects insights logically
            3. Uses appropriate technical depth for {config.style.value} style
            4. Includes statistical details if requested
            5. Flows naturally between sections
            
            Structure: Introduction → Key Findings → Detailed Analysis → Implications
            """
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            logger.warning(f"Failed to generate detailed narrative: {str(e)}")
            return "Detailed analysis reveals multiple patterns and relationships within the data."
    
    def _generate_visualization_recommendations(
        self, 
        df: pd.DataFrame, 
        insights: List[DataInsight]
    ) -> List[Dict[str, Any]]:
        """Generate recommendations for visualizations."""
        recommendations = []
        
        # Trend visualizations
        trend_insights = [i for i in insights if i.insight_type == InsightType.TREND]
        for insight in trend_insights:
            recommendations.append({
                "chart_type": "line_chart",
                "title": f"Trend: {insight.context.get('column', '').title()} Over Time",
                "columns": {
                    "x": insight.context.get('date_column', 'date'),
                    "y": insight.context.get('column', '')
                },
                "description": f"Visualize the {insight.statistical_measures.get('slope', 0) > 0 and 'increasing' or 'decreasing'} trend in {insight.context.get('column', '')}",
                "priority": "high" if insight.confidence_score > 0.8 else "medium"
            })
        
        # Correlation visualizations
        correlation_insights = [i for i in insights if i.insight_type == InsightType.CORRELATION]
        for insight in correlation_insights:
            recommendations.append({
                "chart_type": "scatter_plot",
                "title": f"Correlation: {insight.context.get('column_1', '')} vs {insight.context.get('column_2', '')}",
                "columns": {
                    "x": insight.context.get('column_1', ''),
                    "y": insight.context.get('column_2', '')
                },
                "description": f"Show the {insight.statistical_measures.get('correlation_coefficient', 0) > 0 and 'positive' or 'negative'} correlation between variables",
                "priority": "high" if abs(insight.statistical_measures.get('correlation_coefficient', 0)) > 0.7 else "medium"
            })
        
        # Distribution visualizations
        distribution_insights = [i for i in insights if i.insight_type == InsightType.DISTRIBUTION]
        for insight in distribution_insights:
            recommendations.append({
                "chart_type": "histogram",
                "title": f"Distribution: {insight.context.get('column', '').title()}",
                "columns": {
                    "x": insight.context.get('column', '')
                },
                "description": f"Show the {insight.context.get('distribution_type', 'normal')} distribution pattern",
                "priority": "medium"
            })
        
        # Comparison visualizations
        comparison_insights = [i for i in insights if i.insight_type == InsightType.COMPARISON]
        for insight in comparison_insights:
            recommendations.append({
                "chart_type": "bar_chart",
                "title": f"Comparison: {insight.context.get('numeric_column', '').title()} by {insight.context.get('categorical_column', '').title()}",
                "columns": {
                    "x": insight.context.get('categorical_column', ''),
                    "y": insight.context.get('numeric_column', '')
                },
                "description": f"Compare {insight.context.get('numeric_column', '')} across different {insight.context.get('categorical_column', '')} categories",
                "priority": "high" if insight.statistical_measures.get('effect_size', 0) > 0.3 else "medium"
            })
        
        return recommendations[:8]  # Limit to 8 recommendations
    
    def _generate_action_items(
        self, 
        insights: List[DataInsight], 
        config: NarrativeConfig
    ) -> List[str]:
        """Generate actionable recommendations."""
        try:
            all_recommendations = []
            for insight in insights:
                all_recommendations.extend(insight.recommendations)
            
            # Use AI to consolidate and prioritize recommendations
            recommendations_text = "\n".join([f"• {rec}" for rec in all_recommendations])
            
            prompt = f"""
            Based on these data analysis recommendations, create a prioritized list of 5-7 actionable items:
            
            {recommendations_text}
            
            Target audience: {config.target_audience}
            Style: {config.style.value}
            
            Generate specific, actionable items that:
            1. Are relevant to {config.target_audience}
            2. Can be implemented based on the insights
            3. Are prioritized by impact and feasibility
            4. Use {config.style.value} language style
            
            Format as a simple list without bullets or numbers.
            """
            
            response = self.model.generate_content(prompt)
            action_items = [item.strip() for item in response.text.strip().split('\n') if item.strip()]
            
            return action_items[:7]  # Limit to 7 items
            
        except Exception as e:
            logger.warning(f"Failed to generate action items: {str(e)}")
            # Fallback to original recommendations
            action_items = []
            for insight in insights[:5]:
                action_items.extend(insight.recommendations)
            return list(set(action_items))[:7]  # Remove duplicates and limit


# Example usage and testing
if __name__ == "__main__":
    # Example configuration
    PROJECT_ID = "your-project-id"
    
    # Initialize narrative generator
    generator = NarrativeGenerator(PROJECT_ID)
    
    # Example data
    sample_data = pd.DataFrame({
        'date': pd.date_range('2023-01-01', periods=100, freq='D'),
        'revenue': np.random.normal(10000, 2000, 100) + np.arange(100) * 50,
        'customers': np.random.poisson(100, 100),
        'product_type': np.random.choice(['A', 'B', 'C'], 100),
        'region': np.random.choice(['US', 'EU', 'ASIA'], 100)
    })
    
    sample_context = {
        "natural_language_query": "Show me revenue trends and customer patterns by product and region",
        "confidence_score": 0.9,
        "columns_used": ["date", "revenue", "customers", "product_type", "region"]
    }
    
    try:
        # Generate narrative
        narrative = generator.generate_narrative_from_data(
            sample_data, 
            sample_context,
            NarrativeConfig(
                style=NarrativeStyle.EXECUTIVE,
                target_audience="business_stakeholders",
                length="standard",
                include_statistics=True,
                include_recommendations=True,
                focus_areas=[],
                tone="analytical"
            )
        )
        
        print(f"Generated Narrative: {narrative.narrative_id}")
        print(f"Title: {narrative.title}")
        print(f"Executive Summary: {narrative.executive_summary[:200]}...")
        print(f"Key Insights: {len(narrative.key_insights)}")
        print(f"Visualization Recommendations: {len(narrative.visualization_recommendations)}")
        print(f"Action Items: {len(narrative.action_items)}")
        
        # Print first insight
        if narrative.key_insights:
            first_insight = narrative.key_insights[0]
            print(f"\nFirst Insight:")
            print(f"  Type: {first_insight.insight_type.value}")
            print(f"  Title: {first_insight.title}")
            print(f"  Summary: {first_insight.summary}")
            print(f"  Confidence: {first_insight.confidence_score:.3f}")
            
    except Exception as e:
        print(f"Error: {e}")