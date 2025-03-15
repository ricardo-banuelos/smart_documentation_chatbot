export interface DocumentInfo {
    id: string;
    filename: string;
    upload_date: string;
  }
  
  export interface SessionInfo {
    session_id: string;
    document_id: string;
    created_at: string;
    last_activity: string;
  }
  
  export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
    timestamp?: string;
  }
  
  export interface ChatHistoryResponse {
    messages: ChatMessage[];
    session_id: string;
  }
  
  export interface QueryResponse {
    answer: string;
    sources: string[];
    session_id: string;
  }