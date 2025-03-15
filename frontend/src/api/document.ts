import apiClient from './index';

export const uploadDocument = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await apiClient.post('/upload/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const getDocuments = async () => {
  const response = await apiClient.get('/documents/');
  return response.data;
};

export const deleteDocument = async (documentId: string) => {
  const response = await apiClient.delete(`/documents/${documentId}`);
  return response.data;
};