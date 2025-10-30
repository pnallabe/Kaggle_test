import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { apiClient } from '@services/api';
import { Job, JobResult } from '@types/index';

interface JobState {
  jobs: Record<string, JobResult>;
  currentJobId: string | null;
  loading: boolean;
  error: string | null;
  polling: boolean;
}

const initialState: JobState = {
  jobs: {},
  currentJobId: null,
  loading: false,
  error: null,
  polling: false,
};

export const submitJob = createAsyncThunk(
  'jobs/submitJob',
  async (payload: { query: string; dataset_id: string }, { rejectWithValue }) => {
    try {
      const data = await apiClient.submitJob(payload);
      return data;
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to submit job';
      return rejectWithValue(errorMessage);
    }
  }
);

export const pollJobCompletion = createAsyncThunk(
  'jobs/pollJobCompletion',
  async (jobId: string, { rejectWithValue }) => {
    try {
      const result = await apiClient.pollJobStatus(jobId);
      return result;
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Job polling failed';
      return rejectWithValue(errorMessage);
    }
  }
);

export const getJobStatus = createAsyncThunk(
  'jobs/getJobStatus',
  async (jobId: string, { rejectWithValue }) => {
    try {
      const result = await apiClient.getJobStatus(jobId);
      return result;
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to get job status';
      return rejectWithValue(errorMessage);
    }
  }
);

const jobSlice = createSlice({
  name: 'jobs',
  initialState,
  reducers: {
    setCurrentJob: (state, action: PayloadAction<string | null>) => {
      state.currentJobId = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(submitJob.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(submitJob.fulfilled, (state, action) => {
        state.loading = false;
        const job = action.payload;
        state.jobs[job.job_id] = job;
        state.currentJobId = job.job_id;
      })
      .addCase(submitJob.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(pollJobCompletion.pending, (state) => {
        state.polling = true;
      })
      .addCase(pollJobCompletion.fulfilled, (state, action) => {
        state.polling = false;
        const result = action.payload;
        state.jobs[result.job_id] = result;
      })
      .addCase(pollJobCompletion.rejected, (state, action) => {
        state.polling = false;
        state.error = action.payload as string;
      })
      .addCase(getJobStatus.fulfilled, (state, action) => {
        const result = action.payload;
        state.jobs[result.job_id] = result;
      });
  },
});

export const { setCurrentJob, clearError } = jobSlice.actions;
export default jobSlice.reducer;
