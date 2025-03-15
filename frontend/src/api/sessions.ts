// src/api/sessions.ts
import apiClient from './index';

export const getDocumentSessions = async (documentId: string) => {
  const response = await apiClient.get(`/sessions/${documentId}`);
  return response.data;
};

export const getSessionHistory = async (sessionId: string) => {
  const response = await apiClient.get(`/sessions/history/${sessionId}`);
  return response.data;
};

export const clearSession = async (sessionId: string) => {
  const response = await apiClient.delete(`/sessions/${sessionId}`);
  return response.data;
};