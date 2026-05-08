import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Agent, ApiError } from '@/types';
import { fetchAgents, fetchAgentById } from '@/services/agentService';

export interface AgentState {
  agents: Agent[];
  selectedAgent: Agent | null;
  isLoading: boolean;
  error: ApiError | null;
}

const initialState: AgentState = {
  agents: [],
  selectedAgent: null,
  isLoading: false,
  error: null,
};

export const getAgents = createAsyncThunk<
  Agent[],
  void,
  { rejectValue: ApiError }
>('agents/getAgents', async (_, { rejectWithValue }) => {
  try {
    const response = await fetchAgents();
    return response;
  } catch (error: any) {
    return rejectWithValue({
      code: 'FETCH_AGENTS_ERROR',
      message: error.message || 'Failed to fetch agents',
    });
  }
});

export const getAgentById = createAsyncThunk<
  Agent,
  string,
  { rejectValue: ApiError }
>('agents/getAgentById', async (id: string, { rejectWithValue }) => {
  try {
    const response = await fetchAgentById(id);
    return response;
  } catch (error: any) {
    return rejectWithValue({
      code: 'FETCH_AGENT_ERROR',
      message: error.message || 'Failed to fetch agent',
    });
  }
});

const agentSlice = createSlice({
  name: 'agents',
  initialState,
  reducers: {
    selectAgent: (state, action: PayloadAction<Agent>) => {
      state.selectedAgent = action.payload;
    },
    clearSelectedAgent: (state) => {
      state.selectedAgent = null;
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // Get agents
    builder
      .addCase(getAgents.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(getAgents.fulfilled, (state, action) => {
        state.isLoading = false;
        state.agents = action.payload;
      })
      .addCase(getAgents.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload || {
          code: 'UNKNOWN_ERROR',
          message: 'An unknown error occurred',
        };
      });

    // Get agent by ID
    builder
      .addCase(getAgentById.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(getAgentById.fulfilled, (state, action) => {
        state.isLoading = false;
        state.selectedAgent = action.payload;
      })
      .addCase(getAgentById.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload || {
          code: 'UNKNOWN_ERROR',
          message: 'An unknown error occurred',
        };
      });
  },
});

export const { selectAgent, clearSelectedAgent, clearError } = agentSlice.actions;
export default agentSlice.reducer;
