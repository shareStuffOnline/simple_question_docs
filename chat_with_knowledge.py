#!/usr/bin/env python3

import argparse
import json
import requests
import faiss
import numpy as np
import sys

def debug_print(*args):
    """Utility for quick debug logs to stderr (so they don't mix with normal output)."""
    print("[DEBUG]", *args, file=sys.stderr)

# 1) Embedding the user query
def get_query_embedding(query: str, model: str) -> np.ndarray:
    """
    Use your /api/embed endpoint to embed a user query.
    """
    data = {
        "model": model,
        "input": query
    }
    debug_print("Sending POST to /api/embed with data:", data)

    response = requests.post("http://localhost:5000/api/embed", json=data)
    debug_print("Response status code from /api/embed:", response.status_code)

    if response.status_code != 200:
        debug_print("Embedding error. Full response:", response.text)
        raise RuntimeError(f"Embedding server returned {response.status_code}")

    json_resp = response.json()
    #debug_print("Parsed JSON from /api/embed:", json_resp)

    # Adjust if your endpoint returns data differently:
    if "embeddings" in json_resp and len(json_resp["embeddings"]) > 0:
        embedding = json_resp["embeddings"][0]
    else:
        raise KeyError("No embedding found in 'embeddings' field.")
    return np.array(embedding, dtype=np.float32)

# 2) Query the Faiss index
def query_faiss_index(query_vector: np.ndarray, top_k: int, metadata_list, index) -> list:
    """
    Perform top-k similarity search in Faiss, return a list of docs with distances.
    """
    query_vector_2d = np.array([query_vector], dtype=np.float32)
    distances, indices = index.search(query_vector_2d, top_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        # If distance is float max (~3.4028235e+38), it means no close match
        meta = metadata_list[idx]
        results.append({
            "distance": dist,
            "filename": meta.get("filename", ""),
            "text": meta.get("text", "")
        })
    return results

# 3) Send to /api/chat
def chat_with_context(model: str, user_query: str, docs: list) -> str:
    """
    Combine user query + retrieved docs into a chat conversation, then
    call your local chat endpoint for a final answer.
    """
    # Flatten all retrieved docs into a single string or a bullet list
    context_str = "\n\n".join([
        f"[DOC] Filename: {d['filename']}\nText: {d['text']}" for d in docs
    ])

    system_prompt = f"""You are a helpful assistant with access to the following retrieved documents:
{context_str}

Please use this context to help answer user questions accurately.
"""

    # We form the messages:
    messages = [
      {
        "role": "system",
        "content": system_prompt
      },
      {
        "role": "user",
        "content": user_query
      }
    ]

    payload = {
        "model": model,
        "messages": messages,
        "stream": False  # set to True if you want streaming
    }

    debug_print("Sending POST to /api/chat with payload:", json.dumps(payload, indent=2))
    response = requests.post("http://localhost:5000/api/chat", json=payload)
    debug_print("Response status code from /api/chat:", response.status_code)

    if response.status_code != 200:
        debug_print("Chat error. Full response:", response.text)
        raise RuntimeError(f"Chat server returned {response.status_code}")

    chat_resp = response.json()
    debug_print("Full JSON response from /api/chat:", json.dumps(chat_resp, indent=2))


    return chat_resp

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True, help="User's question to the LLM.")
    parser.add_argument("--model", default="qwen:0.5b", help="Model to use for embedding and chat.")
    parser.add_argument("--top_k", type=int, default=3, help="Retrieve this many docs for context.")
    args = parser.parse_args()

    debug_print(f"Query: {args.query}, Model: {args.model}, top_k: {args.top_k}")

    # 1) Embed the user query
    query_emb = get_query_embedding(args.query, args.model)

    # 2) Load Faiss index and metadata
    debug_print("Loading Faiss index from working_data/faiss.index...")
    index = faiss.read_index("working_data/faiss.index")
    debug_print("Loading metadata from working_data/faiss_metadata.json...")
    with open("working_data/faiss_metadata.json", "r") as f:
        metadata_list = json.load(f)

    # 3) Query index for top-k docs
    results = query_faiss_index(query_emb, args.top_k, metadata_list, index)
    debug_print("Top-k results from Faiss:")
    for r in results:
        debug_print(r)

    # 4) Send everything to /api/chat
    #answer = chat_with_context(args.model, args.query, results) (debug - show all)
    answer = chat_with_context(args.model, args.query, results)["message"]["content"]


    # 5) Print the final LLM answer
    print("\n=== Final LLM Answer ===")
    print(answer)

if __name__ == "__main__":
    main()

