from pydantic import BaseModel
from typing import List, Optional

class DocumentProcessRequest(BaseModel):
    file_path: str

class DocumentProcessResponse(BaseModel):
    asset_id: str

class ChatStartRequest(BaseModel):
    asset_id: str

class ChatStartResponse(BaseModel):
    chat_thread_id: str

class ChatMessageRequest(BaseModel):
    chat_thread_id: str
    message: str

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None

class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessage]
