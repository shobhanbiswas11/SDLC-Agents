import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface UIState {
  sidebarOpen: boolean;
  darkMode: boolean;
  notifications: Notification[];
  toastMessage: string | null;
  toastType: 'success' | 'error' | 'info' | 'warning';
}

interface Notification {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info' | 'warning';
  timestamp: number;
}

const initialState: UIState = {
  sidebarOpen: true,
  darkMode: false,
  notifications: [],
  toastMessage: null,
  toastType: 'info',
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    toggleSidebar: (state) => {
      state.sidebarOpen = !state.sidebarOpen;
    },
    setSidebarOpen: (state, action: PayloadAction<boolean>) => {
      state.sidebarOpen = action.payload;
    },
    toggleDarkMode: (state) => {
      state.darkMode = !state.darkMode;
    },
    setDarkMode: (state, action: PayloadAction<boolean>) => {
      state.darkMode = action.payload;
    },
    addNotification: (state, action: PayloadAction<Omit<Notification, 'id' | 'timestamp'>>) => {
      const notification: Notification = {
        id: `notification-${Date.now()}`,
        timestamp: Date.now(),
        ...action.payload,
      };
      state.notifications.push(notification);
    },
    removeNotification: (state, action: PayloadAction<string>) => {
      state.notifications = state.notifications.filter(
        (notif) => notif.id !== action.payload
      );
    },
    clearNotifications: (state) => {
      state.notifications = [];
    },
    showToast: (
      state,
      action: PayloadAction<{
        message: string;
        type: 'success' | 'error' | 'info' | 'warning';
      }>
    ) => {
      state.toastMessage = action.payload.message;
      state.toastType = action.payload.type;
    },
    hideToast: (state) => {
      state.toastMessage = null;
    },
  },
});

export const {
  toggleSidebar,
  setSidebarOpen,
  toggleDarkMode,
  setDarkMode,
  addNotification,
  removeNotification,
  clearNotifications,
  showToast,
  hideToast,
} = uiSlice.actions;

export default uiSlice.reducer;
