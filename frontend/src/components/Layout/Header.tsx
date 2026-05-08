import React from 'react';
import Link from 'next/link';
import { useAppDispatch, useAppSelector } from '@/hooks';
import { toggleSidebar, toggleDarkMode } from '@/store/slices/uiSlice';

export const Header: React.FC = () => {
  const dispatch = useAppDispatch();
  const { darkMode } = useAppSelector((state) => state.ui);

  return (
    <header className="bg-white dark:bg-gray-900 shadow-sm border-b border-gray-200 dark:border-gray-800">
      <div className="flex items-center justify-between h-16 px-4 sm:px-6 lg:px-8">
        {/* Logo and Title */}
        <Link href="/" className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-lg" />
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">
            Agent Garden
          </h1>
        </Link>

        {/* Actions */}
        <div className="flex items-center gap-4">
          {/* Dark Mode Toggle */}
          <button
            onClick={() => dispatch(toggleDarkMode())}
            className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
            aria-label="Toggle dark mode"
          >
            {darkMode ? '☀️' : '🌙'}
          </button>

          {/* Sidebar Toggle */}
          <button
            onClick={() => dispatch(toggleSidebar())}
            className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition lg:hidden"
            aria-label="Toggle sidebar"
          >
            ☰
          </button>

          {/* Profile Menu */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-primary-500 rounded-full flex items-center justify-center text-white text-sm font-semibold">
              A
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
