'use client';

import React, { useEffect, useState } from 'react';
import { useAppDispatch, useAppSelector } from '@/hooks';
import { getAgents } from '@/store/slices/agentSlice';
import { AgentCard } from '@/components';
import { AgentCategory } from '@/types';

const CATEGORIES: { value: AgentCategory; label: string }[] = [
  { value: 'text_processing', label: 'Text Processing' },
  { value: 'data_analysis', label: 'Data Analysis' },
  { value: 'content_generation', label: 'Content Generation' },
  { value: 'code_generation', label: 'Code Generation' },
  { value: 'image_processing', label: 'Image Processing' },
  { value: 'translation', label: 'Translation' },
  { value: 'summarization', label: 'Summarization' },
  { value: 'classification', label: 'Classification' },
  { value: 'extraction', label: 'Extraction' },
];

export default function AgentsPage() {
  const dispatch = useAppDispatch();
  const { agents, isLoading, error } = useAppSelector((state) => state.agents);
  const [selectedCategory, setSelectedCategory] = useState<AgentCategory | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    dispatch(getAgents());
  }, [dispatch]);

  const filteredAgents = agents.filter((agent) => {
    const matchesCategory = selectedCategory ? agent.category === selectedCategory : true;
    const matchesSearch =
      agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      agent.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          All Agents
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Explore all available AI agents ({agents.length} total)
        </p>
      </div>

      {/* Search and Filter */}
      <div className="space-y-4">
        {/* Search */}
        <div>
          <input
            type="text"
            placeholder="Search agents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>

        {/* Category Filter */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setSelectedCategory(null)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition ${
              selectedCategory === null
                ? 'bg-primary-500 text-white'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white hover:bg-gray-300 dark:hover:bg-gray-600'
            }`}
          >
            All
          </button>
          {CATEGORIES.map((cat) => (
            <button
              key={cat.value}
              onClick={() => setSelectedCategory(cat.value)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition ${
                selectedCategory === cat.value
                  ? 'bg-primary-500 text-white'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white hover:bg-gray-300 dark:hover:bg-gray-600'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Results Count */}
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Showing {filteredAgents.length} agent{filteredAgents.length !== 1 ? 's' : ''}
      </div>

      {/* Agents Grid */}
      {isLoading ? (
        <div className="text-center py-12">
          <div className="inline-block w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full animate-spin" />
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading agents...</p>
        </div>
      ) : error ? (
        <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 p-4 rounded-lg">
          <p className="text-red-800 dark:text-red-300">
            Failed to load agents: {error.message}
          </p>
        </div>
      ) : filteredAgents.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredAgents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      ) : (
        <div className="text-center py-12 text-gray-600 dark:text-gray-400">
          <p>No agents found matching your criteria</p>
        </div>
      )}
    </div>
  );
}
