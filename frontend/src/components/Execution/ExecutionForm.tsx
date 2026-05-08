'use client';

import React, { useState } from 'react';
import { Agent, AgentResponse } from '@/types';
import { useAppDispatch, useAppSelector } from '@/hooks';
import { runAgent } from '@/store/slices/executionSlice';

interface ExecutionFormProps {
  agent: Agent;
  onSubmit?: (response: AgentResponse) => void;
}

export const ExecutionForm: React.FC<ExecutionFormProps> = ({
  agent,
  onSubmit,
}) => {
  const dispatch = useAppDispatch();
  const { isExecuting, current } = useAppSelector((state) => state.execution);
  const [formData, setFormData] = useState<Record<string, string>>({});

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const result = await dispatch(
      runAgent({
        agentId: agent.id,
        agentName: agent.name,
        endpoint: agent.endpoint,
        payload: formData,
      })
    );

    if (onSubmit && result.payload) {
      onSubmit(result.payload as AgentResponse);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Input Fields */}
      <div className="space-y-4">
        <div>
          <label
            htmlFor="input"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
          >
            Input
          </label>
          <textarea
            id="input"
            name="input"
            value={formData.input || ''}
            onChange={handleChange}
            placeholder="Enter your input text here..."
            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            rows={5}
            required
          />
        </div>
      </div>

      {/* Error Display */}
      {current.error && (
        <div className="p-4 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-800 dark:text-red-300">
            Error: {current.error}
          </p>
        </div>
      )}

      {/* Result Display */}
      {current.result && (
        <div className="p-4 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg">
          <p className="text-sm font-semibold text-green-800 dark:text-green-300 mb-2">
            Result:
          </p>
          <pre className="text-xs text-green-700 dark:text-green-400 overflow-auto max-h-48">
            {JSON.stringify(current.result, null, 2)}
          </pre>
        </div>
      )}

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isExecuting}
        className="w-full px-4 py-3 bg-primary-500 hover:bg-primary-600 disabled:bg-primary-300 text-white font-semibold rounded-lg transition flex items-center justify-center gap-2"
      >
        {isExecuting ? (
          <>
            <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Executing...
          </>
        ) : (
          'Execute Agent'
        )}
      </button>
    </form>
  );
};
