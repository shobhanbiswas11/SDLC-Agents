import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface UIState {
  showFileTree: boolean;
  fileSearchQuery: string;
  expandedViolations: Record<number, boolean>;
}

const initialState: UIState = {
  showFileTree: true,
  fileSearchQuery: '',
  expandedViolations: {},
};

const slice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setShowFileTree(state, { payload }: PayloadAction<boolean>) {
      state.showFileTree = payload;
    },
    setFileSearchQuery(state, { payload }: PayloadAction<string>) {
      state.fileSearchQuery = payload;
    },
    toggleExpandedViolation(state, { payload }: PayloadAction<number>) {
      state.expandedViolations[payload] = !state.expandedViolations[payload];
    },
    resetExpandedViolations(state) {
      state.expandedViolations = {};
    },
  },
});

export const uiActions = slice.actions;
export default slice.reducer;
