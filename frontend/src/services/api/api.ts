/**
 * Shared axios client used by every agent service.
 */
import axios, { AxiosError, AxiosInstance } from 'axios';
import type { ApiError } from '@/types';

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private client: AxiosInstance;

  constructor(baseURL: string) {
    this.client = axios.create({
      baseURL,
      headers: { 'Content-Type': 'application/json' },
      timeout: 60_000,
    });

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ApiError>) => {
        return Promise.reject(
          error.response?.data || {
            code: 'NETWORK_ERROR',
            message: 'Network error occurred',
          },
        );
      },
    );
  }

  get<T = any>(url: string, config = {}) {
    return this.client.get<T>(url, config);
  }

  post<T = any>(url: string, data?: any, config = {}) {
    return this.client.post<T>(url, data, config);
  }

  delete<T = any>(url: string, config = {}) {
    return this.client.delete<T>(url, config);
  }

  /** Returns the underlying axios instance for streaming/raw use cases. */
  raw() {
    return this.client;
  }

  baseURL() {
    return API_BASE_URL;
  }
}

export const apiClient = new ApiClient(API_BASE_URL);
export const API_BASE = API_BASE_URL;
