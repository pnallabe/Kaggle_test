"""
Schema inference utility functions and integration helpers
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from google.cloud import storage, bigquery
from profiler import SchemaInferrer, DatasetProfile
from validator import DataValidator, create_sample_validation_config


class SchemaInferenceService:
    """Service for automated schema inference and validation rule generation"""
    
    def __init__(self, project_id: str, bucket_name: str):
        self.project_id = project_id
        self.bucket_name = bucket_name
        self.storage_client = storage.Client(project=project_id)
        self.bq_client = bigquery.Client(project=project_id)
        self.inferrer = SchemaInferrer()
        self.logger = logging.getLogger(__name__)
    
    def infer_schema_from_gcs(self, file_path: str, sample_size: int = 10000) -> DatasetProfile:
        """Infer schema from a file in GCS"""
        try:
            # Download file to temporary location for analysis
            local_path = self._download_gcs_file(file_path)
            
            # Profile the file
            profile = self.inferrer.profile_file(local_path, sample_size)
            
            # Clean up temporary file
            Path(local_path).unlink(missing_ok=True)
            
            return profile
            
        except Exception as e:
            self.logger.error(f"Error inferring schema from {file_path}: {str(e)}")
            raise
    
    def _download_gcs_file(self, gcs_path: str) -> str:
        """Download GCS file to local temporary location"""
        # Parse GCS path
        if not gcs_path.startswith('gs://'):
            raise ValueError(f"Invalid GCS path: {gcs_path}")
        
        path_parts = gcs_path[5:].split('/', 1)
        bucket_name = path_parts[0]
        blob_name = path_parts[1]
        
        # Download file
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        # Create temporary file
        import tempfile
        import os
        
        suffix = Path(blob_name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            blob.download_to_filename(temp_file.name)
            return temp_file.name
    
    def generate_validation_rules(self, profile: DatasetProfile) -> Dict[str, Any]:
        """Generate validation rules based on data profile"""
        rules = []
        
        for col_profile in profile.column_profiles:
            col_name = col_profile.column_name
            
            # Add NOT NULL rule for columns with low null percentage
            if col_profile.null_percentage < 5:
                rules.append({
                    'type': 'not_null',
                    'columns': [col_name],
                    'severity': 'ERROR'
                })
            
            # Add UNIQUE rule for potential key columns
            if ('id' in col_name.lower() or col_profile.unique_percentage > 95) and col_profile.unique_count > 1:
                rules.append({
                    'type': 'unique',
                    'columns': [col_name],
                    'severity': 'ERROR'
                })
            
            # Add range rules for numeric columns
            if col_profile.data_type in ['INTEGER', 'FLOAT'] and col_profile.min_value is not None:
                # Set reasonable bounds based on data distribution
                if col_profile.std_dev and col_profile.mean_value:
                    # Use 3-sigma rule for outlier detection
                    lower_bound = col_profile.mean_value - 3 * col_profile.std_dev
                    upper_bound = col_profile.mean_value + 3 * col_profile.std_dev
                    
                    rules.append({
                        'type': 'range',
                        'column': col_name,
                        'min_value': max(lower_bound, col_profile.min_value),
                        'max_value': min(upper_bound, col_profile.max_value * 1.1),  # Allow 10% headroom
                        'severity': 'WARNING'
                    })
            
            # Add pattern rules for string columns with consistent formats
            if col_profile.data_type == 'STRING' and col_profile.top_values:
                # Check for email pattern
                if 'email' in col_name.lower():
                    rules.append({
                        'type': 'pattern',
                        'column': col_name,
                        'pattern': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                        'severity': 'ERROR'
                    })
                
                # Check for categorical data with limited values
                elif col_profile.unique_count <= 20:
                    allowed_values = [item[0] for item in col_profile.top_values[:20]]
                    rules.append({
                        'type': 'value_set',
                        'column': col_name,
                        'allowed_values': allowed_values,
                        'severity': 'WARNING'
                    })
        
        return {'rules': rules}
    
    def create_bigquery_table(self, profile: DatasetProfile, dataset_id: str, table_id: str) -> str:
        """Create BigQuery table with inferred schema"""
        try:
            # Create dataset if it doesn't exist
            dataset_ref = self.bq_client.dataset(dataset_id)
            try:
                self.bq_client.get_dataset(dataset_ref)
            except:
                dataset = bigquery.Dataset(dataset_ref)
                dataset.location = "US"
                self.bq_client.create_dataset(dataset)
                self.logger.info(f"Created dataset {dataset_id}")
            
            # Convert profile schema to BigQuery schema
            bq_schema = []
            for field in profile.suggested_schema:
                bq_field = bigquery.SchemaField(
                    name=field['name'],
                    field_type=field['type'],
                    mode=field['mode'],
                    description=field.get('description', '')
                )
                bq_schema.append(bq_field)
            
            # Create table
            table_ref = dataset_ref.table(table_id)
            table = bigquery.Table(table_ref, schema=bq_schema)
            
            # Add table description
            table.description = f"Auto-generated table from schema inference. " \
                              f"Data quality score: {profile.data_quality_score:.1f}%. " \
                              f"Profiled on {profile.profiling_timestamp}."
            
            # Set partitioning if there's a timestamp column
            timestamp_columns = [field['name'] for field in profile.suggested_schema 
                               if field['type'] == 'TIMESTAMP']
            if timestamp_columns:
                table.time_partitioning = bigquery.TimePartitioning(
                    type_=bigquery.TimePartitioningType.DAY,
                    field=timestamp_columns[0]
                )
            
            # Set clustering if there are good clustering candidates
            clustering_columns = [col.column_name for col in profile.column_profiles 
                                if col.data_type == 'STRING' and 50 <= col.unique_count <= 1000]
            if clustering_columns:
                table.clustering_fields = clustering_columns[:4]  # Max 4 clustering columns
            
            created_table = self.bq_client.create_table(table)
            self.logger.info(f"Created table {dataset_id}.{table_id}")
            
            return f"{self.project_id}.{dataset_id}.{table_id}"
            
        except Exception as e:
            self.logger.error(f"Error creating BigQuery table: {str(e)}")
            raise
    
    def save_profile_to_gcs(self, profile: DatasetProfile, gcs_path: str):
        """Save profile to GCS as JSON"""
        try:
            # Convert profile to dict
            from profiler import asdict
            profile_dict = asdict(profile)
            
            # Convert non-serializable objects
            def convert_for_json(obj):
                if hasattr(obj, 'isoformat'):
                    return obj.isoformat()
                elif hasattr(obj, 'tolist'):
                    return obj.tolist()
                elif str(type(obj)) == "<class 'numpy.float64'>":
                    return float(obj)
                elif str(type(obj)) == "<class 'numpy.int64'>":
                    return int(obj)
                return obj
            
            # Recursively convert
            def recursive_convert(d):
                if isinstance(d, dict):
                    return {k: recursive_convert(v) for k, v in d.items()}
                elif isinstance(d, list):
                    return [recursive_convert(item) for item in d]
                else:
                    return convert_for_json(d)
            
            profile_dict = recursive_convert(profile_dict)
            
            # Upload to GCS
            profile_json = json.dumps(profile_dict, indent=2, default=str)
            
            # Parse GCS path
            path_parts = gcs_path[5:].split('/', 1) if gcs_path.startswith('gs://') else [self.bucket_name, gcs_path]
            bucket_name = path_parts[0]
            blob_name = path_parts[1]
            
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.upload_from_string(profile_json, content_type='application/json')
            
            self.logger.info(f"Saved profile to {gcs_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving profile to GCS: {str(e)}")
            raise


class DataQualityMonitor:
    """Monitor data quality over time and detect drift"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.bq_client = bigquery.Client(project=project_id)
        self.logger = logging.getLogger(__name__)
    
    def compare_profiles(self, profile1: DatasetProfile, profile2: DatasetProfile) -> Dict[str, Any]:
        """Compare two data profiles and identify differences"""
        comparison = {
            'schema_changes': [],
            'quality_changes': {},
            'statistical_drift': [],
            'new_columns': [],
            'removed_columns': [],
            'overall_drift_score': 0.0
        }
        
        # Get column names from both profiles
        cols1 = {col.column_name: col for col in profile1.column_profiles}
        cols2 = {col.column_name: col for col in profile2.column_profiles}
        
        # Find new and removed columns
        comparison['new_columns'] = list(set(cols2.keys()) - set(cols1.keys()))
        comparison['removed_columns'] = list(set(cols1.keys()) - set(cols2.keys()))
        
        # Compare common columns
        drift_scores = []
        for col_name in set(cols1.keys()) & set(cols2.keys()):
            col1 = cols1[col_name]
            col2 = cols2[col_name]
            
            # Check for data type changes
            if col1.data_type != col2.data_type:
                comparison['schema_changes'].append({
                    'column': col_name,
                    'change': 'data_type',
                    'old_value': col1.data_type,
                    'new_value': col2.data_type
                })
            
            # Check for significant null percentage changes
            null_diff = abs(col1.null_percentage - col2.null_percentage)
            if null_diff > 10:  # More than 10% change
                comparison['statistical_drift'].append({
                    'column': col_name,
                    'metric': 'null_percentage',
                    'old_value': col1.null_percentage,
                    'new_value': col2.null_percentage,
                    'change': null_diff
                })
                drift_scores.append(null_diff / 100)
            
            # Check for unique count changes (for categorical data)
            if col1.unique_count <= 100 and col2.unique_count <= 100:
                unique_diff = abs(col1.unique_count - col2.unique_count) / max(col1.unique_count, 1)
                if unique_diff > 0.2:  # More than 20% change
                    comparison['statistical_drift'].append({
                        'column': col_name,
                        'metric': 'unique_count',
                        'old_value': col1.unique_count,
                        'new_value': col2.unique_count,
                        'change': unique_diff
                    })
                    drift_scores.append(unique_diff)
            
            # Check for statistical drift in numeric columns
            if (col1.data_type in ['INTEGER', 'FLOAT'] and col2.data_type in ['INTEGER', 'FLOAT'] 
                and col1.mean_value is not None and col2.mean_value is not None):
                
                # Calculate normalized difference in means
                mean_diff = abs(col1.mean_value - col2.mean_value)
                if col1.std_dev and col1.std_dev > 0:
                    normalized_diff = mean_diff / col1.std_dev
                    if normalized_diff > 0.5:  # More than 0.5 standard deviations
                        comparison['statistical_drift'].append({
                            'column': col_name,
                            'metric': 'mean_value',
                            'old_value': col1.mean_value,
                            'new_value': col2.mean_value,
                            'normalized_difference': normalized_diff
                        })
                        drift_scores.append(min(normalized_diff / 2, 1.0))
        
        # Calculate overall drift score
        if drift_scores:
            comparison['overall_drift_score'] = sum(drift_scores) / len(drift_scores)
        
        # Compare quality scores
        comparison['quality_changes'] = {
            'data_quality_score_change': profile2.data_quality_score - profile1.data_quality_score,
            'completeness_score_change': profile2.completeness_score - profile1.completeness_score
        }
        
        return comparison
    
    def generate_drift_report(self, comparison: Dict[str, Any]) -> str:
        """Generate human-readable drift report"""
        lines = ["Data Drift Analysis Report", "=" * 30, ""]
        
        # Overall assessment
        drift_score = comparison['overall_drift_score']
        if drift_score < 0.1:
            assessment = "LOW"
        elif drift_score < 0.3:
            assessment = "MODERATE"
        else:
            assessment = "HIGH"
        
        lines.append(f"Overall Drift Assessment: {assessment} (score: {drift_score:.3f})")
        lines.append("")
        
        # Schema changes
        if comparison['schema_changes']:
            lines.append("Schema Changes:")
            for change in comparison['schema_changes']:
                lines.append(f"  - {change['column']}: {change['change']} changed from {change['old_value']} to {change['new_value']}")
            lines.append("")
        
        # New/removed columns
        if comparison['new_columns']:
            lines.append(f"New Columns: {', '.join(comparison['new_columns'])}")
        if comparison['removed_columns']:
            lines.append(f"Removed Columns: {', '.join(comparison['removed_columns'])}")
        if comparison['new_columns'] or comparison['removed_columns']:
            lines.append("")
        
        # Statistical drift
        if comparison['statistical_drift']:
            lines.append("Statistical Drift Detected:")
            for drift in comparison['statistical_drift']:
                lines.append(f"  - {drift['column']} ({drift['metric']}): {drift['old_value']:.2f} → {drift['new_value']:.2f}")
            lines.append("")
        
        # Quality changes
        quality_changes = comparison['quality_changes']
        lines.append("Data Quality Changes:")
        lines.append(f"  - Data Quality Score: {quality_changes['data_quality_score_change']:+.1f}")
        lines.append(f"  - Completeness Score: {quality_changes['completeness_score_change']:+.1f}")
        
        return "\n".join(lines)


