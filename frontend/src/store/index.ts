import { configureStore } from '@reduxjs/toolkit';
import codingStandardsReducer from './slices/codingStandardsSlice';
import chatReducer from './slices/chatSlice';
import uiReducer from './slices/uiSlice';

export const store = configureStore({
  reducer: {
    codingStandards: codingStandardsReducer,
    chat: chatReducer,
    ui: uiReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
