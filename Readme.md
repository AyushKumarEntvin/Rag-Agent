## RAG Chatbot with LangChain
This repository contains a Retrieval-Augmented Generation (RAG) chatbot application that allows users to upload documents, process them, and chat with an AI assistant that can answer questions based on the document content.

## Features

Document processing for various file formats (PDF, TXT, DOC, DOCX)
Asynchronous backend with FastAPI
Streaming responses for a better user experience
Persistent chat history
Interactive Streamlit frontend
LangChain's ConversationalRetrievalChain for intelligent document retrieval and response generation

## Architecture
The application consists of two main components:

Backend: A FastAPI server that handles document processing, chat management, and AI interactions
Frontend: A Streamlit application that provides a user-friendly interface

## Backend Components

main.py: FastAPI application entry point with API endpoints
document_processor.py: Handles document loading, chunking, and embedding
chat_service.py: Manages chat sessions and interactions with the LangChain retrieval chain
models.py: Pydantic models for API requests and responses

## Frontend Components

app.py: Streamlit application for user interactions

## Prerequisites

Python 3.8+
OpenAI API key

## Installation

### Clone the repository:

 git clone https://github.com/AyushKumarEntvin/Rag-Agent.git
cd rag-chatbot

### Create a virtual environment:

 python -m venv venv

source venv/bin/activate  

#### On Windows: venv\Scripts\activate

### Install dependencies:

 pip install -r requirements.txt

### Create a .env file in the root directory with your OpenAI API key:

OPENAI_API_KEY=your_openai_api_key_here

API_BASE_URL = "http://localhost:8000/api"  # Change this to your backend URL

### Running the Application
Start the Backend
 uvicorn main:app --reload --host 0.0.0.0 --port 8000

Start the Frontend in new terminal
 cd frontend
streamlit run app.py
The frontend will be accessible at http://localhost:8501

backend docs:
{Backend Base URL}/docs

## Usage Guide
1. Upload and Process a Document

Navigate to the Streamlit interface at http://localhost:8501
In the left sidebar, use the file uploader to select a document (PDF, TXT, DOC, or DOCX)
Click "Process Document" to extract and embed the document content
Once processing is complete, you'll receive an Asset ID

2. Start a Chat

In the "Start a Chat" section, enter the Asset ID (it should be pre-filled if you just processed a document)
Click "Start Chat" to initialize a new chat session
The chat interface will appear in the main panel

3. Chat with the AI Assistant

Type your question in the text input field at the bottom of the chat interface
Click "Send" to submit your question
The AI assistant will process your question, search the document for relevant information, and provide a response
Continue the conversation by asking follow-up questions

How It Works

Document Processing:

Documents are uploaded and saved to the uploads directory
The document is loaded and split into smaller chunks using LangChain's document loaders and text splitters
Each chunk is embedded using OpenAI embeddings
The embeddings are stored in a ChromaDB vector database


Chat Initialization:

A unique chat thread ID is generated
A ConversationalRetrievalChain is created with access to the document's vector store
A conversation memory is initialized to maintain context


Question Answering:

User questions are sent to the backend
The ConversationalRetrievalChain:

Retrieves relevant document chunks based on the question
Generates a response using the retrieved information and conversation history
Maintains context for follow-up questions


The response is streamed back to the frontend


Chat History:

All messages are stored in memory and persisted to disk
Chat history can be retrieved when rejoining a chat session



API Endpoints

POST /api/documents/process: Process a document and create embeddings

POST /api/chat/start: Start a new chat thread with a specific asset ID

POST /api/chat/message: Send a message to a chat thread and get a streaming response

GET /api/chat/history: Get the chat history for a specific chat thread

GET /api/chat/status: Check if a chat thread is currently processing a message


Requirements
See requirements.txt for a complete list of dependencies. Key libraries include:

fastapi
uvicorn
langchain
langchain-openai
chromadb
streamlit
python-dotenv

## Asynchronous Processing
The application leverages FastAPI's asynchronous capabilities:

Document processing runs in background threads to avoid blocking the main thread
Chat responses are streamed asynchronously for a better user experience
Multiple chat sessions can be handled concurrently
Thread locks ensure that concurrent requests to the same chat thread are handled properly
