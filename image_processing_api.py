import logging
from pymongo import MongoClient
from flask import Flask, jsonify, request
import openai
import pytesseract
from PIL import Image 
import os 
import io
from io import BytesIO
from application_config import(
    AZ_OPENAI_API_BASE,
    AZ_OPENAI_API_BASEKEY,
    AZ_GPT16k_ENGINE,
    AZ_OPENAI_API_BASEVERSION
)
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\admin\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'
print(pytesseract.get_languages())

app = Flask(__name__)

client = MongoClient('mongodb://localhost:27017/')
db = client['image']
collection = db['image_chunks']

print("document inserted and collection created")

chunk_size = 1024

openai.api_key = AZ_OPENAI_API_BASEKEY

@app.route('/upload', methods = ['POST'])
def upload_image_chunks():
    file = request.files['file']
    # chunk_size = request.form['chunk_size']

    file_id = os.path.splitext(file.filename)[0]
    
    if collection.find_one({"fileId": file_id}):
        return jsonify({"error": "File with this name already exists. Please choose a different name."}), 400 

    image_data =file.read()
    print(f"Image Size {len(image_data)} bytes.")

    num_chunks = (len(image_data) + chunk_size - 1)//chunk_size

    for i in range(num_chunks):
        start = i * chunk_size 
        end = start + chunk_size if i < num_chunks -1 else len(image_data)
        chunk_data = image_data[start:end]

        chunk_document = {
            "chunk_no" : i,
            "file" : chunk_data,
            "fileId" : file_id
        }

        collection.insert_one(chunk_document)

    return jsonify({"message": "file uplaoded and chunks saved successfully"}), 200 

@app.route('/retrieve/<file_id>', methods=['GET'])
def retrieve_file(file_id):
    chunks = collection.find({"fileId": file_id}).sort("chunk_no", 1)

    if not chunks:
        return jsonify({"error": "No file found with the given file_id."}), 404

    output_path = f"reconstructed_{file_id}.jpg"  
    with open(output_path, 'wb') as output_file:
        for chunk in chunks:
            output_file.write(chunk['file'])

    return jsonify({"message": f"File reconstructed and saved as {output_path}."}), 200

@app.route('/distinct_fileID', methods = ['GET'])
def distinct_file_ids(): 
    distinct_file_ids = collection.distinct("fileId")
    return jsonify({"file_ids": distinct_file_ids}), 200 

def az_open_ai_cred():
    try:
        openai.api_type = "azure"
        openai.azure_endpoint = AZ_OPENAI_API_BASE
        openai.api_version = AZ_OPENAI_API_BASEVERSION
        openai.api_key = AZ_OPENAI_API_BASEKEY
        print("OpenAI credentials set successfully.")
    except Exception as e:
        logging.error("Error setting OpenAI credentials: %s", str(e))

client = az_open_ai_cred

@app.route('/ask', methods = ["POST"])
def ask_question():
    data = request.get_json()
    az_open_ai_cred()
    if 'file_id' not in data or 'question' not in data:
        return jsonify({"error": "Missing file_id or question parameter"}), 400 
    
    file_id = data['file_id']
    question = data['question']

    file_metadata = collection.find_one({'fileId': file_id })
    if not file_metadata:
        return jsonify ({"error": f"No such file with id {file_id}."}), 404

    chunks = collection.find({"fileId": file_id}).sort("chunk_no", 1)
    image_data = b''.join([chunk['file'] for chunk in chunks])
    image = Image.open(io.BytesIO(image_data))
    print(f"Image loaded successfully. Size: {image.size}, Mode: {image.mode}")
    text = pytesseract.image_to_string(image, lang = 'eng')
    print(f'text of image::::: {text}')

    # file_info = {
    #     "file_id": file_metadata["fileId"],
    #     "chunk_count": collection.count_documents({"fileID": file_id}),
    #     "chunk_size": chunk_size
    # }
    
    # messages=[
    #         {"role": "user", "content": f"The uploaded file by the user with file id {file_info['file_id']}. The file has {file_info['chunk_count']} chunks and the size of chunk is {file_info['chunk_size']} bytes. Finally, the extracted text from the image is: {text}/n Question: {question}."
    #     }],
    
    messages = [
                    {"role": "user", "content": f"{text}\nQuestion: {question}"}
                ]
    
    response = openai.chat.completions.create(
        model=AZ_GPT16k_ENGINE, 
        temperature=0,
        messages = messages,
        max_tokens=100
    )

    print('Text of image:')
    answer = response.choices[0].message.content
    return jsonify({f"The answer to the question: {question} is:" : answer}), 200 

if __name__ == '__main__':
    app.run(debug=True, port=5001)   