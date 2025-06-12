import httpx
import time
import os
import sys

# Add project root to path to allow importing from other directories
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Configuration ---
INGESTION_SERVICE_URL = "http://localhost:8002"
# IMPORTANT: Use the absolute path to your test images directory
# User provided path: C:\Users\aitor\OneDrive\Escritorio\dng test
# Python on Windows needs either double backslashes or forward slashes.
IMAGE_DIRECTORY = "C:/Users/aitor/OneDrive/Escritorio/dng test"

def run_ingestion_test():
    """
    Tests the full backend ingestion pipeline.
    1. Starts an ingestion job.
    2. Polls for status until the job is complete.
    3. Prints a summary of the results and performance.
    """
    print("🚀 Starting Backend Performance and Correctness Test...")
    print("=" * 60)
    print(f"Target Ingestion Service: {INGESTION_SERVICE_URL}")
    print(f"Target Image Directory:   {IMAGE_DIRECTORY}")
    print("=" * 60)

    if not os.path.isdir(IMAGE_DIRECTORY):
        print(f"❌ CRITICAL: Image directory not found at '{IMAGE_DIRECTORY}'")
        print("Please ensure the path is correct and accessible.")
        return

    client = httpx.Client(timeout=120.0)
    job_id = None
    start_time = time.time()

    # 1. Start the ingestion job
    try:
        print("\n▶️  Sending request to start ingestion...")
        response = client.post(
            f"{INGESTION_SERVICE_URL}/api/v1/ingest/",
            json={"directory_path": IMAGE_DIRECTORY},
            timeout=30.0
        )
        response.raise_for_status()
        job_info = response.json()
        job_id = job_info.get("job_id")
        print(f"✅ Ingestion job started successfully. Job ID: {job_id}")
    except httpx.HTTPStatusError as e:
        print(f"❌ Error starting ingestion job: {e.response.status_code}")
        print(f"   Response: {e.response.text}")
        return
    except httpx.RequestError as e:
        print(f"❌ Connection Error: Could not connect to the Ingestion Service at {INGESTION_SERVICE_URL}.")
        print("   Please ensure both the Ingestion and ML Inference services are running.")
        return

    # 2. Poll for job status
    if not job_id:
        print("❌ CRITICAL: Failed to get Job ID. Cannot monitor status.")
        return

    print("\n🔄 Monitoring job progress...")
    last_log_count = 0
    try:
        while True:
            response = client.get(f"{INGESTION_SERVICE_URL}/api/v1/ingest/status/{job_id}")
            response.raise_for_status()
            status_info = response.json()

            # Print new log messages
            logs = status_info.get("logs", [])
            if len(logs) > last_log_count:
                for log_line in logs[last_log_count:]:
                    print(f"   [LOG] {log_line}")
                last_log_count = len(logs)

            status = status_info.get("status")
            progress = status_info.get("progress", 0)
            print(f"   ... Job Status: {status.upper()} | Progress: {progress:.2f}%")

            if status in ["completed", "failed"]:
                print(f"\n✅ Job finished with status: {status.upper()}")
                end_time = time.time()
                break

            time.sleep(5) # Poll every 5 seconds

    except httpx.HTTPStatusError as e:
        print(f"❌ Error getting job status: {e.response.status_code}")
        print(f"   Response: {e.response.text}")
        return
    except httpx.RequestError as e:
        print(f"❌ Connection Error while monitoring job: {e}")
        return

    # 3. Print final report
    total_time = end_time - start_time
    print("\n" + "=" * 60)
    print("📊 FINAL PERFORMANCE REPORT")
    print("=" * 60)
    print(f"Total Ingestion Time: {total_time:.2f} seconds")

    final_result = status_info.get("result", {})
    if status == "completed":
        processed_count = final_result.get("processed_count", 0)
        failed_count = final_result.get("failed_count", 0)
        print(f"Files Processed: {processed_count}")
        print(f"Files Failed:    {failed_count}")
        if processed_count > 0:
            avg_time_per_file = total_time / processed_count
            print(f"Average time per file: {avg_time_per_file:.2f} seconds")
        if failed_count > 0:
            print("\n🚨 Failures Reported:")
            for detail in final_result.get("failed_details", []):
                print(f"  - File: {detail.get('file')}, Error: {detail.get('error')}")
    else: # Failed
        print("   Job failed. Final result details:")
        print(f"   {final_result.get('error')}")
        print(f"   {final_result.get('message')}")

    print("\n" + "=" * 60)
    print("Test complete.")


if __name__ == "__main__":
    # Before running, make sure you have started the backend services:
    # 1. Start the ML Inference service (e.g., in one terminal):
    #    cd backend/ml_inference_fastapi_app
    #    python main.py
    #
    # 2. Start the Ingestion Orchestration service (e.g., in another terminal):
    #    cd backend/ingestion_orchestration_fastapi_app
    #    python main.py
    #
    # 3. Ensure your Qdrant container is running.
    run_ingestion_test() 