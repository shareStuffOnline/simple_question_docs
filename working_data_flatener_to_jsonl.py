import os
import json

# Define directories and files
data_dir = "working_data"
output_file = "working_data/documents.jsonl"

with open(output_file, "w", encoding="utf-8") as out_file:
    for filename in os.listdir(data_dir):
        if filename.endswith(".txt"):
            file_path = os.path.join(data_dir, filename)

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Flatten newlines and escape double quotes
            flattened_text = content.replace("\n", " ")
            flattened_text = flattened_text.replace('"', '\\"')

            # Create the JSON record
            record = {
                "filename": filename,
                "text": flattened_text
            }

            # Write one JSON object per line
            out_file.write(json.dumps(record) + "\n")

# Print the absolute path to documents.jsonl
print(os.path.abspath(output_file))

