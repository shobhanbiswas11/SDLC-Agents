'use client';

import React from 'react';
import { useAppSelector, useAppDispatch } from '@/hooks';
import { removeFromHistory } from '@/store/slices/executionSlice';

const formatTimeAgo = (timestamp: string): string => {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
};

export const ExecutionHistory: React.FC = () => {
  const dispatch = useAppDispatch();
  const { history } = useAppSelector((state) => state.execution);

  if (history.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-600 dark:text-gray-400">
          No execution history yet
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
        Execution History
      </h2>

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {history.map((execution) => (
          <div
            key={execution.id}
            className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:shadow-md transition"
          >
            <div className="flex items-start justify-between mb-2">
              <div>
                <p className="font-semibold text-gray-900 dark:text-white">
                  {execution.agentName}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {formatTimeAgo(execution.timestamp)}
                </p>
              </div>
              <button
                onClick={() => dispatch(removeFromHistory(execution.id))}
                className="text-gray-400 hover:text-red-500 dark:hover:text-red-400 transition"
                title="Remove from history"
              >
                ✕
              </button>
            </div>

            <details className="text-sm">
              <summary className="cursor-pointer text-primary-600 dark:text-primary-400 hover:underline">
                View details
              </summary>
              <div className="mt-2 space-y-2 ml-4">
                <div>
                  <p className="text-xs font-semibold text-gray-600 dark:text-gray-400">
                    Input:
                  </p>
                  <pre className="text-xs bg-gray-100 dark:bg-gray-900 p-2 rounded overflow-auto max-h-24">
                    {JSON.stringify(execution.input, null, 2)}
                  </pre>
                </div>
                <div>
                  <p className="text-xs font-semibold text-gray-600 dark:text-gray-400">
                    Output:
                  </p>
                  <pre className="text-xs bg-gray-100 dark:bg-gray-900 p-2 rounded overflow-auto max-h-24">
                    {JSON.stringify(execution.output, null, 2)}
                  </pre>
                </div>
              </div>
            </details>
          </div>
        ))}
      </div>
    </div>
  );
};
