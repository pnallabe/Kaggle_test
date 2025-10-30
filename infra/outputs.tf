output "gcs_artifacts_bucket" {
  value       = google_storage_bucket.artifacts.name
  description = "GCS bucket for artifacts"
}

output "gcs_backend_bucket" {
  value       = google_storage_bucket.backend_storage.name
  description = "GCS bucket for backend configs"
}

output "cloud_sql_instance" {
  value       = google_sql_database_instance.metadata_db.connection_name
  description = "Cloud SQL instance connection name"
}

output "cloud_sql_private_ip" {
  value       = google_sql_database_instance.metadata_db.private_ip_address
  description = "Cloud SQL private IP address"
}

output "bigquery_analytics_dataset" {
  value       = google_bigquery_dataset.analytics.dataset_id
  description = "BigQuery analytics dataset"
}

output "bigquery_audit_dataset" {
  value       = google_bigquery_dataset.audit.dataset_id
  description = "BigQuery audit dataset"
}

output "pubsub_job_topic" {
  value       = google_pubsub_topic.job_queue.name
  description = "Pub/Sub topic for job queue"
}

output "cloud_run_api_url" {
  value       = google_cloud_run_service.api.status[0].url
  description = "Cloud Run API endpoint"
}

output "api_service_account_email" {
  value       = google_service_account.api.email
  description = "API service account email"
}

output "worker_service_account_email" {
  value       = google_service_account.worker.email
  description = "Worker service account email"
}

output "redis_host" {
  value       = google_redis_instance.cache.host
  description = "Redis cache host"
}

output "redis_port" {
  value       = google_redis_instance.cache.port
  description = "Redis cache port"
}

output "kms_key_id" {
  value       = google_kms_crypto_key.key.id
  description = "Cloud KMS key ID"
}

output "db_connection_secret" {
  value       = google_secret_manager_secret.db_connection_string.id
  description = "Secret Manager ID for DB connection string"
}

output "vpc_network_name" {
  value       = google_compute_network.vpc.name
  description = "VPC network name"
}

output "subnet_name" {
  value       = google_compute_subnetwork.subnet.name
  description = "Subnet name"
}
