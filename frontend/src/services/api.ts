import axios, { AxiosInstance, AxiosError } from 'axios';
import type { Project, Job, JobResult, Dataset, QueryHistory, User, AuthResponse } from '../types/index';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add token to requests if available
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('auth_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Handle errors globally
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Handle unauthorized access
          localStorage.removeItem('auth_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Projects
  async getProjects(): Promise<{ projects: Project[] }> {
    const response = await this.client.get('/api/v1/projects');
    return response.data;
  }

  async getProject(projectId: string): Promise<Project> {
    const response = await this.client.get(`/api/v1/projects/${projectId}`);
    return response.data;
  }

  async createProject(project: Partial<Project>): Promise<Project> {
    const response = await this.client.post('/api/v1/projects', project);
    // Handle both wrapped response and direct project object
    if (response.data?.project) {
      return response.data.project;
    }
    return response.data as Project;
  }

  // Authentication
  async register(email: string, password: string, name: string) {
    const response = await this.client.post('/api/v1/auth/register', {
      email,
      password,
      name,
    });
    return response.data;
  }

  async login(email: string, password: string) {
    const response = await this.client.post('/api/v1/auth/login', {
      email,
      password,
    });
    return response.data;
  }

  async getProfile() {
    const response = await this.client.get('/api/v1/auth/profile');
    return response.data;
  }

  async updateProfile(updates: Record<string, unknown>) {
    const response = await this.client.put('/api/v1/auth/profile', updates);
    return response.data;
  }

  // Datasets
  async getDatasets(projectId: string): Promise<{ datasets: Dataset[] }> {
    const response = await this.client.get(`/api/v1/projects/${projectId}/datasets`);
    return response.data;
  }

  async uploadDataset(
    projectId: string,
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<Dataset> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.client.post(
      `/api/v1/projects/${projectId}/datasets`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const progress = Math.round(
              (progressEvent.loaded / progressEvent.total) * 100
            );
            onProgress?.(progress);
          }
        },
      }
    );

    return response.data;
  }

  async getPresignedUploadUrl(projectId: string, fileName: string) {
    const response = await this.client.post(
      `/api/v1/projects/${projectId}/presigned-url`,
      { file_name: fileName }
    );
    return response.data;
  }

  // Jobs / Queries
  async submitJob(payload: {
    query: string;
    dataset_id: string;
    options?: Record<string, unknown>;
  }): Promise<Job> {
    const response = await this.client.post('/api/v1/jobs', payload);
    return response.data;
  }

  async getJobStatus(jobId: string): Promise<JobResult> {
    const response = await this.client.get(`/api/v1/jobs/${jobId}`);
    return response.data;
  }

  async pollJobStatus(jobId: string, maxAttempts = 60): Promise<JobResult> {
    let attempts = 0;
    const interval = 1000; // 1 second

    return new Promise((resolve, reject) => {
      const checkStatus = async () => {
        try {
          const result = await this.getJobStatus(jobId);
          if (result.status === 'completed' || result.status === 'failed') {
            resolve(result);
          } else if (attempts < maxAttempts) {
            attempts++;
            setTimeout(checkStatus, interval);
          } else {
            reject(new Error('Job polling timeout'));
          }
        } catch (error) {
          reject(error);
        }
      };
      checkStatus();
    });
  }

  // Artifacts
  async getArtifact(artifactId: string) {
    const response = await this.client.get(`/api/v1/artifacts/${artifactId}`);
    return response.data;
  }

  // Query History
  async getQueryHistory(projectId: string): Promise<{ history: QueryHistory[] }> {
    const response = await this.client.get(
      `/api/v1/projects/${projectId}/query-history`
    );
    return response.data;
  }

  async deleteQueryHistoryItem(historyId: string): Promise<void> {
    await this.client.delete(`/api/v1/query-history/${historyId}`);
  }

  // Health check
  async getHealth() {
    const response = await this.client.get('/health');
    return response.data;
  }
}

export const apiClient = new APIClient();
