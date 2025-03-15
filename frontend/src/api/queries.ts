import apiClient from './index';

export const queryDocument = async (documentId: string, question: string, sessionId?: string) => {
  const response = await apiClient.post(`/query/${documentId}`, {
    question,
    session_id: sessionId,
  });
  return response.data;
};