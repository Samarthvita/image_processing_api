import requests
from flask import Flask, jsonify, request
from flask_pymongo import PyMongo 
import gridfs
from datetime import datetime 
from bson.objectid import ObjectId
from io import BytesIO
import openai
from openai import AzureOpenAI
import os
from application_config import(
    AZ_OPENAI_API_BASE,
    AZ_OPENAI_API_BASEKEY,
    AZ_GPT16k_ENGINE,
    AZ_OPENAI_API_BASEVERSION
)

app = Flask(__name__)

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

# MongoDB setup 
app.config["MONGO_URL"]= "mongodb://localhost:27017/IMAGE_UPLOAD"
mongo = PyMongo(app, uri = "mongodb://localhost:27017/IMAGE_UPLOAD")
fs = gridfs.GridFS(mongo.db)

openai.api_key = AZ_OPENAI_API_BASEKEY

def format_image_metadata(image):
    return{
        "file_id": str(image["_id"]),
        "file_name": image['file_name'],
        # "time_stamp": image["timestamp"]
    }

#Route for uploading image
@app.route('/upload', methods = ['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']

    # Check if file is empty
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    #saving the image in gridfs and metadata in mongodb 
    file_id = fs.put(file, file_name = file.filename)
    timestamp = datetime.utcnow()

    #Saving the metadata to a seperate collection 
    image_metadata = {
        "_id" : file_id,
        "file_name": file.filename, 
        # "time_stamp": timestamp
    }
    mongo.db.IMAGE_UPLOAD_metadata.insert_one(image_metadata)
    return jsonify({"message": "File uploaded successfully", "file_id": str(file_id)}), 200

#Route to list all the uploaded images
@app.route('/IMAGES', methods = ['GET'])
def list_images():
    images = mongo.db.IMAGE_UPLOAD_metadata.find()
    result = [format_image_metadata(image) for image in images]
    return jsonify(result), 200
 
#Route to get metadata of a specific image 
@app.route('/IMAGE/<file_id>', methods =['GET'])
def get_image_metadata(file_id):
    image = mongo.db.IMAGE_UPLOAD_metadata.find_one({"_id": ObjectId(file_id)})
    if not image:
        return jsonify({"error": "image not found"}), 404 
    return jsonify(format_image_metadata(image)), 200

def extract_features_from_images(file):
    img_bytes = file.read()

    response = openai.Image.create(
        image= img_bytes,
        model = "openai/clp",
        features = True 
    )

    if response.status_code == 200:
        features = response.json().get('features', {})
        return features
    else:
        return({"error": "Failed to extract features from the imaege"})

#Route to ask questions about the image 
@app.route('/IMAGE/<file_id>/question', methods = ['POST'])
def ask_question(file_id):
    image = mongo.db.IMAGE_UPLOAD_metadata.find_one({"_id": ObjectId(file_id)})
    if not image:
        return jsonify({"error": "image not found"}), 404
    
    file = fs.get(ObjectId(file_id))

    image_features = extract_features_from_images(file)

    if 'error' in image_features:
        return jsonify({image_features}), 400 
    
    mongo.db.IMAGE_UPLOAD_features.update_one(
        {"_id": ObjectId(file_id)},
        {"$set":{"features": image_features}},
        upsert= True
    )
    
    question = request.json.get('question')
    if not question:
        return jsonify({"error": "No question provided"}), 400 

    prompt = f"Features extracted from the image: {image_features}. Answer the following question: {question}"

    response = openai.Completion.create(
        engine= AZ_GPT16k_ENGINE,
        prompt = prompt,
        max_tokens = 150, 
        temperature = 0.7
    )

    answer = response.choices[0].text.strip()
    return jsonify({"answer": answer}), 200 

    # if "name" in question.lower():
    #     answer = f"The image's name is {image['file_name']}."
    # elif "timestamp" in question.lower():
    #     answer = f"The image was uploaded on {image['timestamp']}."
    # else:
    #     answer = "Sorry, I don't know the answer to that question."

    # return jsonify({"question": question, "answer": answer}), 200

# def create_azure_openai_client():
#     try:
#         return AzureOpenAI(
#             azure_endpoint= AZ_OPENAI_API_BASE
#             api_version= AZ_OPENAI_API_BASEVERSION
#             api_key= AZ_OPENAI_API_BASEKEY
#         ) 
#     except Exception as e:
#         app.logger.error(f"Error in creating azure openai client:{e}")
#         return None 
# client = create_azure_openai_client()

# def initialize_conversation(payload: )

if __name__ == '__main__':
    app.run(debug=True)




image_metadata == path on s3, path saved on metadata 
#dependency alternatives 
#URL 
