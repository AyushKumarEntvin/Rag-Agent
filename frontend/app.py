import streamlit as st
import requests
import json
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# API endpoints
API_BASE_URL = os.getenv("API_BASE_URL")  # Change this to your backend URL in .env
PROCESS_DOCUMENT_URL = f"{API_BASE_URL}/documents/process"
START_CHAT_URL = f"{API_BASE_URL}/chat/start"
SEND_MESSAGE_URL = f"{API_BASE_URL}/chat/message"
GET_HISTORY_URL = f"{API_BASE_URL}/chat/history"
GET_STATUS_URL = f"{API_BASE_URL}/chat/status"

# Set page config
st.set_page_config(page_title="RAG Chatbot", layout="wide")

# Initialize session state variables
if "chat_thread_id" not in st.session_state:
    st.session_state.chat_thread_id = None
if "asset_id" not in st.session_state:
    st.session_state.asset_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "waiting_for_response" not in st.session_state:
    st.session_state.waiting_for_response = False
if "last_message_time" not in st.session_state:
    st.session_state.last_message_time = None

st.markdown("""
<style>
.user-message {
    background-color: #4CAF50;
    color: white;
    padding: 10px 15px;
    border-radius: 15px;
    margin: 5px 0;
    display: inline-block;
    max-width: 80%;
    font-family: Arial, sans-serif;
    font-size: 16px;
}
.assistant-message {
    background-color: #2196F3;
    color: white;
    padding: 10px 15px;
    border-radius: 15px;
    margin: 5px 0;
    display: inline-block;
    max-width: 80%;
    font-family: Arial, sans-serif;
    font-size: 16px;
}
</style>
""", unsafe_allow_html=True)

# Create a two-column layout
col1, col2 = st.columns([1, 3])

# Sidebar for document processing and chat initialization
with col1:
    st.header("Document Processing")
    
    # File upload section
    uploaded_file = st.file_uploader("Upload a document", type=["txt", "pdf", "doc", "docx"])
    
    if uploaded_file is not None:
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(os.getcwd(), "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save the uploaded file
        file_path = os.path.join(upload_dir, uploaded_file.name.replace(" ", "_"))
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.success(f"File uploaded: {uploaded_file.name}")
        
        if st.button("Process Document"):
            with st.spinner("Processing document..."):
                try:
                    # Call the document processing API
                    response = requests.post(
                        PROCESS_DOCUMENT_URL,
                        json={"file_path": file_path}
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.asset_id = result["asset_id"]
                        st.success(f"Document processed! Asset ID: {st.session_state.asset_id}")
                    else:
                        st.error(f"Error: {response.text}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    st.header("Start a Chat")
    
    # Input for asset ID
    asset_id_input = st.text_input("Enter Asset ID", value=st.session_state.asset_id or "")
    
    if st.button("Start Chat"):
        if asset_id_input:
            with st.spinner("Starting chat..."):
                try:
                    # Call the start chat API
                    response = requests.post(
                        START_CHAT_URL,
                        json={"asset_id": asset_id_input}
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.chat_thread_id = result["chat_thread_id"]
                        st.session_state.asset_id = asset_id_input
                        st.session_state.messages = []
                        st.success(f"Chat started!")
                        
                        # Load chat history
                        try:
                            history_response = requests.get(
                                f"{GET_HISTORY_URL}?chat_thread_id={st.session_state.chat_thread_id}"
                            )
                            if history_response.status_code == 200:
                                st.session_state.messages = history_response.json()["messages"]
                        except:
                            pass
                    else:
                        st.error(f"Error: {response.text}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        else:
            st.warning("Please enter an Asset ID")

# Main chat interface
with col2:
    st.header("Chat")
    
    # Display chat status
    if st.session_state.chat_thread_id:
        st.success(f"Active chat with Asset ID: {st.session_state.asset_id}")
    
        # Display messages
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f'<div style="text-align: right;"><div class="user-message">{message["content"]}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="text-align: left;"><div class="assistant-message">{message["content"]}</div></div>', unsafe_allow_html=True)
        
        if st.session_state.waiting_for_response:
            st.markdown("⏳ Waiting for response...", unsafe_allow_html=True)
        
        # Message input
        user_input = st.text_input("Type your message", key="message_input")
        send_button = st.button("Send")
        
        if send_button and user_input and not st.session_state.waiting_for_response:
            # Add user message to the chat
            user_message = {
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now().isoformat()
            }
            st.session_state.messages.append(user_message)
            
            # Set waiting flag
            st.session_state.waiting_for_response = True
            st.session_state.last_message_time = datetime.now().isoformat()
            
            # Make a non-blocking request to the API
            try:
                response = requests.post(
                    SEND_MESSAGE_URL,
                    json={
                        "chat_thread_id": st.session_state.chat_thread_id,
                        "message": user_input
                    },
                    stream=True,
                    headers={"Accept": "text/event-stream"}
                )
                
                # Process the response
                if response.status_code == 200:
                    # Extract the response text
                    response_text = ""
                    for line in response.iter_lines():
                        if line:
                            decoded_line = line.decode('utf-8')
                            if decoded_line.startswith('data: '):
                                response_text += decoded_line[6:] + " "
                    
                    # Add assistant message to the chat
                    assistant_message = {
                        "role": "assistant",
                        "content": response_text.strip(),
                        "timestamp": datetime.now().isoformat()
                    }
                    st.session_state.messages.append(assistant_message)
                else:
                    st.error(f"Error: {response.text}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
            
            # Clear the waiting flag
            st.session_state.waiting_for_response = False
            
            # Rerun to update UI
            st.experimental_rerun()
    else:
        st.info("No active chat. Please start a chat from the sidebar.")

# Check if we need to refresh chat history
if st.session_state.chat_thread_id and st.session_state.waiting_for_response:
    try:
        status_response = requests.get(
            f"{GET_STATUS_URL}?chat_thread_id={st.session_state.chat_thread_id}"
        )
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            
            # If processing is done, refresh the chat history
            if not status_data.get("is_processing", False):
                history_response = requests.get(
                    f"{GET_HISTORY_URL}?chat_thread_id={st.session_state.chat_thread_id}"
                )
                
                if history_response.status_code == 200:
                    st.session_state.messages = history_response.json()["messages"]
                    st.session_state.waiting_for_response = False
                    
                    # Rerun to update UI
                    st.experimental_rerun()
    except:
        pass
    
    # Rerun every few seconds to check for updates
    time.sleep(2)
    st.experimental_rerun()