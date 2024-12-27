#!/usr/bin/env python3
import sys
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_models_from_server(ip):
    """Make API request to a single server and return results"""
    url = f"http://{ip}:11434/api/tags"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return {
            "ip": ip,
            "status": "success",
            "data": response.json()
        }
    except requests.exceptions.RequestException as e:
        return {
            "ip": ip,
            "status": "error",
            "error": str(e)
        }

def filter_model_data(data):
    """Extract only model names and sizes from the data"""
    models = data.get('models', [])
    filtered_models = [{'name': model['name'], 'size': model['size']} 
                      for model in models 
                      if 'name' in model and 'size' in model]
    return filtered_models

def process_servers(server_list):
    """Process multiple servers in parallel"""
    with ThreadPoolExecutor(max_workers=None) as executor:
        future_to_ip = {
            executor.submit(get_models_from_server, ip.strip()): ip.strip()
            for ip in server_list
        }
        
        for future in as_completed(future_to_ip):
            ip = future_to_ip[future]
            try:
                result = future.result()
                print(f"\n{'='*50}")
                print(f"Server: {ip}")
                print(f"{'='*50}")
                if result["status"] == "success":
                    filtered_data = filter_model_data(result["data"])
                    formatted_json = json.dumps(filtered_data, indent=2)
                    print(formatted_json)
                else:
                    print(f"Error: {result['error']}")
                print(f"{'='*50}")
            except Exception as e:
                print(f"Error processing {ip}: {str(e)}")

def main():
    if not sys.stdin.isatty():
        print("Reading IPs from pipe...")
        server_list = [line.strip() for line in sys.stdin if line.strip()]
        process_servers(server_list)
    else:
        print("Error: Please provide server IPs via pipe")
        sys.exit(1)

if __name__ == "__main__":
    main()
