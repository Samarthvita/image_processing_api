import os
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
    session = {
        "app_name": payload.get('app_Name'),
        "document_name": payload.get('document_name'),
        "email_id": payload.get('emailId'),
        "user_id": payload.get('userId'),
        "messages": [],
        "created_at": datetime.now()
    }
    #print(session)
    
    # Initialize with existing messages if provided
    messages = payload.get('message', [])
    #print(messages)
    for msg in messages:
        add_message(session, 
                    role=msg.get('role'),
                    content=msg.get('content'),
                    question_list=msg.get('questionList'),
                    page_number=msg.get('pageNumber'))
    
    return session

def add_message(session: Dict[str, Any], role: str, content: str, question_list: List = None, page_number: Any = None):
    """Add a message to the session"""
    message = {
        "role": role,
        "content": content,
        "questionList": question_list or [],
        "pageNumber": page_number
    }
    session["messages"].append(message)
    print (session)

def get_openai_messages(session: Dict[str, Any]) -> List[Dict[str, str]]:
    """Convert messages to OpenAI-compatible format"""
    return [{"role": msg["role"], "content": msg["content"]} for msg in session["messages"]]

def get_answer(session_id: str, session: Dict[str, Any], message: str) -> Dict[str, Any]:
    """Get an answer from Azure OpenAI using the conversation session"""
    try:
        # Add the new user message to the session
        add_message(session, role="user", content=message)
        print (get_openai_messages)
        
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

@app.route('/chat', methods=['POST'])
def chat():
    """Enhanced chat endpoint handling the new payload structure"""
    try:
        payload = request.json
        session_id = payload.get('chat_session_id')
        message = payload.get('message', [])[-1].get('content') if payload.get('message') else None
        print("last message",payload.get('message', [])[-1])


        if not session_id or not message:
            return jsonify({
                "status": "error",
                "error": "Missing required fields: session_id or message"
            }), 400

        # Initialize or retrieve session
        if session_id not in conversation_sessions:
            conversation_sessions[session_id] = initialize_conversation(payload)

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
