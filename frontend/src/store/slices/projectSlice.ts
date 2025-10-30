import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { apiClient } from '@services/api';
import { Project } from '@types/index';

interface ProjectState {
  projects: Project[];
  currentProject: Project | null;
  loading: boolean;
  error: string | null;
}

const initialState: ProjectState = {
  projects: [],
  currentProject: null,
  loading: false,
  error: null,
};

export const fetchProjects = createAsyncThunk(
  'projects/fetchProjects',
  async (_, { rejectWithValue }) => {
    try {
      const data = await apiClient.getProjects();
      return data.projects || data || [];
    } catch (error: any) {
      console.error('Fetch projects error:', error);
      const errorMessage = error?.response?.data?.error || error?.message || 'Failed to fetch projects';
      return rejectWithValue(errorMessage);
    }
  }
);

export const createProject = createAsyncThunk(
  'projects/createProject',
  async (project: Partial<Project>, { rejectWithValue }) => {
    try {
      const data = await apiClient.createProject(project);
      // Handle both direct project object and wrapped response
      const projectData = (data as any).project || data;
      return projectData;
    } catch (error: any) {
      console.error('Create project error:', error);
      const errorMessage = error?.response?.data?.error || error?.message || 'Failed to create project';
      return rejectWithValue(errorMessage);
    }
  }
);

const projectSlice = createSlice({
  name: 'projects',
  initialState,
  reducers: {
    setCurrentProject: (state, action: PayloadAction<Project | null>) => {
      state.currentProject = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchProjects.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchProjects.fulfilled, (state, action) => {
        state.loading = false;
        state.projects = action.payload;
      })
      .addCase(fetchProjects.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(createProject.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(createProject.fulfilled, (state, action) => {
        state.loading = false;
        state.projects.push(action.payload);
      })
      .addCase(createProject.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

export const { setCurrentProject, clearError } = projectSlice.actions;
export default projectSlice.reducer;
