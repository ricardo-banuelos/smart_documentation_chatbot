import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

from .document_loaders import DocumentLoaderFactory

# Load environment variables from .env file
load_dotenv()

class DocumentQueryEngine:
    """Base query engine for all document types"""
    
    def __init__(self, openai_api_key=None, model_name="gpt-3.5-turbo"):
        """
        Initialize the document query engine with conversational memory.
        
        Args:
            openai_api_key: Your OpenAI API key. If None, will look for OPENAI_API_KEY in environment variables.
            model_name: The OpenAI model to use for answering questions.
        """
        # Set API key
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Please provide it as an argument or set OPENAI_API_KEY environment variable.")
        
        # Set the model name
        self.model_name = model_name
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(openai_api_key=self.api_key)
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model_name=self.model_name,
            temperature=0,
            openai_api_key=self.api_key
        )
        
        # Vector store
        self.vector_store = None
        
        # Initialize memory storage for different sessions
        self.memories = {}
        
        # Document metadata
        self.document_type = None
        self.document_path = None
    
    def load_document(self, file_path, chunk_size=1000, chunk_overlap=100):
        """
        Load and process a document file.
        
        Args:
            file_path: Path to the document file.
            chunk_size: Size of text chunks to split the document into.
            chunk_overlap: Amount of overlap between chunks.
        
        Returns:
            self: For method chaining.
        """
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document file not found: {file_path}")
        
        # Get the document loader based on file extension
        loader = DocumentLoaderFactory.get_loader(file_path)
        
        # Load document
        documents = loader.load(file_path)
        
        # Store document metadata
        self.document_path = file_path
        _, ext = os.path.splitext(file_path.lower())
        self.document_type = ext
        
        # Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        chunks = text_splitter.split_documents(documents)
        
        # Create vector store
        self.vector_store = FAISS.from_documents(chunks, self.embeddings)
        
        return self
    
    def get_or_create_memory(self, session_id):
        """
        Get an existing memory for a session or create a new one.
        """
        if session_id not in self.memories:
            self.memories[session_id] = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="answer"
            )

        return self.memories[session_id]
    
    def create_qa_chain(self, session_id=None):
        """
        Create a conversational question-answering chain with memory.
        
        Returns:
            ConversationalRetrievalChain: The question-answering chain.
        """
        if not self.vector_store:
            raise ValueError("No document has been loaded. Call load_document() first.")
        
        # Get or create memory for this session
        session_id = session_id or "default"
        memory = self.get_or_create_memory(session_id)
        
        # Create custom prompt
        condense_prompt_template = """
        Given the following conversation and a follow up question, rephrase the follow up question to be a standalone question that captures all relevant context from the conversation.
        
        Chat History:
        {chat_history}
        
        Follow Up Input: {question}
        Standalone question:
        """
        
        condense_prompt = PromptTemplate.from_template(condense_prompt_template)
        
        qa_prompt_template = """
        You are an assistant that answers questions based on the provided document.
        Use only the following context to answer the question. If you don't know the answer or it's not in the context, say "I don't have enough information to answer this question."
        
        Context: {context}
        
        Question: {question}
        """
        
        qa_prompt = PromptTemplate.from_template(qa_prompt_template)
        
        # Create retriever
        retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 4}  # Retrieve top 4 most relevant chunks
        )
        
        # Create conversational QA chain with memory
        qa_chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=retriever,
            memory=memory,
            combine_docs_chain_kwargs={"prompt": qa_prompt},
            condense_question_prompt=condense_prompt,
            return_source_documents=True
        )
        
        return qa_chain
    
    def query(self, question, session_id=None):
        """
        Query the document with a question, maintaining conversation history.
        
        Args:
            question: The question to ask about the document.
            session_id: Optional identifier for the conversation session.
        
        Returns:
            dict: The answer and source documents.
        """
        session_id = session_id or "default"
        qa_chain = self.create_qa_chain(session_id)
        result = qa_chain({"question": question})
        
        # Format the result
        answer = result["answer"]
        sources = [doc.page_content[:150] + "..." for doc in result["source_documents"]]
        
        return {
            "answer": answer,
            "sources": sources
        }
    
    def get_chat_history(self, session_id):
        """
        Get the current chat history for a specific session.
        """
        if not session_id or session_id not in self.memories:
            return []
        return self.memories[session_id].chat_memory.messages
    
    def clear_memory(self, session_id=None):
        """
        Clear the conversation memory for a specific session or all sessions.
        """
        if session_id:
            if session_id in self.memories:
                self.memories[session_id].clear()
                return {"status": "success", "message": f"Conversation history for session {session_id} cleared"}
            return {"status": "warning", "message": f"No history found for session {session_id}"}
        else:
            self.memories = {}
            return {"status": "success", "message": "All conversation histories cleared"}

# Factory to create different engines based on document type
class QueryEngineFactory:
    """Factory for creating query engines"""
    
    @staticmethod
    def create_engine(file_path, openai_api_key=None, model_name="gpt-3.5-turbo"):
        """Create appropriate query engine for the document type"""
        # For now, we're using the same engine for all document types
        # This can be expanded to create specialized engines if needed
        engine = DocumentQueryEngine(openai_api_key, model_name)
        return engine