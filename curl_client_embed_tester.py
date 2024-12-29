 #!/usr/bin/env python3

import threading
import time
import subprocess

def make_api_calls(thread_id, num_calls=4):
    """
    Function for each thread to call the /api/embed endpoint multiple times.
    """
    for i in range(num_calls):
        start_time = time.time()
        
        # Example embedding payload with multiple inputs
        request_body = """{
            "model": "qwen:0.5b",
            "input": ["Why is the sky blue?", "Why is the grass green?"]
        }"""
        
        curl_cmd = [
            "curl",
            "-X", "POST",
            "http://127.0.0.1:5000/api/embed",
            "-H", "Content-Type: application/json",
            "-d", request_body
        ]
        
        # Run the curl command and capture output
        result = subprocess.run(curl_cmd, capture_output=True, text=True)
        elapsed_time = time.time() - start_time
        
        print(f"[Thread {thread_id}] Request {i} => "
              f"Elapsed: {elapsed_time:.4f}s, "
              f"Status: {result.returncode}, "
              f"Output: {result.stdout.strip()}")

def run_test():
    """
    Launches threads, each issuing API calls to /api/embed, and times the entire run.
    """
    start_time = time.time()
    threads = []

    # Create two threads (change this number as needed for concurrency tests)
    for thread_id in range(2):
        t = threading.Thread(target=make_api_calls, args=(thread_id, 4))
        threads.append(t)

    # Start both threads
    for t in threads:
        t.start()

    # Wait for both threads to finish
    for t in threads:
        t.join()

    total_elapsed = time.time() - start_time
    print(f"Total elapsed time for all threads: {total_elapsed:.4f} seconds")

if __name__ == "__main__":
    run_test()
