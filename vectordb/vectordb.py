"""
Vector database management for the Financial Analyst Agent.

This module handles:
- Vector store operations (FAISS)
- Embedding generation and indexing
- Similarity search
- Vector store persistence
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document


class VectorStore:
    """Wrapper for FAISS vector store operations."""
    
    def __init__(self, embedding_model: str = "text-embedding-3-small"):
        """
        Initialize vector store with embeddings.
        
        Args:
            embedding_model: OpenAI embedding model name
        """
        self.embedding_model = OpenAIEmbeddings(model=embedding_model)
        self.store = None
        self.index_path = None
    
    def add_documents(self, documents: List[Document]) -> None:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of LangChain Document objects
        """
        if self.store is None:
            self.store = FAISS.from_documents(documents, self.embedding_model)
        else:
            self.store.add_documents(documents)
        
        print(f"✅ Added {len(documents)} documents. Total vectors: {self.store.index.ntotal}")
    
    def search(self, query: str, k: int = 4) -> List[Document]:
        """
        Search for similar documents.
        
        Args:
            query: Search query string
            k: Number of top results to return
            
        Returns:
            List of similar Document objects
        """
        if self.store is None:
            raise ValueError("Vector store not initialized. Add documents first.")
        
        return self.store.similarity_search(query, k=k)
    
    def search_with_scores(self, query: str, k: int = 4) -> List[tuple]:
        """
        Search with similarity scores.
        
        Args:
            query: Search query string
            k: Number of top results to return
            
        Returns:
            List of (Document, score) tuples
        """
        if self.store is None:
            raise ValueError("Vector store not initialized. Add documents first.")
        
        return self.store.similarity_search_with_score(query, k=k)
    
    def get_retriever(self, k: int = 4):
        """
        Get a LangChain retriever.
        
        Args:
            k: Number of documents to retrieve
            
        Returns:
            FAISS retriever
        """
        if self.store is None:
            raise ValueError("Vector store not initialized. Add documents first.")
        
        return self.store.as_retriever(search_kwargs={"k": k})
    
    def save(self, path: str) -> None:
        """
        Save vector store to disk.
        
        Args:
            path: Directory path to save index
        """
        if self.store is None:
            raise ValueError("No vector store to save.")
        
        os.makedirs(path, exist_ok=True)
        self.store.save_local(path)
        self.index_path = path
        print(f"✅ Vector store saved to {path}")
    
    @classmethod
    def load(cls, path: str, embedding_model: str = "text-embedding-3-small") -> "VectorStore":
        """
        Load vector store from disk.
        
        Args:
            path: Directory path containing saved index
            embedding_model: OpenAI embedding model name
            
        Returns:
            Initialized VectorStore instance
        """
        vs = cls(embedding_model=embedding_model)
        embeddings = OpenAIEmbeddings(model=embedding_model)
        vs.store = FAISS.load_local(path, embeddings)
        vs.index_path = path
        print(f"✅ Vector store loaded from {path}. Total vectors: {vs.store.index.ntotal}")
        return vs


def create_vectorstore_from_documents(documents: List[Document], 
                                     embedding_model: str = "text-embedding-3-small") -> VectorStore:
    """
    Create a vectorstore from a list of documents.
    
    Args:
        documents: List of LangChain Document objects
        embedding_model: OpenAI embedding model name
        
    Returns:
        Initialized VectorStore
    """
    vs = VectorStore(embedding_model=embedding_model)
    vs.add_documents(documents)
    return vs
