from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')

db = client['image']

collection = db['image_chunks']

# collection.insert_one({"chunk_no": 0, "file": "image_data_in_chunk_0", "fileID": "file1"})

print("document inserted and collection created")

image_path = r"C:\Users\admin\SAMARTH VITA MASTER FOLDER\BOILER PLATES\BOILER PLATE 1\roses_image.jpg"

with open(image_path, 'rb') as image_file:
    image_data = image_file.read()
    
print(f"Image Size : {len(image_data)} bytes")

num_chunks = 10

chunk_size = len(image_data) // num_chunks

chunks = []

file_id = ""

for i in range(num_chunks):
    start = i * chunk_size
    end = start + chunk_size if i < num_chunks - 1 else len(image_data)
    
    chunk_data = image_data[start:end]
   
    chunk_document = {
        "chunk_no": i,
        "file": chunk_data,
        "fileId": file_id
    }
    
    collection.insert_one(chunk_document)
print(f"Inserted chunk {i + 1}/{num_chunks} into MongoDB.")

output_path = r"C:\Users\admin\SAMARTH VITA MASTER FOLDER\BOILER PLATES\BOILER PLATE 1\reconstructed_image.jpg"

def retrieving_data_from_chunks(file_id, output_path):
    chunks = collection.find({"fileId": file_id}).sort("chunk_no", 1)

    with open(output_path, 'wb') as output_file:
        for chunk in chunks:
            output_file.write(chunk['file'])

    print(f"Image reconstructed and saved to {output_path}")
    
if __name__ == "__main__":
    retrieving_data_from_chunks('file1', 'reconstructed_image.jpg')  