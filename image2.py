from pymongo import MongoClient
from flask import Flask, jsonify, request
import os 

app = Flask(__name__)

client = MongoClient('mongodb://localhost:27017/')
db = client['image']
collection = db['image_chunks']

# collection.insert_one({"chunk_no": 99, "file": "image_data_in_chunk_0", "fileID": "file999"})
print("document inserted and collection created")

chunk_size = 1024

@app.route('/upload', methods = ['POST'])
def upload_image_chunks():
    file = request.files['file']
    # chunk_size = request.form['chunk_size']

    file_id = os.path.splitext(file.filename)[0]
    
    if collection.find_one({"fileId": file_id}):
        return jsonify({"error": "File with this name already exists. Please choose a different name."}), 400 

    image_data =file.read()
    # print(f"Image Size {len(image_data)} bytes.")

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

if __name__ == '__main__':
    app.run(debug=True)





#if 'file' not in request.files or 'file_id' not in request.form:
#return jsonify({"error": "Missing required parameters: file or file_id"}), 400
    