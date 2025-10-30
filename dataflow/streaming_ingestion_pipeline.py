"""
Streaming ingestion pipeline for real-time data processing from Pub/Sub
"""

import argparse
import logging
import json
from typing import Dict, Any
from datetime import datetime

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, GoogleCloudOptions, WorkerOptions
from apache_beam.io.gcp.pubsub import ReadFromPubSub
from apache_beam.io.gcp.bigquery import WriteToBigQuery, BigQueryDisposition
from apache_beam.transforms.window import FixedWindows, SlidingWindows, Sessions
from google.cloud import bigquery

from ingestion_pipeline import DataValidator


class PubSubMessageParser(beam.DoFn):
    """Parse Pub/Sub messages and extract data"""
    
    def __init__(self, validation_rules: Dict[str, Any]):
        self.validation_rules = validation_rules
        self.validator = None
    
    def setup(self):
        self.validator = DataValidator(self.validation_rules)
    
    def process(self, element):
        """Parse and validate Pub/Sub message"""
        try:
            # Decode message
            if hasattr(element, 'data'):
                # Pub/Sub message object
                message_data = element.data.decode('utf-8')
                attributes = element.attributes or {}
                publish_time = element.publish_time
            else:
                # String message
                message_data = element
                attributes = {}
                publish_time = datetime.utcnow()
            
            # Parse JSON data
            try:
                data = json.loads(message_data)
            except json.JSONDecodeError as e:
                logging.error(f"Invalid JSON in message: {e}")
                yield {
                    '_raw_message': message_data,
                    '_error': f"JSON decode error: {str(e)}",
                    '_validation_status': 'parse_error',
                    '_processed_at': datetime.utcnow().isoformat(),
                    '_publish_time': publish_time.isoformat() if hasattr(publish_time, 'isoformat') else str(publish_time)
                }
                return
            
            # Add metadata
            data['_publish_time'] = publish_time.isoformat() if hasattr(publish_time, 'isoformat') else str(publish_time)
            data['_message_attributes'] = attributes
            
            # Validate data
            validated_data = self.validator.validate_row(data)
            
            yield validated_data
            
        except Exception as e:
            logging.error(f"Error processing Pub/Sub message: {str(e)}")
            yield {
                '_raw_message': str(element),
                '_error': str(e),
                '_validation_status': 'processing_error',
                '_processed_at': datetime.utcnow().isoformat()
            }


class DataEnricher(beam.DoFn):
    """Enrich data with additional context and transformations"""
    
    def __init__(self, enrichment_rules: Dict[str, Any]):
        self.enrichment_rules = enrichment_rules
    
    def process(self, element):
        """Apply enrichment rules to data"""
        try:
            # Skip enrichment for error records
            if element.get('_validation_status') in ['parse_error', 'processing_error']:
                yield element
                return
            
            # Apply field mappings
            field_mappings = self.enrichment_rules.get('field_mappings', {})
            for old_field, new_field in field_mappings.items():
                if old_field in element:
                    element[new_field] = element.pop(old_field)
            
            # Apply transformations
            transformations = self.enrichment_rules.get('transformations', {})
            for field, transform_config in transformations.items():
                if field in element:
                    element[field] = self._apply_transformation(element[field], transform_config)
            
            # Add computed fields
            computed_fields = self.enrichment_rules.get('computed_fields', {})
            for field_name, computation in computed_fields.items():
                try:
                    element[field_name] = self._compute_field(element, computation)
                except Exception as e:
                    logging.warning(f"Failed to compute field {field_name}: {e}")
            
            yield element
            
        except Exception as e:
            logging.error(f"Error enriching data: {str(e)}")
            element['_enrichment_error'] = str(e)
            yield element
    
    def _apply_transformation(self, value: Any, transform_config: Dict[str, Any]) -> Any:
        """Apply a transformation to a field value"""
        transform_type = transform_config.get('type')
        
        if transform_type == 'uppercase':
            return str(value).upper()
        elif transform_type == 'lowercase':
            return str(value).lower()
        elif transform_type == 'multiply':
            factor = transform_config.get('factor', 1)
            return float(value) * factor
        elif transform_type == 'format_date':
            from_format = transform_config.get('from_format', '%Y-%m-%d')
            to_format = transform_config.get('to_format', '%Y-%m-%d %H:%M:%S')
            dt = datetime.strptime(str(value), from_format)
            return dt.strftime(to_format)
        else:
            return value
    
    def _compute_field(self, record: Dict[str, Any], computation: Dict[str, Any]) -> Any:
        """Compute a new field value"""
        comp_type = computation.get('type')
        
        if comp_type == 'concat':
            fields = computation.get('fields', [])
            separator = computation.get('separator', '')
            values = [str(record.get(field, '')) for field in fields]
            return separator.join(values)
        elif comp_type == 'sum':
            fields = computation.get('fields', [])
            return sum(float(record.get(field, 0)) for field in fields)
        elif comp_type == 'current_timestamp':
            return datetime.utcnow().isoformat()
        else:
            return None


