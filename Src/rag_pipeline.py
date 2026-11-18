"""
RAG (Retrieval-Augmented Generation) pipeline for the Financial Analyst Agent.

This module orchestrates:
- PDF document loading and parsing
- Text chunking with overlap
- Embedding generation
- FAISS vector store creation and retrieval
- Semantic similarity search over policy documents
"""

import os
from pathlib import Path
from typing import Optional, List

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document


class RAGPipeline:
    """Orchestrator for RAG pipeline - loads, chunks, embeds, and stores policy documents."""
    
    def __init__(self, data: str = "data/policy_documents", embedding_model: str = "text-embedding-3-small"):
        """
        Initialize RAG pipeline.
        
        Args:
            data: Directory containing policy PDF documents
            embedding_model: OpenAI embedding model name
        """
        self.data = Path(data).resolve()
        self.embedding_model = OpenAIEmbeddings(model=embedding_model)
        self.vectorstore = None
        self.retriever = None
        self.chunks = None
        
        if not self.data.exists():
            raise FileNotFoundError(f"Policy directory not found: {self.data}")
    
    def load_documents(self) -> List[Document]:
        """
        Load all PDF documents from the policy directory.
        
        Returns:
            List of LangChain Document objects (one per page)
        """
        # CONCEPT: RAG step 1 - Load
        # PyPDFLoader returns one Document per PDF page. Each Document keeps
        # metadata (source file path and page number) that is later used for citations.
        all_pages = []
        pdf_files = sorted([f for f in os.listdir(self.data) if f.endswith(".pdf")])
        
        print(f"📄 Loading {len(pdf_files)} policy PDFs from {self.data}/...\n")
        
        for pdf_file in pdf_files:
            pdf_path = os.path.join(self.data, pdf_file)
            loader = PyPDFLoader(pdf_path)
            pages = loader.load()
            all_pages.extend(pages)
            print(f"   ✓ {pdf_file}: {len(pages)} pages")
        
        print(f"\n✅ Total pages extracted: {len(all_pages)}")
        return all_pages
    
    def chunk_documents(self, documents: List[Document], chunk_size: int = 1000, 
                       chunk_overlap: int = 300) -> List[Document]:
        """
        Split documents into chunks with overlap.
        
        Args:
            documents: List of documents to chunk
            chunk_size: Size of each chunk in characters
            chunk_overlap: Number of overlapping characters between chunks
            
        Returns:
            List of chunked documents
        """
        # CONCEPT: RAG step 2 - Chunk
        # Whole pages are too long and too mixed in topic to search well, so they
        # are cut into ~1000-character pieces. The 300-character overlap means a
        # sentence cut at a boundary still appears whole in one of the two chunks.
        # The splitter tries to cut at paragraph breaks first, then lines,
        # then sentences, then words.
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        chunks = text_splitter.split_documents(documents)
        print(f"✅ Split into {len(chunks)} chunks (size={chunk_size}, overlap={chunk_overlap})")
        
        self.chunks = chunks
        return chunks
    
    def build_vectorstore(self, documents: Optional[List[Document]] = None) -> FAISS:
        """
        Build FAISS vector store from chunked documents.
        
        Args:
            documents: List of documents to embed. If None, uses self.chunks
            
        Returns:
            FAISS vectorstore instance
        """
        if documents is None:
            if self.chunks is None:
                raise ValueError("No documents provided and no chunks cached. Call chunk_documents first.")
            documents = self.chunks
        
        # CONCEPT: RAG step 3 - Embed and index
        # An embedding model turns each chunk into a list of 1,536 numbers (a
        # vector). Texts with similar meaning get vectors that are close together.
        # FAISS stores the vectors in memory so the nearest ones can be found fast.
        # Note: the index is rebuilt (and the embedding API is paid for) every time
        # the server starts; it is not saved to disk.
        print(f"\n⏳ Embedding {len(documents)} chunks with {self.embedding_model.model}...")
        self.vectorstore = FAISS.from_documents(documents, self.embedding_model)
        
        print(f"\n✅ FAISS vector store built:")
        print(f"   Vectors: {self.vectorstore.index.ntotal}")
        print(f"   Embedding dimensions: 1,536")
        
        return self.vectorstore
    
    def create_retriever(self, k: int = 4):
        """
        Create a retriever that returns top-k similar documents.
        
        Args:
            k: Number of top results to return
            
        Returns:
            FAISS retriever chain
        """
        if self.vectorstore is None:
            raise ValueError("Vectorstore not built. Call build_vectorstore first.")
        
        # CONCEPT: RAG step 4 - Retrieve
        # At question time the query is embedded too, and the k chunks whose
        # vectors are closest to it are returned (similarity search).
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": k})
        print(f"   Retriever: top-{k} similarity search")
        
        return self.retriever
    
    def setup_complete_pipeline(self) -> tuple:
        """
        Complete RAG pipeline setup in one call.
        
        Returns:
            Tuple of (vectorstore, retriever)
        """
        documents = self.load_documents()
        self.chunk_documents(documents)
        self.build_vectorstore()
        self.create_retriever()
        
        return self.vectorstore, self.retriever
    
    def search(self, query: str, k: int = 4) -> List[Document]:
        """
        Search for similar documents.
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of similar documents
        """
        if self.retriever is None:
            raise ValueError("Retriever not initialized. Call create_retriever first.")
        
        return self.retriever.invoke(query)


def initialize_rag_pipeline(data: str = "data/policy_documents") -> tuple:
    """
    Initialize and setup complete RAG pipeline.
    
    Args:
        data: Directory containing policy PDFs
        
    Returns:
        Tuple of (vectorstore, retriever, rag_pipeline)
    """
    rag = RAGPipeline(data=data)
    vectorstore, retriever = rag.setup_complete_pipeline()
    return vectorstore, retriever, rag
