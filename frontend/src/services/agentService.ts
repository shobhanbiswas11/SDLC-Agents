import { apiClient } from './api';
import { Agent, PaginatedResponse } from '@/types';

const AGENTS_ENDPOINT = '/api/agents';

export const agentService = {
  /**
   * Fetch all available agents
   */
  async getAllAgents(
    page: number = 1,
    limit: number = 10
  ): Promise<PaginatedResponse<Agent>> {
    const response = await apiClient.get<PaginatedResponse<Agent>>(
      `${AGENTS_ENDPOINT}?page=${page}&limit=${limit}`
    );
    return response.data;
  },

  /**
   * Fetch agent by ID
   */
  async getAgentById(id: string): Promise<Agent> {
    const response = await apiClient.get<Agent>(
      `${AGENTS_ENDPOINT}/${id}`
    );
    return response.data;
  },

  /**
   * Search agents by query
   */
  async searchAgents(query: string): Promise<Agent[]> {
    const response = await apiClient.get<Agent[]>(
      `${AGENTS_ENDPOINT}/search?q=${encodeURIComponent(query)}`
    );
    return response.data;
  },

  /**
   * Get agents by category
   */
  async getAgentsByCategory(category: string): Promise<Agent[]> {
    const response = await apiClient.get<Agent[]>(
      `${AGENTS_ENDPOINT}/category/${category}`
    );
    return response.data;
  },

  /**
   * Get agent metadata and documentation
   */
  async getAgentMetadata(id: string): Promise<Record<string, any>> {
    const response = await apiClient.get<Record<string, any>>(
      `${AGENTS_ENDPOINT}/${id}/metadata`
    );
    return response.data;
  },
};

// Standalone functions for compatibility with Redux thunks
export const fetchAgents = async (): Promise<Agent[]> => {
  const response = await apiClient.get<Agent[]>(AGENTS_ENDPOINT);
  return response.data;
};

export const fetchAgentById = async (id: string): Promise<Agent> => {
  const response = await apiClient.get<Agent>(
    `${AGENTS_ENDPOINT}/${id}`
  );
  return response.data;
};
