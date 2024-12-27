import threading
import time
import subprocess

def make_api_calls(thread_id, num_calls=30):
    """
    Function for each thread to call the API multiple times.
    """
    for i in range(num_calls):
        start_time = time.time()
        # This curl command mirrors the example you gave:
        curl_cmd = [
            "curl", "-X", "POST", "http://127.0.0.1:5000/api/generate",
            "-H", "Content-Type: application/json",
            "-d", '{"model": "qwen:0.5b", "prompt": "Why is the sky blue?", "priority": 1, "stream": false}'
        ]
        # Run the curl command and capture output (stdout/stderr)
        result = subprocess.run(curl_cmd, capture_output=True, text=True)
        elapsed_time = time.time() - start_time
        
        print(f"[Thread {thread_id}] Request {i} => Elapsed: {elapsed_time:.4f}s, "
              f"Status: {result.returncode}, Output: {result.stdout.strip()}")

def run_test():
    """
    Launches threads, each issuing API calls, and times the entire run.
    """
    start_time = time.time()
    threads = []

    # Create two threads
    for thread_id in range(10):
        t = threading.Thread(target=make_api_calls, args=(thread_id, 100))
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

