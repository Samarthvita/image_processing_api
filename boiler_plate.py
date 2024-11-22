import os
import fitz
from flask import Flask, request, jsonify
from openai import AzureOpenAI
from application_config import (
    AZ_OPENAI_API_BASE,
    AZ_OPENAI_API_BASEKEY,
    AZ_GPT16k_ENGINE,
    AZ_OPENAI_API_BASEVERSION
)

app = Flask(__name__)

def read_pdf(file_path):
    # Open the PDF file
    pdf_document = fitz.open(file_path)
    #variable that contain text
    pdf_text = ""    

    # Iterate through each page and extract text
    for page_num in range(pdf_document.page_count):
        page = pdf_document[page_num]
        pdf_text += page.get_text()  # Append each page's text to pdf_text

    pdf_document.close()  # Close the PDF file
    return pdf_text


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

def get_answer(question):
    """
    Get an answer from Azure OpenAI for the given question.
    
    Args:
        question (str): The user's question.
    
    Returns:
        str: The answer from the AI model, or an error message.
    """
    try:
        file_path = r"C:\Users\admin\SAMARTH VITA MASTER FOLDER\BOILER PLATES\BOILER PLATE 1\Interview_Questions_HR.pdf"
        pdf_content = read_pdf(file_path)
        
        response = client.chat.completions.create(
                    model=AZ_GPT16k_ENGINE, 
                    messages=[
                             {"role": "system", "content": "You are a helpful assistant that answers questions from the given User guide: {pdf_content}"},
                             {"role": "user", "content": f"question: {question} "}
                             ]
                            )

        return response.choices[0].message.content.strip()
    except Exception as e:
        app.logger.error(f"Error getting answer: {e}")
        return f"Error getting answer: {e}"
    
@app.route('/ask', methods=['POST'])
def ask_question():
    """API endpoint to ask a question and get an answer."""
    data = request.json
    question = data.get('question')

    #pdf_text = read_pdf(file_path)
    

    if not question:
        return jsonify({"error": "Please provide a question."}), 400

    answer = get_answer(question)
    return jsonify({"answer": answer})


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "OK"}), 200

if __name__ == "__main__":
    if not client:
        app.logger.error("Failed to initialize Azure OpenAI client. Exiting.")
    else:
        app.run(debug=True)