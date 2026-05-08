'use client';

import React, { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAppDispatch, useAppSelector } from '@/hooks';
import { getAgentById } from '@/store/slices/agentSlice';
import { ExecutionForm, ExecutionHistory } from '@/components';

export default function AgentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const dispatch = useAppDispatch();
  const { selectedAgent, isLoading, error } = useAppSelector(
    (state) => state.agents
  );
  const agentId = params.id as string;

  useEffect(() => {
    if (agentId) {
      dispatch(getAgentById(agentId));
    }
  }, [agentId, dispatch]);

  if (isLoading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full animate-spin" />
        <p className="mt-4 text-gray-600 dark:text-gray-400">Loading agent...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-2xl">
        <button
          onClick={() => router.back()}
          className="mb-4 text-primary-600 dark:text-primary-400 hover:underline text-sm font-semibold"
        >
          ← Back
        </button>
        <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 p-4 rounded-lg">
          <p className="text-red-800 dark:text-red-300">
            Failed to load agent: {error.message}
          </p>
        </div>
      </div>
    );
  }

  if (!selectedAgent) {
    return (
      <div className="max-w-2xl">
        <button
          onClick={() => router.back()}
          className="mb-4 text-primary-600 dark:text-primary-400 hover:underline text-sm font-semibold"
        >
          ← Back
        </button>
        <div className="text-center py-12 text-gray-600 dark:text-gray-400">
          <p>Agent not found</p>
        </div>
      </div>
    );
  }

  const statusColors = {
    active: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
    inactive: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300',
    beta: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
  };

  return (
    <div className="space-y-8">
      {/* Back Button */}
      <button
        onClick={() => router.back()}
        className="text-primary-600 dark:text-primary-400 hover:underline text-sm font-semibold"
      >
        ← Back to Agents
      </button>

      {/* Agent Header */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-start gap-6">
            <div className="text-6xl">{selectedAgent.icon}</div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                {selectedAgent.name}
              </h1>
              <p className="text-gray-600 dark:text-gray-400 mt-2">
                {selectedAgent.description}
              </p>
            </div>
          </div>
          <span
            className={`text-xs font-semibold px-4 py-2 rounded-full ${
              statusColors[selectedAgent.status]
            }`}
          >
            {selectedAgent.status.charAt(0).toUpperCase() + selectedAgent.status.slice(1)}
          </span>
        </div>

        {/* Details Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
          <div>
            <p className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              Category
            </p>
            <p className="text-gray-900 dark:text-white capitalize">
              {selectedAgent.category.replace(/_/g, ' ')}
            </p>
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              Version
            </p>
            <p className="text-gray-900 dark:text-white">{selectedAgent.version}</p>
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              Endpoint
            </p>
            <p className="text-gray-900 dark:text-white text-xs break-all font-mono">
              {selectedAgent.endpoint}
            </p>
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-700 dark:text-gray-300">Tags</p>
            <div className="flex flex-wrap gap-2 mt-2">
              {selectedAgent.tags.map((tag) => (
                <span
                  key={tag}
                  className="text-xs bg-primary-50 dark:bg-primary-950 text-primary-700 dark:text-primary-300 px-2 py-1 rounded"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Execution Form */}
        <div className="lg:col-span-1">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
              Execute Agent
            </h2>
            <ExecutionForm agent={selectedAgent} />
          </div>
        </div>

        {/* Execution History */}
        <div className="lg:col-span-2">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <ExecutionHistory />
          </div>
        </div>
      </div>
    </div>
  );
}