# Utility functions for common operations
def batch_infer_schemas(gcs_paths: List[str], project_id: str, bucket_name: str) -> Dict[str, DatasetProfile]:
    """Batch infer schemas for multiple files"""
    service = SchemaInferenceService(project_id, bucket_name)
    profiles = {}
    
    for path in gcs_paths:
        try:
            profile = service.infer_schema_from_gcs(path)
            profiles[path] = profile
        except Exception as e:
            logging.error(f"Failed to infer schema for {path}: {str(e)}")
    
    return profiles


def create_validation_config_from_profile(profile: DatasetProfile) -> Dict[str, Any]:
    """Create validation configuration from data profile"""
    service = SchemaInferenceService("dummy", "dummy")
    return service.generate_validation_rules(profile)


if __name__ == "__main__":
    # Example usage
    import os
    
    project_id = os.getenv("GCP_PROJECT_ID", "test-project")
    bucket_name = os.getenv("GCS_BUCKET", "test-bucket")
    
    # Initialize service
    service = SchemaInferenceService(project_id, bucket_name)
    
    print("Schema Inference Service initialized")
    print(f"Project: {project_id}")
    print(f"Bucket: {bucket_name}")
    
    # Example: Infer schema from sample data
    # profile = service.infer_schema_from_gcs("gs://your-bucket/data/sample.csv")
    # print(f"Inferred schema for sample data: {len(profile.column_profiles)} columns")
    
    # Generate validation rules
    # validation_config = service.generate_validation_rules(profile)
    # print(f"Generated {len(validation_config['rules'])} validation rules")