#!/usr/bin/env python3
import sys
import json
import requests

EMBED_URL = "http://localhost:5000/api/embed"
MODEL_NAME = "qwen:0.5b"

for line in sys.stdin:
    doc = json.loads(line)
    text = doc["text"]
    payload = {"model": MODEL_NAME, "input": text}
    
    resp = requests.post(EMBED_URL, json=payload)
    resp.raise_for_status()
    data = resp.json()
    
    doc["embedding"] = data["embeddings"][0]
    print(json.dumps(doc))


# cat documents.jsonl | python embed_docs.py > embedded_docs.jsonl
# cat working_data/documents.jsonl | python3 embed_docs.py > working_data/embedded_docs.jsonl

