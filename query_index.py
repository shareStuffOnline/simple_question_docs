import argparse
import json
import requests
import faiss
import numpy as np 


def get_query_embedding(query: str, model: str) -> np.ndarray:
    data = {
        "model": model,
        "input": query
    }

    #print("[DEBUG] Sending request data to embedding endpoint:", data)
    response = requests.post("http://localhost:5000/api/embed", json=data)
    #print("[DEBUG] Response status code:", response.status_code)
    #print("[DEBUG] Raw response text:", response.text)

    if response.status_code != 200:
        raise RuntimeError(f"Embedding server returned non-200 status code: {response.status_code}")

    json_resp = response.json()
    #print("[DEBUG] Parsed JSON from server:", json_resp)
    
    # Adjust for "embeddings" instead of "embedding".
    if "embeddings" in json_resp and len(json_resp["embeddings"]) > 0:
        embedding = json_resp["embeddings"][0]
        #print("[DEBUG] Extracted embedding vector:", embedding)  # <--- New debug line
    else:
        raise KeyError("No embedding found in 'embeddings' field.")

    # Convert to float32 NumPy array
    return np.array(embedding, dtype=np.float32)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True, help="The query text to embed and search.")
    parser.add_argument("--model", default="qwen:0.5b", help="Which model to use for embedding.")
    parser.add_argument("--top_k", type=int, default=3, help="Number of top results.")
    args = parser.parse_args()

    # Actually call the function
    query_vector = get_query_embedding(args.query, args.model)

    # Just to confirm it worked, print out the shape
    #print("[DEBUG] Returned embedding shape:", query_vector.shape)

    # Then do something with your embedding...
    # e.g. read a Faiss index, search, etc.
    index = faiss.read_index("faiss.index")
    with open("faiss_metadata.json", "r") as mfile:
        metadata_list = json.load(mfile)
    
    query_vector_2d = np.array([query_vector], dtype=np.float32)
    distances, indices = index.search(query_vector_2d, args.top_k)
    
    for rank, (dist, idx) in enumerate(zip(distances[0], indices[0]), start=1):
        meta = metadata_list[idx]
        print(f"\n#{rank} | Distance: {dist}")
        print(f"   Filename: {meta['filename']}")
        print(f"   Text: {meta['text'][:100]}...")  # truncated

