import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { apiClient } from '@services/api';
import { Dataset } from '@types/index';

interface DatasetState {
  datasets: Dataset[];
  currentDataset: Dataset | null;
  loading: boolean;
  error: string | null;
  uploadProgress: Record<string, number>;
}

const initialState: DatasetState = {
  datasets: [],
  currentDataset: null,
  loading: false,
  error: null,
  uploadProgress: {},
};

export const fetchDatasets = createAsyncThunk(
  'datasets/fetchDatasets',
  async (projectId: string, { rejectWithValue }) => {
    try {
      const data = await apiClient.getDatasets(projectId);
      return data.datasets;
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch datasets';
      return rejectWithValue(errorMessage);
    }
  }
);

export const uploadDataset = createAsyncThunk(
  'datasets/uploadDataset',
  async (
    { projectId, file }: { projectId: string; file: File },
    { dispatch, rejectWithValue }
  ) => {
    try {
      const dataset = await apiClient.uploadDataset(projectId, file, (progress) => {
        dispatch(setUploadProgress({ fileName: file.name, progress }));
      });
      dispatch(clearUploadProgress(file.name));
      return dataset;
    } catch (error: unknown) {
      dispatch(clearUploadProgress(file.name));
      const errorMessage = error instanceof Error ? error.message : 'Failed to upload dataset';
      return rejectWithValue(errorMessage);
    }
  }
);

const datasetSlice = createSlice({
  name: 'datasets',
  initialState,
  reducers: {
    setCurrentDataset: (state, action: PayloadAction<Dataset | null>) => {
      state.currentDataset = action.payload;
    },
    setUploadProgress: (
      state,
      action: PayloadAction<{ fileName: string; progress: number }>
    ) => {
      state.uploadProgress[action.payload.fileName] = action.payload.progress;
    },
    clearUploadProgress: (state, action: PayloadAction<string>) => {
      delete state.uploadProgress[action.payload];
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchDatasets.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchDatasets.fulfilled, (state, action) => {
        state.loading = false;
        state.datasets = action.payload;
      })
      .addCase(fetchDatasets.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(uploadDataset.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(uploadDataset.fulfilled, (state, action) => {
        state.loading = false;
        state.datasets.push(action.payload);
      })
      .addCase(uploadDataset.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

export const { setCurrentDataset, setUploadProgress, clearUploadProgress, clearError } =
  datasetSlice.actions;
export default datasetSlice.reducer;