class StreamingStatsCollector(beam.DoFn):
    """Collect streaming statistics with windowing"""
    
    def process(self, element, window=beam.DoFn.WindowParam):
        """Collect windowed statistics"""
        window_start = window.start.to_utc_datetime()
        window_end = window.end.to_utc_datetime()
        
        stats = {
            'window_start': window_start.isoformat(),
            'window_end': window_end.isoformat(),
            'record_count': 1,
            'validation_status': element.get('_validation_status', 'unknown'),
            'processing_time': datetime.utcnow().isoformat()
        }
        
        yield beam.pvalue.TaggedOutput('data', element)
        yield beam.pvalue.TaggedOutput('stats', stats)


def run_streaming_pipeline(argv=None):
    """Run the streaming ingestion pipeline"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--subscription', required=True, help='Pub/Sub subscription')
    parser.add_argument('--output_table', required=True, help='BigQuery output table')
    parser.add_argument('--temp_location', required=True, help='GCS temp location')
    parser.add_argument('--project', required=True, help='GCP project ID')
    parser.add_argument('--validation_rules', help='JSON string with validation rules')
    parser.add_argument('--enrichment_rules', help='JSON string with enrichment rules')
    parser.add_argument('--window_size', type=int, default=60, help='Window size in seconds')
    parser.add_argument('--window_type', default='fixed', choices=['fixed', 'sliding', 'session'])
    
    known_args, pipeline_args = parser.parse_known_args(argv)
    
    # Parse rules
    validation_rules = {}
    if known_args.validation_rules:
        validation_rules = json.loads(known_args.validation_rules)
    
    enrichment_rules = {}
    if known_args.enrichment_rules:
        enrichment_rules = json.loads(known_args.enrichment_rules)
    
    # Set up pipeline options for streaming
    pipeline_options = PipelineOptions(pipeline_args)
    pipeline_options.view_as(beam.options.pipeline_options.StandardOptions).streaming = True
    
    google_cloud_options = pipeline_options.view_as(GoogleCloudOptions)
    google_cloud_options.project = known_args.project
    google_cloud_options.temp_location = known_args.temp_location
    google_cloud_options.region = 'us-central1'
    
    worker_options = pipeline_options.view_as(WorkerOptions)
    worker_options.machine_type = 'n1-standard-2'
    worker_options.max_num_workers = 10
    worker_options.autoscaling_algorithm = 'THROUGHPUT_BASED'
    
    with beam.Pipeline(options=pipeline_options) as pipeline:
        
        # Read from Pub/Sub
        messages = (
            pipeline
            | 'Read from Pub/Sub' >> ReadFromPubSub(subscription=known_args.subscription)
        )
        
        # Parse and validate messages
        parsed_data = (
            messages
            | 'Parse messages' >> beam.ParDo(PubSubMessageParser(validation_rules))
        )
        
        # Enrich data
        enriched_data = (
            parsed_data
            | 'Enrich data' >> beam.ParDo(DataEnricher(enrichment_rules))
        )
        
        # Apply windowing
        window_size = known_args.window_size
        if known_args.window_type == 'fixed':
            windowing = beam.WindowInto(FixedWindows(window_size))
        elif known_args.window_type == 'sliding':
            windowing = beam.WindowInto(SlidingWindows(window_size, window_size // 2))
        else:  # session
            windowing = beam.WindowInto(Sessions(window_size))
        
        windowed_data = enriched_data | 'Apply windowing' >> windowing
        
        # Collect statistics
        outputs = (
            windowed_data
            | 'Collect stats' >> beam.ParDo(StreamingStatsCollector()).with_outputs('data', 'stats')
        )
        
        # Write valid data to BigQuery
        valid_data = (
            outputs.data
            | 'Filter valid records' >> beam.Filter(
                lambda x: x.get('_validation_status') == 'valid'
            )
            | 'Remove internal fields' >> beam.Map(
                lambda x: {k: v for k, v in x.items() 
                          if not k.startswith('_') or k in ['_publish_time']}
            )
        )
        
        valid_data | 'Write to BigQuery' >> WriteToBigQuery(
            table=known_args.output_table,
            schema='SCHEMA_AUTODETECT',
            create_disposition=BigQueryDisposition.CREATE_IF_NEEDED,
            write_disposition=BigQueryDisposition.WRITE_APPEND,
            additional_bq_parameters={
                'timePartitioning': {
                    'type': 'HOUR',
                    'field': '_publish_time'
                }
            }
        )
        
        # Write invalid data to errors table
        invalid_data = (
            outputs.data
            | 'Filter invalid records' >> beam.Filter(
                lambda x: x.get('_validation_status') in ['invalid', 'parse_error', 'processing_error']
            )
        )
        
        invalid_data | 'Write errors' >> WriteToBigQuery(
            table=f"{known_args.output_table}_errors",
            schema='SCHEMA_AUTODETECT',
            create_disposition=BigQueryDisposition.CREATE_IF_NEEDED,
            write_disposition=BigQueryDisposition.WRITE_APPEND
        )
        
        # Aggregate and write windowed statistics
        windowed_stats = (
            outputs.stats
            | 'Group stats by window' >> beam.GroupBy(
                lambda x: (x['window_start'], x['window_end'])
            )
            | 'Aggregate windowed stats' >> beam.Map(
                lambda x: {
                    'window_start': x[0][0],
                    'window_end': x[0][1],
                    'total_records': len(list(x[1])),
                    'valid_records': len([s for s in x[1] if s['validation_status'] == 'valid']),
                    'invalid_records': len([s for s in x[1] if s['validation_status'] in ['invalid', 'parse_error', 'processing_error']]),
                    'aggregated_at': datetime.utcnow().isoformat()
                }
            )
        )
        
        windowed_stats | 'Write windowed stats' >> WriteToBigQuery(
            table=f"{known_args.output_table}_windowed_stats",
            schema=[
                {'name': 'window_start', 'type': 'TIMESTAMP', 'mode': 'REQUIRED'},
                {'name': 'window_end', 'type': 'TIMESTAMP', 'mode': 'REQUIRED'},
                {'name': 'total_records', 'type': 'INTEGER', 'mode': 'REQUIRED'},
                {'name': 'valid_records', 'type': 'INTEGER', 'mode': 'REQUIRED'},
                {'name': 'invalid_records', 'type': 'INTEGER', 'mode': 'REQUIRED'},
                {'name': 'aggregated_at', 'type': 'TIMESTAMP', 'mode': 'REQUIRED'}
            ],
            create_disposition=BigQueryDisposition.CREATE_IF_NEEDED,
            write_disposition=BigQueryDisposition.WRITE_APPEND
        )


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    run_streaming_pipeline()