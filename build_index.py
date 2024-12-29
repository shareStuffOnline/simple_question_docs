#!/usr/bin/env python3

import sys
import json
import faiss
import numpy as np
import os

def main():
    # Make sure our output directory exists
    output_dir = "working_data"
    os.makedirs(output_dir, exist_ok=True)

    embeddings = []
    metadata_list = []

    # Read JSONL from stdin
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        doc = json.loads(line)
        # doc must contain "embedding" as a float array
        embedding = doc.get("embedding", [])
        if not embedding:
            continue
        
        # Convert to float32 for Faiss
        embeddings.append(embedding)

        # Store metadata (filename, text, etc.)
        # You can store more keys if needed
        metadata_list.append({
            "filename": doc.get("filename", ""),
            "text": doc.get("text", "")
        })

    # Convert to numpy array
    emb_array = np.array(embeddings, dtype=np.float32)
    if len(emb_array) == 0:
        print("No embeddings found. Exiting...")
        return

    # Build Faiss index
    d = emb_array.shape[1]   # dimension
    index = faiss.IndexFlatL2(d)
    index.add(emb_array)

    print(f"Indexed {index.ntotal} vectors of dimension {d}.")

    # Save index to disk in the working_data subdirectory
    index_path = os.path.join(output_dir, "faiss.index")
    faiss.write_index(index, index_path)

    # Save metadata to a JSON file in the working_data subdirectory
    metadata_path = os.path.join(output_dir, "faiss_metadata.json")
    with open(metadata_path, "w") as mfile:
        json.dump(metadata_list, mfile, ensure_ascii=False, indent=2)
    
    print(f"Index and metadata saved to '{output_dir}' folder.")

if __name__ == "__main__":
    main()

# (IndexFlatL2) to approximate search (IndexHNSWFlat, IndexIVFPQ, etc.) 
