import React from 'react';
import Link from 'next/link';
import { Agent } from '@/types';

interface AgentCardProps {
  agent: Agent;
}

export const AgentCard: React.FC<AgentCardProps> = ({ agent }) => {
  const statusColors = {
    active: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
    inactive: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300',
    beta: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
  };

  return (
    <Link href={`/agents/${agent.id}`}>
      <div className="h-full bg-white dark:bg-gray-900 rounded-lg shadow-md hover:shadow-lg transition-shadow p-6 cursor-pointer border border-gray-200 dark:border-gray-800 hover:border-primary-500 dark:hover:border-primary-500">
        {/* Icon and Status */}
        <div className="flex items-start justify-between mb-4">
          <div className="text-4xl">{agent.icon}</div>
          <span
            className={`text-xs font-semibold px-3 py-1 rounded-full ${
              statusColors[agent.status]
            }`}
          >
            {agent.status.charAt(0).toUpperCase() + agent.status.slice(1)}
          </span>
        </div>

        {/* Title and Description */}
        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">
          {agent.name}
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4 line-clamp-2">
          {agent.description}
        </p>

        {/* Tags */}
        <div className="flex flex-wrap gap-2 mb-4">
          {agent.tags.slice(0, 2).map((tag) => (
            <span
              key={tag}
              className="text-xs bg-primary-50 dark:bg-primary-950 text-primary-700 dark:text-primary-300 px-2 py-1 rounded"
            >
              {tag}
            </span>
          ))}
          {agent.tags.length > 2 && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              +{agent.tags.length - 2} more
            </span>
          )}
        </div>

        {/* Footer */}
        <div className="text-xs text-gray-500 dark:text-gray-400">
          v{agent.version}
        </div>
      </div>
    </Link>
  );
};
