export * from './codingStandards';
export * from './chat';

export interface ApiError {
  code: string;
  message: string;
  detail?: string;
}
