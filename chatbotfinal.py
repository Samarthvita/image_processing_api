import os
import fitz
from datetime import datetime
from flask import Flask, request, jsonify
from openai import AzureOpenAI
from typing import List, Dict, Any
from application_config import (
    AZ_OPENAI_API_BASE,
    AZ_OPENAI_API_BASEKEY,
    AZ_GPT16k_ENGINE,
    AZ_OPENAI_API_BASEVERSION
)

app = Flask(__name__)

def read_pdf(file_path):
    """Reads the PDF file and returns its text content."""
    pdf_document = fitz.open(file_path)
    pdf_text = ""
    for page_num in range(pdf_document.page_count):
        page = pdf_document[page_num]
        pdf_text += page.get_text()
    pdf_document.close()
    return pdf_text

# Dictionary to store conversation sessions
conversation_sessions: Dict[str, Dict[str, Any]] = {}

def create_azure_openai_client():
    """Create and return an Azure OpenAI client."""
    try:
        return AzureOpenAI(
            azure_endpoint=AZ_OPENAI_API_BASE,
            api_version=AZ_OPENAI_API_BASEVERSION,
            api_key=AZ_OPENAI_API_BASEKEY
        )
    except Exception as e:
        app.logger.error(f"Error creating Azure OpenAI client: {e}")
        return None

client = create_azure_openai_client()

def initialize_conversation(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Initialize or retrieve a conversation session from the payload"""
    file_path = r"C:\Users\admin\SAMARTH VITA MASTER FOLDER\BOILER PLATES\BOILER PLATE 1\Interview_Questions_HR.pdf"  # Change the path as needed
    pdf_content = read_pdf(file_path)  # Extract PDF content
    
    # Chunk the PDF content to fit the model's token limits
    pdf_chunks = chunk_pdf_content(pdf_content)
    
    # Save the chunks in the session to refer to them later
    session = {
        "app_name": payload.get('app_Name'),
        "document_name": payload.get('document_name'),
        "email_id": payload.get('emailId'),
        "user_id": payload.get('userId'),
        "messages": [],
        "created_at": datetime.now(),
        "pdf_chunks": pdf_chunks  # Store the chunked content
    }
    
    # Add a system message with context
    add_system_message(session, pdf_chunks[0])  # Start with the first chunk
    
    # Initialize with existing messages if provided
    messages = payload.get('message', [])
    for msg in messages:
        add_message(session, 
                    role=msg.get('role'),
                    content=msg.get('content'),
                    question_list=msg.get('questionList'),
                    page_number=msg.get('pageNumber'))
    
    return session

def get_relevant_chunk(query: str, pdf_chunks: List[str]) -> str:
    """Search through the document chunks to find the most relevant one based on the query"""
    # For simplicity, just return the first chunk (this can be improved with search techniques)
    # Ideally, you'd use a method to find the chunk most relevant to the query, e.g., cosine similarity, embeddings, etc.
    return pdf_chunks[0]  # For simplicity, just return the first chunk. Improve this logic as needed.

def add_system_message(session: Dict[str, Any], pdf_content: str):
    """Add a system message with context to the assistant"""
    # Make sure to give a clearer instruction to the assistant
    system_message = {
        "role": "system",
        "content": (
            "You are a helpful assistant that answers questions based solely on the content "
            "provided in the document. You cannot provide information outside the document. "
            "If you do not know the answer, say that you do not know. Here is the content of the document:\n\n"
            f"{pdf_content[:2000]}..."  # Limiting the content preview to the first 2000 characters.
        )
    }
    session["messages"].append(system_message)

def add_message(session: Dict[str, Any], role: str, content: str, question_list: List = None, page_number: Any = None):
    """Add a message to the session"""
    message = {
        "role": role,
        "content": content,  # Use content passed from the payload (user message or PDF content)
        "questionList": question_list or [],
        "pageNumber": page_number
    }
    session["messages"].append(message)

def chunk_pdf_content(pdf_content: str, chunk_size: int = 1000) -> List[str]:
    """Split the PDF content into smaller chunks to fit within the token limit."""
    # Split the document into chunks of the specified size (1000 characters by default)
    chunks = []
    for i in range(0, len(pdf_content), chunk_size):
        chunks.append(pdf_content[i:i + chunk_size])
    return chunks


def get_openai_messages(session: Dict[str, Any]) -> List[Dict[str, str]]:
    """Convert messages to OpenAI-compatible format"""
    return [{"role": msg["role"], "content": msg["content"]} for msg in session["messages"]]


def get_answer(session_id: str, session: Dict[str, Any], message: str) -> Dict[str, Any]:
    """Get an answer from Azure OpenAI using the conversation session"""
    try:
        # Add the new user message to the session
        add_message(session, role="user", content=message)
        
        # Get the relevant chunk from the document for the user's query
        relevant_chunk = get_relevant_chunk(message, session["pdf_chunks"])
        
        # Add the chunk as context to the system message
        add_system_message(session, relevant_chunk)
        
        # Get response from Azure OpenAI
        response = client.chat.completions.create(
            model=AZ_GPT16k_ENGINE,
            messages=get_openai_messages(session)
        )
        
        answer = response.choices[0].message.content.strip()
        
        # Add the assistant's response to the session
        add_message(session, role="assistant", content=answer)
        
        return {
            "status": "success",
            "answer": answer,
            "session_id": session_id
        }
    except Exception as e:
        app.logger.error(f"Error getting answer: {e}")
        return {
            "status": "error",
            "error": str(e),
            "session_id": session_id
        }
    
def upload_file():
    try:
        files_list = get_files_for_uploading('procurement', 'finance', 'legal', 'learning', 'presales')

@app.route('/chat', methods=['POST'])
def chat():
    """Enhanced chat endpoint handling the new payload structure"""
    try:
        payload = request.json
        session_id = payload.get('chat_session_id')
        message = payload.get('message', [])[-1].get('content') if payload.get('message') else None

        if not session_id or not message:
            return jsonify({
                "status": "error",
                "error": "Missing required fields: session_id or message"
            }), 400

        # Initialize or retrieve session
        if session_id not in conversation_sessions:
            conversation_sessions[session_id] = initialize_conversation(payload)  # Initialize session

        # Get answer
        result = get_answer(session_id, conversation_sessions[session_id], message)
        
        if result["status"] == "error":
            return jsonify(result), 500
            
        return jsonify(result)

    except Exception as e:
        app.logger.error(f"Error in chat endpoint: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/reset', methods=['POST'])
def reset_conversation():
    """Reset a conversation session"""
    data = request.json
    session_id = data.get('chat_session_id')

    if not session_id:
        return jsonify({
            "status": "error",
            "error": "Missing session_id"
        }), 400

    if session_id in conversation_sessions:
        del conversation_sessions[session_id]
        return jsonify({
            "status": "success",
            "message": f"Conversation session {session_id} has been reset"
        })
    
    return jsonify({
        "status": "success",
        "message": f"No active session found for {session_id}"
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "OK",
        "timestamp": datetime.now().isoformat()
    }), 200

if __name__ == "__main__":
    if not client:
        app.logger.error("Failed to initialize Azure OpenAI client. Exiting.")
        exit(1)
    app.run(debug=True)

    
#how to connect with mongodb using python or fla