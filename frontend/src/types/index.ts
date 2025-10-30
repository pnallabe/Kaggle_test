/**
 * Type definitions for AI Data Analyst Frontend
 */

/**
 * AUTHENTICATION TYPES
 */

export interface User {
  user_id: string;
  email: string;
  name: string;
  created_at: string;
  updated_at?: string;
  profile?: {
    avatar_url?: string | null;
    bio?: string;
    organization?: string;
    phone?: string;
  };
  settings?: {
    dark_mode?: boolean;
    notifications_enabled?: boolean;
    notifications_email?: boolean;
  };
  storage?: {
    used_mb?: number;
    max_mb?: number;
    percentage_used?: number;
  };
}

export interface AuthResponse {
  user: User;
  token: string;
  message: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  isAuthenticated: boolean;
}

/**
 * PROJECT TYPES
 */

export interface Project {
  id: string;
  user_id?: string;
  name: string;
  description: string;
  created_at: string;
  status: 'active' | 'archived' | 'deleted';
  data_sources: string[];
  last_updated: string;
}

/**
 * DATASET TYPES
 */

export interface Dataset {
  id: string;
  user_id?: string;
  name: string;
  file_name?: string;
  file_type?: 'csv' | 'bigquery' | 'postgresql' | 'salesforce';
  type?: 'csv' | 'bigquery' | 'postgresql' | 'salesforce';
  size_bytes: number;
  row_count?: number;
  rows?: number;
  columns?: Column[];
  column_names?: string[];
  created_at: string;
  updated_at?: string;
  project_id?: string | null;
  description?: string;
}

export interface Column {
  name: string;
  type: 'string' | 'number' | 'date' | 'boolean';
  nullable: boolean;
}

export interface Job {
  job_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress: number;
  created_at: string;
  estimated_completion?: string;
  priority: 'low' | 'normal' | 'high';
  queue_position?: number;
}

export interface JobResult extends Job {
  results?: {
    summary: {
      total_records_analyzed: number;
      analysis_duration_seconds: number;
      confidence_score: number;
    };
    insights: string[];
    visualizations: Visualization[];
  };
  error?: string;
}

export interface Visualization {
  id: string;
  type: 'line_chart' | 'bar_chart' | 'scatter' | 'histogram' | 'table';
  title: string;
  data: Record<string, unknown>;
  layout?: Record<string, unknown>;
}

export interface Artifact {
  id: string;
  type: 'chart' | 'table' | 'text';
  content: Record<string, unknown>;
  created_at: string;
}

export interface User {
  user_id: string;
  email: string;
  name: string;
  created_at: string;
  updated_at?: string;
  profile?: {
    avatar_url?: string | null;
    bio?: string;
    organization?: string;
    phone?: string;
  };
  settings?: {
    dark_mode?: boolean;
    notifications_enabled?: boolean;
    notifications_email?: boolean;
  };
  storage?: {
    used_mb?: number;
    max_mb?: number;
    percentage_used?: number;
  };
}

export interface Workspace {
  id: string;
  name: string;
  owner_id: string;
  members: User[];
  created_at: string;
}

export interface QueryHistory {
  id: string;
  query: string;
  job_id: string;
  dataset_id: string;
  created_at: string;
  results_summary?: string;
}

export interface UploadProgress {
  file_name: string;
  progress: number;
  status: 'pending' | 'uploading' | 'completed' | 'failed';
  error?: string;
}
