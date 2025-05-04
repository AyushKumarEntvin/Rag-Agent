import uuid
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, AsyncGenerator, Any
import json
import os

from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings

from models import ChatMessage

class ChatService:
    def __init__(self):
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        # Initialize embedding model with OpenAI
        self.embedding_model = OpenAIEmbeddings(openai_api_key=openai_api_key)
        
        self.llm = ChatOpenAI(temperature=0.7, openai_api_key=openai_api_key)
        
        # Store active chats
        self.active_chats = {}
        
        # Create locks for each chat thread
        self.chat_locks = {}
        
        # Create directory for chat history
        os.makedirs("./chat_history", exist_ok=True)
    
    async def create_chat(self, asset_id: str) -> str:
        """
        Create a new chat thread for a specific asset.
        
        Args:
            asset_id: Asset ID to associate with the chat
            
        Returns:
            Chat thread ID
        """
        # Generate a unique chat thread ID
        chat_thread_id = str(uuid.uuid4())
        
        # Create a lock for this chat thread
        self.chat_locks[chat_thread_id] = threading.Lock()
        
        # Load the vector store for the asset
        def load_vectorstore():
            vectorstore = Chroma(
                persist_directory=f"./chroma_db/{asset_id}",
                embedding_function=self.embedding_model
            )
            
            # Create conversation memory
            memory = ConversationBufferMemory(
                memory_key='chat_history',
                return_messages=True
            )
            
            # Create conversation chain with OpenAI
            conversation_chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=vectorstore.as_retriever(),
                memory=memory
            )
            
            return conversation_chain
        
        # Run in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        conversation_chain = await loop.run_in_executor(None, load_vectorstore)
        
        # Store the conversation chain and initialize chat history
        self.active_chats[chat_thread_id] = {
            "asset_id": asset_id,
            "conversation_chain": conversation_chain,
            "history": [],
            "processing": False  # Flag to track if a message is being processed
        }
        
        return chat_thread_id
    
    async def send_message(self, chat_thread_id: str, message: str) -> AsyncGenerator[str, None]:
        """
        Send a message to a chat thread and get a streaming response.
        
        Args:
            chat_thread_id: Chat thread ID
            message: User message
            
        Yields:
            Tokens of the assistant's response
        """
        if chat_thread_id not in self.active_chats:
            raise ValueError(f"Chat thread {chat_thread_id} not found")
        
        # Get the lock for this chat thread
        chat_lock = self.chat_locks.get(chat_thread_id)
        if not chat_lock:
            chat_lock = threading.Lock()
            self.chat_locks[chat_thread_id] = chat_lock
        
        if not chat_lock.acquire(blocking=False):
            # If the lock is already held, it means another request is being processed
            yield "I'm still processing your previous message. Please wait a moment."
            return
        
        try:
            # Set the processing flag
            self.active_chats[chat_thread_id]["processing"] = True
            
            # Add user message to history
            timestamp = datetime.now().isoformat()
            user_message = ChatMessage(role="user", content=message, timestamp=timestamp)
            self.active_chats[chat_thread_id]["history"].append(user_message)
            
            # Get conversation chain
            conversation_chain = self.active_chats[chat_thread_id]["conversation_chain"]
            
            # Process the message in a thread pool
            def process_message():
                return conversation_chain.invoke({"question": message})
            
            # Run in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, process_message)
            
            assistant_response = response['answer']
            
            # Add assistant message to history
            assistant_message = ChatMessage(
                role="assistant", 
                content=assistant_response,
                timestamp=datetime.now().isoformat()
            )
            self.active_chats[chat_thread_id]["history"].append(assistant_message)
            
            # Save chat history
            await self._save_chat_history(chat_thread_id)
            
            print(f"Assistant response: {assistant_response}")
            
            # Stream the response word by word
            words = assistant_response.split()
            for i, word in enumerate(words):
                yield word + " "
                if i < len(words) - 1 and word.endswith(('.', '!', '?')):
                    yield "\n"
                await asyncio.sleep(0.05)  # Simulate streaming
        
        finally:
            # Clear the processing flag and release the lock
            self.active_chats[chat_thread_id]["processing"] = False
            chat_lock.release()
    
    async def get_chat_history(self, chat_thread_id: str) -> List[ChatMessage]:
        """
        Get the chat history for a specific chat thread.
        
        Args:
            chat_thread_id: Chat thread ID
            
        Returns:
            List of chat messages
        """
        if chat_thread_id not in self.active_chats:
            # Try to load from disk
            history_path = f"./chat_history/{chat_thread_id}.json"
            if os.path.exists(history_path):
                with open(history_path, 'r') as f:
                    history_data = json.load(f)
                    return [ChatMessage(**msg) for msg in history_data]
            raise ValueError(f"Chat thread {chat_thread_id} not found")
        
        return self.active_chats[chat_thread_id]["history"]
    
    async def is_processing(self, chat_thread_id: str) -> bool:
        """
        Check if a chat thread is currently processing a message.
        
        Args:
            chat_thread_id: Chat thread ID
            
        Returns:
            True if processing, False otherwise
        """
        if chat_thread_id not in self.active_chats:
            return False
        
        return self.active_chats[chat_thread_id].get("processing", False)
    
    async def _save_chat_history(self, chat_thread_id: str):
        """
        Save chat history to disk.
        
        Args:
            chat_thread_id: Chat thread ID
        """
        history = self.active_chats[chat_thread_id]["history"]
        history_path = f"./chat_history/{chat_thread_id}.json"
        
        with open(history_path, 'w') as f:
            json.dump([msg.dict() for msg in history], f)
