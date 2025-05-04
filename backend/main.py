from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import asyncio
import os
import logging
import time
from dotenv import load_dotenv

from models import (
    DocumentProcessRequest,
    DocumentProcessResponse,
    ChatStartRequest,
    ChatStartResponse,
    ChatMessageRequest,
    ChatHistoryResponse,
    ChatMessage
)
from document_processor import DocumentProcessor
from chat_service import ChatService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("rag_chatbot")

# Load environment variables
logger.info("Loading environment variables")
load_dotenv()

if not os.environ.get("OPENAI_API_KEY"):
    logger.error("OPENAI_API_KEY environment variable is not set")
    raise ValueError("OPENAI_API_KEY environment variable is not set. Please set it in your .env file or environment.")

logger.info("Initializing FastAPI application")
app = FastAPI(title="RAG Chatbot API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
logger.info("Initializing document processor and chat service")
document_processor = DocumentProcessor()
chat_service = ChatService()

@app.post("/api/documents/process", response_model=DocumentProcessResponse)
async def process_document(request: DocumentProcessRequest, background_tasks: BackgroundTasks):
    """
    Process a document and create embeddings.
    
    Args:
        request: Document processing request with file path
        
    Returns:
        Document processing response with asset ID
    """
    request_id = f"req_{int(time.time())}"
    logger.info(f"[{request_id}] Processing document request for file: {request.file_path}")
    
    try:
        logger.info(f"[{request_id}] Calling document processor")
        start_time = time.time()
        asset_id = await document_processor.process_document(request.file_path)
        processing_time = time.time() - start_time
        
        logger.info(f"[{request_id}] Document processed successfully. Asset ID: {asset_id}. Processing time: {processing_time:.2f}s")
        return DocumentProcessResponse(asset_id=asset_id)
    except Exception as e:
        logger.error(f"[{request_id}] Error processing document: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.post("/api/chat/start", response_model=ChatStartResponse)
async def start_chat(request: ChatStartRequest):
    """
    Start a new chat thread with a specific asset ID.
    
    Args:
        request: Chat start request with asset ID
        
    Returns:
        Chat start response with chat thread ID
    """
    request_id = f"req_{int(time.time())}"
    logger.info(f"[{request_id}] Starting chat with asset ID: {request.asset_id}")
    
    try:
        logger.info(f"[{request_id}] Creating chat thread")
        start_time = time.time()
        chat_thread_id = await chat_service.create_chat(request.asset_id)
        creation_time = time.time() - start_time
        
        logger.info(f"[{request_id}] Chat thread created successfully. Thread ID: {chat_thread_id}. Creation time: {creation_time:.2f}s")
        return ChatStartResponse(chat_thread_id=chat_thread_id)
    except Exception as e:
        logger.error(f"[{request_id}] Error starting chat: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error starting chat: {str(e)}")

@app.post("/api/chat/message")
async def send_message(request: ChatMessageRequest):
    """
    Send a message to a chat thread and get a streaming response.
    
    Args:
        request: Chat message request with thread ID and user message
        
    Returns:
        Streaming response with agent's reply
    """
    request_id = f"req_{int(time.time())}"
    logger.info(f"[{request_id}] Sending message to chat thread: {request.chat_thread_id}")
    logger.info(f"[{request_id}] Message content: {request.message}")
    
    try:
        async def generate_response():
            logger.info(f"[{request_id}] Starting response stream")
            token_count = 0
            start_time = time.time()
            
            async for token in chat_service.send_message(request.chat_thread_id, request.message):
                token_count += 1
                yield f"data: {token}\n\n"
                await asyncio.sleep(0.01)  # Small delay for streaming effect
            
            processing_time = time.time() - start_time
            logger.info(f"[{request_id}] Response stream completed. Tokens: {token_count}. Processing time: {processing_time:.2f}s")
                
        logger.info(f"[{request_id}] Returning streaming response")
        return StreamingResponse(generate_response(), media_type="text/event-stream")
    except Exception as e:
        logger.error(f"[{request_id}] Error sending message: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")

@app.get("/api/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history(chat_thread_id: str):
    """
    Get the chat history for a specific chat thread.
    
    Args:
        chat_thread_id: ID of the chat thread
        
    Returns:
        Chat history response with messages
    """
    request_id = f"req_{int(time.time())}"
    logger.info(f"[{request_id}] Getting chat history for thread: {chat_thread_id}")
    
    try:
        start_time = time.time()
        history = await chat_service.get_chat_history(chat_thread_id)
        retrieval_time = time.time() - start_time
        
        logger.info(f"[{request_id}] Chat history retrieved successfully. Messages: {len(history)}. Retrieval time: {retrieval_time:.2f}s")
        return ChatHistoryResponse(messages=history)
    except Exception as e:
        logger.error(f"[{request_id}] Error retrieving chat history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving chat history: {str(e)}")
    
@app.get("/api/chat/status")
async def get_chat_status(chat_thread_id: str):
    """
    Check if a chat thread is currently processing a message.
    
    Args:
        chat_thread_id: ID of the chat thread
        
    Returns:
        Status of the chat thread
    """
    request_id = f"req_{int(time.time())}"
    logger.info(f"[{request_id}] Checking status for chat thread: {chat_thread_id}")
    
    try:
        is_processing = await chat_service.is_processing(chat_thread_id)
        logger.info(f"[{request_id}] Chat status retrieved. Is processing: {is_processing}")
        return {"is_processing": is_processing}
    except Exception as e:
        logger.error(f"[{request_id}] Error checking chat status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error checking chat status: {str(e)}")

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    logger.info("Application startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down")