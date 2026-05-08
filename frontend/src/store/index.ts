import { configureStore } from '@reduxjs/toolkit';
import agentReducer     from './slices/agentSlice';
import executionReducer from './slices/executionSlice';
import uiReducer        from './slices/uiSlice';
import dependencyResolverReducer from './slices/dependencyResolverSlice';

export const store = configureStore({
  reducer: {
    agents:             agentReducer,
    execution:          executionReducer,
    ui:                 uiReducer,
    dependencyResolver: dependencyResolverReducer,
  },
});

export type RootState   = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
