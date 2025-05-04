import os
import uuid
import asyncio
from typing import List, Dict, Any
import chromadb
from langchain.document_loaders import TextLoader, PyPDFLoader, Docx2txtLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma

class DocumentProcessor:
    def __init__(self):
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        self.embedding_model = OpenAIEmbeddings(openai_api_key=openai_api_key)
        
        # Initialize ChromaDB client
        os.makedirs("./chroma_db", exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        
        # Supported file extensions
        self.supported_extensions = {
            ".txt": TextLoader,
            ".pdf": PyPDFLoader,
            ".doc": Docx2txtLoader,
            ".docx": Docx2txtLoader
        }
        
    async def process_document(self, file_path: str) -> str:
        """
        Process a document and create embeddings.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Asset ID for the processed document
        """
        
        print(f"Attempting to process file: {file_path}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"File exists: {os.path.exists(file_path)}")
        
        # Make file path absolute if it's not already
        if not os.path.isabs(file_path):
            # Try different relative paths
            possible_paths = [
                file_path,
                os.path.join(".", file_path),
                os.path.join("..", file_path),
                os.path.join(os.getcwd(), file_path)
            ]
            
            # Find the first path that exists
            for path in possible_paths:
                if os.path.exists(path):
                    file_path = path
                    print(f"Found file at: {file_path}")
                    break
        
        # Validate file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}. Tried looking in: {possible_paths}")
        
        # Get file extension
        _, ext = os.path.splitext(file_path)
        if ext.lower() not in self.supported_extensions:
            raise ValueError(f"Unsupported file type: {ext}. Supported types: {list(self.supported_extensions.keys())}")
        
        # Generate a unique asset ID
        asset_id = str(uuid.uuid4())
        
        # Process the document asynchronously
        await self._process_document_async(file_path, ext.lower(), asset_id)
        
        return asset_id
    
    async def _process_document_async(self, file_path: str, ext: str, asset_id: str):
        """
        Process document asynchronously to create and store embeddings.
        
        Args:
            file_path: Path to the document
            ext: File extension
            asset_id: Unique asset ID
        """
        # Use appropriate loader based on file extension
        loader_class = self.supported_extensions[ext]
        
        # Run document loading in a thread pool
        def load_and_process():
            try:
                # Load document
                loader = loader_class(file_path)
                documents = loader.load()
                
                # Split text into chunks
                text_splitter = CharacterTextSplitter(
                    separator="\n",
                    chunk_size=1000,
                    chunk_overlap=200,
                    length_function=len
                )
                text_chunks = text_splitter.split_documents(documents)
                
                # Create vector store with OpenAI embeddings
                persist_dir = f"./chroma_db/{asset_id}"
                os.makedirs(persist_dir, exist_ok=True)
                
                vectorstore = Chroma.from_documents(
                    documents=text_chunks,
                    embedding=self.embedding_model,
                    persist_directory=persist_dir
                )
                
                # Persist the vector store
                vectorstore.persist()
                
                return len(text_chunks)
            except Exception as e:
                print(f"Error processing document: {str(e)}")
                raise
        
        # Run in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        chunk_count = await loop.run_in_executor(None, load_and_process)
        
        print(f"Processed document {file_path} with asset ID {asset_id}. Created {chunk_count} chunks.")

