'use client';

import React from 'react';
import { useAppSelector, useAppDispatch } from '@/hooks';
import { clearHistory } from '@/store/slices/executionSlice';
import { ExecutionHistory } from '@/components';

export default function ExecutionHistoryPage() {
  const dispatch = useAppDispatch();
  const { history } = useAppSelector((state) => state.execution);

  const handleClearHistory = () => {
    if (confirm('Are you sure you want to clear all execution history?')) {
      dispatch(clearHistory());
    }
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Execution History
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Total executions: {history.length}
          </p>
        </div>
        {history.length > 0 && (
          <button
            onClick={handleClearHistory}
            className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white font-semibold rounded-lg transition"
          >
            Clear History
          </button>
        )}
      </div>

      {/* History Content */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        {history.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-600 dark:text-gray-400">
              No execution history yet. Execute an agent to see results here.
            </p>
          </div>
        ) : (
          <ExecutionHistory />
        )}
      </div>

      {/* Statistics */}
      {history.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              Total Executions
            </p>
            <p className="text-3xl font-bold text-gray-900 dark:text-white">
              {history.length}
            </p>
          </div>
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              Unique Agents
            </p>
            <p className="text-3xl font-bold text-gray-900 dark:text-white">
              {new Set(history.map((h) => h.agentId)).size}
            </p>
          </div>
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              Most Used Agent
            </p>
            <p className="text-lg font-bold text-gray-900 dark:text-white">
              {
                Object.entries(
                  history.reduce(
                    (acc, h) => {
                      acc[h.agentName] = (acc[h.agentName] || 0) + 1;
                      return acc;
                    },
                    {} as Record<string, number>
                  )
                ).sort(([, a], [, b]) => b - a)[0]?.[0] || 'N/A'
              }
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
