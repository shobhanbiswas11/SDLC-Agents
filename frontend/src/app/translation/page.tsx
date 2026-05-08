'use client';

import React, { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@/hooks';
import { getAgents } from '@/store/slices/agentSlice';
import { AgentCard } from '@/components';

export default function TranslationPage() {
  const dispatch = useAppDispatch();
  const { agents, isLoading } = useAppSelector((state) => state.agents);

  useEffect(() => {
    dispatch(getAgents());
  }, [dispatch]);

  const categoryAgents = agents.filter((a) => a.category === 'translation');

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          🌐 Translation Agents
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Translate content across multiple languages with high accuracy.
        </p>
      </div>

      {isLoading ? (
        <div className="text-center py-12">
          <div className="inline-block w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full animate-spin" />
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading agents...</p>
        </div>
      ) : categoryAgents.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {categoryAgents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      ) : (
        <div className="text-center py-12 text-gray-600 dark:text-gray-400">
          <p>No translation agents available yet.</p>
        </div>
      )}
    </div>
  );
}
