import os
from typing import List, Dict, Any
from langchain.docstore.document import Document as LangchainDocument
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.document_loaders import UnstructuredWordDocumentLoader

class BaseDocumentLoader:
    """Base class for document loaders"""
    
    def load(self, file_path: str) -> List[LangchainDocument]:
        """Load document from file path"""
        raise NotImplementedError
        
    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """Get list of supported file extensions"""
        raise NotImplementedError


class PDFDocumentLoader(BaseDocumentLoader):
    """Loader for PDF documents"""
    
    def load(self, file_path: str) -> List[LangchainDocument]:
        """Load PDF document using PyPDFLoader"""
        loader = PyPDFLoader(file_path)
        return loader.load()
    
    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        return ['.pdf']


class TextDocumentLoader(BaseDocumentLoader):
    """Loader for plain text documents"""
    
    def load(self, file_path: str) -> List[LangchainDocument]:
        """Load text document using TextLoader"""
        loader = TextLoader(file_path)
        return loader.load()
    
    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        return ['.txt']


class DocxDocumentLoader(BaseDocumentLoader):
    """Loader for Word documents"""
    
    def load(self, file_path: str) -> List[LangchainDocument]:
        """Load Word document using UnstructuredWordDocumentLoader"""
        loader = UnstructuredWordDocumentLoader(file_path)
        return loader.load()
    
    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        return ['.docx', '.doc']


# Factory class to get appropriate loader
class DocumentLoaderFactory:
    """Factory for creating document loaders based on file extension"""
    
    _loaders = {
        '.pdf': PDFDocumentLoader,
        '.txt': TextDocumentLoader,
        '.docx': DocxDocumentLoader,
        '.doc': DocxDocumentLoader
    }
    
    @classmethod
    def get_loader(cls, file_path: str) -> BaseDocumentLoader:
        """Get appropriate loader for file type"""
        _, ext = os.path.splitext(file_path.lower())
        
        if ext not in cls._loaders:
            supported = ', '.join(cls.get_supported_extensions())
            raise ValueError(f"Unsupported file type: {ext}. Supported types: {supported}")
        
        return cls._loaders[ext]()
    
    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """Get list of all supported file extensions"""
        return list(cls._loaders.keys())