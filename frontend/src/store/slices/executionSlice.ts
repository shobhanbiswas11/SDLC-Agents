import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { AgentResponse, ExecutionState } from '@/types';
import { executeAgent } from '@/services/executionService';

interface ExecutionHistory {
  id: string;
  agentId: string;
  agentName: string;
  input: Record<string, any>;
  output: AgentResponse;
  timestamp: string;
  duration: number;
}

export interface ExecutionStateType {
  current: ExecutionState;
  history: ExecutionHistory[];
  isExecuting: boolean;
  error: string | null;
}

const initialState: ExecutionStateType = {
  current: {
    isLoading: false,
    error: null,
    result: null,
  },
  history: [],
  isExecuting: false,
  error: null,
};

export const runAgent = createAsyncThunk<
  AgentResponse,
  {
    agentId: string;
    agentName: string;
    endpoint: string;
    payload: Record<string, any>;
  },
  { rejectValue: string }
>(
  'execution/runAgent',
  async ({ endpoint, payload }, { rejectWithValue }) => {
    try {
      const response = await executeAgent(endpoint, payload);
      return response;
    } catch (error: any) {
      return rejectWithValue(
        error.message || 'Failed to execute agent'
      );
    }
  }
);

const executionSlice = createSlice({
  name: 'execution',
  initialState,
  reducers: {
    setResult: (state, action: PayloadAction<any>) => {
      state.current.result = action.payload;
    },
    clearResult: (state) => {
      state.current.result = null;
      state.current.error = null;
    },
    clearError: (state) => {
      state.current.error = null;
    },
    clearHistory: (state) => {
      state.history = [];
    },
    removeFromHistory: (state, action: PayloadAction<string>) => {
      state.history = state.history.filter((item) => item.id !== action.payload);
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(runAgent.pending, (state) => {
        state.isExecuting = true;
        state.current.isLoading = true;
        state.current.error = null;
      })
      .addCase(runAgent.fulfilled, (state, action) => {
        state.isExecuting = false;
        state.current.isLoading = false;
        state.current.result = action.payload;

        // Add to history
        const historyItem: ExecutionHistory = {
          id: `exec-${Date.now()}`,
          agentId: action.meta.arg.agentId,
          agentName: action.meta.arg.agentName,
          input: action.meta.arg.payload,
          output: action.payload,
          timestamp: new Date().toISOString(),
          duration: 0,
        };
        state.history.unshift(historyItem);

        // Keep only last 50 items
        if (state.history.length > 50) {
          state.history = state.history.slice(0, 50);
        }
      })
      .addCase(runAgent.rejected, (state, action) => {
        state.isExecuting = false;
        state.current.isLoading = false;
        state.current.error = action.payload || 'Unknown error occurred';
        state.error = action.payload || 'Unknown error occurred';
      });
  },
});

export const { setResult, clearResult, clearError, clearHistory, removeFromHistory } =
  executionSlice.actions;

export default executionSlice.reducer;
