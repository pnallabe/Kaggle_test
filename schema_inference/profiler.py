"""
Automated schema inference and data profiling module
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import json
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import re
from collections import Counter

from google.cloud import storage, bigquery
import pyarrow as pa
import pyarrow.parquet as pq


@dataclass
class ColumnProfile:
    """Profile information for a single column"""
    column_name: str
    data_type: str
    null_count: int
    non_null_count: int
    null_percentage: float
    unique_count: int
    unique_percentage: float
    
    # Statistical measures
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    mean_value: Optional[float] = None
    median_value: Optional[float] = None
    std_dev: Optional[float] = None
    
    # String-specific measures
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    avg_length: Optional[float] = None
    
    # Top values
    top_values: Optional[List[Tuple[Any, int]]] = None
    
    # Data quality flags
    has_duplicates: bool = False
    has_outliers: bool = False
    potential_pii: bool = False
    suggested_constraints: Optional[List[str]] = None


@dataclass
class DatasetProfile:
    """Complete profile for a dataset"""
    dataset_name: str
    total_rows: int
    total_columns: int
    file_size_bytes: int
    profiling_timestamp: str
    
    column_profiles: List[ColumnProfile]
    
    # Dataset-level statistics
    memory_usage_mb: float
    data_quality_score: float
    completeness_score: float
    
    # Recommendations
    suggested_schema: List[Dict[str, Any]]
    data_quality_issues: List[str]
    optimization_recommendations: List[str]


class SchemaInferrer:
    """Infer schema and generate data profiles from various file formats"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Patterns for detecting PII
        self.pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        }
    
    def profile_file(self, file_path: str, sample_size: int = 10000) -> DatasetProfile:
        """Profile a file and generate comprehensive analysis"""
        try:
            # Detect file format and read data
            if file_path.lower().endswith('.csv'):
                df = pd.read_csv(file_path, nrows=sample_size)
            elif file_path.lower().endswith('.parquet'):
                df = pd.read_parquet(file_path)
                if len(df) > sample_size:
                    df = df.sample(n=sample_size)
            elif file_path.lower().endswith('.json'):
                df = pd.read_json(file_path, lines=True, nrows=sample_size)
            else:
                raise ValueError(f"Unsupported file format: {file_path}")
            
            return self.profile_dataframe(df, file_path)
            
        except Exception as e:
            self.logger.error(f"Error profiling file {file_path}: {str(e)}")
            raise
    
    def profile_dataframe(self, df: pd.DataFrame, dataset_name: str = "dataset") -> DatasetProfile:
        """Profile a pandas DataFrame"""
        
        # Calculate dataset-level metrics
        total_rows, total_columns = df.shape
        memory_usage_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
        
        # Profile each column
        column_profiles = []
        for column in df.columns:
            profile = self._profile_column(df[column], str(column))
            column_profiles.append(profile)
        
        # Calculate quality scores
        data_quality_score = self._calculate_data_quality_score(column_profiles)
        completeness_score = self._calculate_completeness_score(column_profiles)
        
        # Generate schema suggestions
        suggested_schema = self._generate_bigquery_schema(column_profiles)
        
        # Identify data quality issues
        data_quality_issues = self._identify_quality_issues(column_profiles)
        
        # Generate optimization recommendations
        optimization_recommendations = self._generate_recommendations(df, column_profiles)
        
        return DatasetProfile(
            dataset_name=dataset_name,
            total_rows=total_rows,
            total_columns=total_columns,
            file_size_bytes=0,  # Would need file system access
            profiling_timestamp=datetime.utcnow().isoformat(),
            column_profiles=column_profiles,
            memory_usage_mb=memory_usage_mb,
            data_quality_score=data_quality_score,
            completeness_score=completeness_score,
            suggested_schema=suggested_schema,
            data_quality_issues=data_quality_issues,
            optimization_recommendations=optimization_recommendations
        )
    
    def _profile_column(self, series: pd.Series, column_name: str) -> ColumnProfile:
        """Generate detailed profile for a single column"""
        
        # Basic statistics
        total_count = len(series)
        null_count = series.isnull().sum()
        non_null_count = total_count - null_count
        null_percentage = (null_count / total_count) * 100 if total_count > 0 else 0
        
        unique_count = series.nunique()
        unique_percentage = (unique_count / total_count) * 100 if total_count > 0 else 0
        
        # Infer data type
        inferred_type = self._infer_data_type(series)
        
        # Initialize profile
        profile = ColumnProfile(
            column_name=column_name,
            data_type=inferred_type,
            null_count=null_count,
            non_null_count=non_null_count,
            null_percentage=null_percentage,
            unique_count=unique_count,
            unique_percentage=unique_percentage,
            has_duplicates=unique_count < non_null_count
        )
        
        # Type-specific profiling
        if non_null_count > 0:
            non_null_series = series.dropna()
            
            if inferred_type in ['INTEGER', 'FLOAT']:
                profile.min_value = float(non_null_series.min())
                profile.max_value = float(non_null_series.max())
                profile.mean_value = float(non_null_series.mean())
                profile.median_value = float(non_null_series.median())
                profile.std_dev = float(non_null_series.std())
                
                # Detect outliers using IQR method
                q1 = non_null_series.quantile(0.25)
                q3 = non_null_series.quantile(0.75)
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                outliers = non_null_series[(non_null_series < lower_bound) | (non_null_series > upper_bound)]
                profile.has_outliers = len(outliers) > 0
                
            elif inferred_type == 'STRING':
                # String length analysis
                lengths = non_null_series.astype(str).str.len()
                profile.min_length = int(lengths.min())
                profile.max_length = int(lengths.max())
                profile.avg_length = float(lengths.mean())
                
                # Check for PII patterns
                profile.potential_pii = self._detect_pii(non_null_series)
            
            elif inferred_type == 'TIMESTAMP':
                try:
                    dt_series = pd.to_datetime(non_null_series)
                    profile.min_value = dt_series.min().isoformat()
                    profile.max_value = dt_series.max().isoformat()
                except:
                    pass
            
            # Top values analysis (for categorical-like data)
            if unique_count <= 50 or unique_percentage <= 10:
                value_counts = non_null_series.value_counts().head(10)
                profile.top_values = [(value, count) for value, count in value_counts.items()]
            
            # Generate constraint suggestions
            profile.suggested_constraints = self._suggest_constraints(profile, non_null_series)
        
        return profile
    
    def _infer_data_type(self, series: pd.Series) -> str:
        """Infer BigQuery-compatible data type for a series"""
        
        # Skip null values for type inference
        non_null_series = series.dropna()
        
        if len(non_null_series) == 0:
            return 'STRING'
        
        # Check for boolean
        if non_null_series.dtype == 'bool':
            return 'BOOLEAN'
        
        # Check for numeric types
        if pd.api.types.is_integer_dtype(non_null_series):
            return 'INTEGER'
        
        if pd.api.types.is_float_dtype(non_null_series):
            return 'FLOAT'
        
        # Check for datetime
        if pd.api.types.is_datetime64_any_dtype(non_null_series):
            return 'TIMESTAMP'
        
        # For object types, try to infer more specific types
        if non_null_series.dtype == 'object':
            # Try to parse as datetime
            try:
                pd.to_datetime(non_null_series.head(100))
                return 'TIMESTAMP'
            except:
                pass
            
            # Try to parse as numeric
            try:
                pd.to_numeric(non_null_series.head(100))
                # Check if all values are integers
                numeric_series = pd.to_numeric(non_null_series)
                if all(val.is_integer() for val in numeric_series if pd.notnull(val)):
                    return 'INTEGER'
                else:
                    return 'FLOAT'
            except:
                pass
            
            # Check for boolean-like strings
            unique_values = set(str(val).lower() for val in non_null_series.unique())
            if unique_values.issubset({'true', 'false', '1', '0', 'yes', 'no', 't', 'f'}):
                return 'BOOLEAN'
        
        # Default to STRING
        return 'STRING'
    
    def _detect_pii(self, series: pd.Series) -> bool:
        """Detect potential PII in string data"""
        
        # Sample some values for PII detection
        sample_values = series.astype(str).head(100)
        
        for pii_type, pattern in self.pii_patterns.items():
            for value in sample_values:
                if re.search(pattern, value):
                    return True
        
        return False
    
    def _suggest_constraints(self, profile: ColumnProfile, series: pd.Series) -> List[str]:
        """Suggest data constraints based on profile"""
        constraints = []
        
        # NOT NULL constraint
        if profile.null_percentage < 5:
            constraints.append("NOT NULL")
        
        # UNIQUE constraint
        if profile.unique_percentage > 95:
            constraints.append("UNIQUE")
        
        # Range constraints for numeric data
        if profile.data_type in ['INTEGER', 'FLOAT'] and profile.min_value is not None:
            if profile.min_value >= 0:
                constraints.append("CHECK (value >= 0)")
            
            # Suggest reasonable ranges based on data distribution
            if profile.std_dev and profile.mean_value:
                reasonable_max = profile.mean_value + 3 * profile.std_dev
                if profile.max_value and profile.max_value > reasonable_max:
                    constraints.append(f"CHECK (value <= {reasonable_max:.2f})")
        
        # String length constraints
        if profile.data_type == 'STRING' and profile.max_length:
            if profile.max_length <= 50:
                constraints.append(f"VARCHAR({profile.max_length})")
            elif profile.max_length <= 255:
                constraints.append(f"VARCHAR(255)")
        
        return constraints
    
    def _calculate_data_quality_score(self, column_profiles: List[ColumnProfile]) -> float:
        """Calculate overall data quality score (0-100)"""
        if not column_profiles:
            return 0.0
        
        scores = []
        for profile in column_profiles:
            # Completeness score (lower null percentage is better)
            completeness = 100 - profile.null_percentage
            
            # Uniqueness score (depends on data type)
            if profile.data_type == 'STRING' and profile.unique_percentage < 50:
                uniqueness = profile.unique_percentage * 2  # Categorical data
            else:
                uniqueness = min(profile.unique_percentage, 100)
            
            # Consistency score (no outliers is better)
            consistency = 80 if profile.has_outliers else 100
            
            # PII detection penalty
            pii_penalty = 20 if profile.potential_pii else 0
            
            column_score = (completeness + uniqueness + consistency - pii_penalty) / 3
            scores.append(max(0, min(100, column_score)))
        
        return sum(scores) / len(scores)
    
    def _calculate_completeness_score(self, column_profiles: List[ColumnProfile]) -> float:
        """Calculate data completeness score (0-100)"""
        if not column_profiles:
            return 0.0
        
        completeness_scores = [100 - profile.null_percentage for profile in column_profiles]
        return sum(completeness_scores) / len(completeness_scores)
    
    def _generate_bigquery_schema(self, column_profiles: List[ColumnProfile]) -> List[Dict[str, Any]]:
        """Generate BigQuery schema from column profiles"""
        schema = []
        
        for profile in column_profiles:
            # Determine mode (NULLABLE vs REQUIRED)
            mode = 'REQUIRED' if profile.null_percentage < 1 else 'NULLABLE'
            
            field = {
                'name': profile.column_name,
                'type': profile.data_type,
                'mode': mode
            }
            
            # Add description with profile summary
            description_parts = [
                f"Unique values: {profile.unique_count}",
                f"Null rate: {profile.null_percentage:.1f}%"
            ]
            
            if profile.data_type in ['INTEGER', 'FLOAT'] and profile.min_value is not None:
                description_parts.append(f"Range: {profile.min_value} to {profile.max_value}")
            
            if profile.potential_pii:
                description_parts.append("Potential PII detected")
            
            field['description'] = "; ".join(description_parts)
            
            schema.append(field)
        
        return schema
    
    def _identify_quality_issues(self, column_profiles: List[ColumnProfile]) -> List[str]:
        """Identify data quality issues"""
        issues = []
        
        for profile in column_profiles:
            col_name = profile.column_name
            
            # High null percentage
            if profile.null_percentage > 50:
                issues.append(f"Column '{col_name}' has high null rate ({profile.null_percentage:.1f}%)")
            
            # Low uniqueness for potential key fields
            if 'id' in col_name.lower() and profile.unique_percentage < 95:
                issues.append(f"Column '{col_name}' appears to be an ID but has low uniqueness ({profile.unique_percentage:.1f}%)")
            
            # Outliers detected
            if profile.has_outliers:
                issues.append(f"Column '{col_name}' contains outliers")
            
            # Potential PII
            if profile.potential_pii:
                issues.append(f"Column '{col_name}' may contain PII data")
            
            # Very long strings
            if profile.data_type == 'STRING' and profile.max_length and profile.max_length > 1000:
                issues.append(f"Column '{col_name}' contains very long strings (max: {profile.max_length} chars)")
        
        return issues
    
    def _generate_recommendations(self, df: pd.DataFrame, column_profiles: List[ColumnProfile]) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Memory optimization
        if df.memory_usage(deep=True).sum() / (1024 * 1024) > 100:  # > 100MB
            recommendations.append("Consider using more efficient data types to reduce memory usage")
        
        # Partitioning recommendations
        datetime_columns = [p.column_name for p in column_profiles if p.data_type == 'TIMESTAMP']
        if datetime_columns:
            recommendations.append(f"Consider partitioning by datetime column: {datetime_columns[0]}")
        
        # Clustering recommendations
        high_cardinality_columns = [p.column_name for p in column_profiles 
                                  if p.unique_count > 100 and p.unique_percentage < 90]
        if high_cardinality_columns:
            recommendations.append(f"Consider clustering by: {', '.join(high_cardinality_columns[:3])}")
        
        # Compression recommendations
        string_columns = [p for p in column_profiles if p.data_type == 'STRING']
        if any(p.unique_percentage < 10 for p in string_columns):
            recommendations.append("Consider using dictionary encoding for categorical string columns")
        
        # Data validation recommendations
        if any(p.potential_pii for p in column_profiles):
            recommendations.append("Implement PII masking or encryption for sensitive columns")
        
        return recommendations
    
    def save_profile_to_json(self, profile: DatasetProfile, output_path: str):
        """Save profile to JSON file"""
        profile_dict = asdict(profile)
        
        # Convert non-serializable objects
        def convert_for_json(obj):
            if isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif pd.isna(obj):
                return None
            return obj
        
        # Recursively convert the profile dictionary
        def recursive_convert(d):
            if isinstance(d, dict):
                return {k: recursive_convert(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [recursive_convert(item) for item in d]
            else:
                return convert_for_json(d)
        
        profile_dict = recursive_convert(profile_dict)
        
        with open(output_path, 'w') as f:
            json.dump(profile_dict, f, indent=2, default=str)


# Example usage and testing
if __name__ == "__main__":
    # Example usage
    inferrer = SchemaInferrer()
    
    # Create sample data for testing
    sample_data = {
        'id': range(1000),
        'name': [f'User_{i}' for i in range(1000)],
        'email': [f'user{i}@example.com' for i in range(1000)],
        'age': np.random.randint(18, 65, 1000),
        'salary': np.random.normal(50000, 15000, 1000),
        'created_at': pd.date_range('2023-01-01', periods=1000, freq='H'),
        'is_active': np.random.choice([True, False], 1000),
        'category': np.random.choice(['A', 'B', 'C', 'D'], 1000),
        'notes': [f'Some notes for user {i}' if i % 10 != 0 else None for i in range(1000)]
    }
    
    df = pd.DataFrame(sample_data)
    
    # Profile the data
    profile = inferrer.profile_dataframe(df, "sample_dataset")
    
    # Print summary
    print(f"Dataset: {profile.dataset_name}")
    print(f"Rows: {profile.total_rows}, Columns: {profile.total_columns}")
    print(f"Data Quality Score: {profile.data_quality_score:.1f}/100")
    print(f"Completeness Score: {profile.completeness_score:.1f}/100")
    print()
    
    print("Column Profiles:")
    for col_profile in profile.column_profiles:
        print(f"  {col_profile.column_name}: {col_profile.data_type} "
              f"(nulls: {col_profile.null_percentage:.1f}%, "
              f"unique: {col_profile.unique_percentage:.1f}%)")
    
    print("\nData Quality Issues:")
    for issue in profile.data_quality_issues:
        print(f"  - {issue}")
    
    print("\nRecommendations:")
    for rec in profile.optimization_recommendations:
        print(f"  - {rec}")
    
    # Save profile
    inferrer.save_profile_to_json(profile, "sample_profile.json")
    print("\nProfile saved to sample_profile.json")