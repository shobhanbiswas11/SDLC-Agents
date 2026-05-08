import { apiClient } from './api';
import { AgentResponse } from '@/types';

export const executionService = {
  /**
   * Execute an agent with given payload
   */
  async executeAgent(
    agentEndpoint: string,
    payload: Record<string, any>
  ): Promise<AgentResponse> {
    const response = await apiClient.post<AgentResponse>(
      agentEndpoint,
      payload
    );
    return response.data;
  },

  /**
   * Get execution history for an agent
   */
  async getExecutionHistory(
    agentId: string,
    limit: number = 10
  ): Promise<Record<string, any>[]> {
    const response = await apiClient.get<Record<string, any>[]>(
      `/api/agents/${agentId}/executions?limit=${limit}`
    );
    return response.data;
  },

  /**
   * Get execution status
   */
  async getExecutionStatus(executionId: string): Promise<AgentResponse> {
    const response = await apiClient.get<AgentResponse>(
      `/api/executions/${executionId}`
    );
    return response.data;
  },

  /**
   * Cancel ongoing execution
   */
  async cancelExecution(executionId: string): Promise<void> {
    await apiClient.post(`/api/executions/${executionId}/cancel`);
  },
};

// Standalone function for Redux thunk compatibility
export const executeAgent = async (
  endpoint: string,
  payload: Record<string, any>
): Promise<AgentResponse> => {
  const response = await apiClient.post<AgentResponse>(endpoint, payload);
  return response.data;
};
