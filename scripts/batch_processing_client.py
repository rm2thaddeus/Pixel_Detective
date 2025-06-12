import httpx
import asyncio
import os
import argparse # For command-line arguments

INGESTION_ORCHESTRATION_SERVICE_URL = os.environ.get("INGESTION_ORCHESTRATION_URL", "http://localhost:8002")

async def run_ingestion_for_directory(directory_path: str):
    if not os.path.isdir(directory_path):
        print(f"Error: Directory not found at '{directory_path}'")
        return

    async with httpx.AsyncClient(timeout=None) as client: # Extended timeout for potentially long processing
        try:
            print(f"Sending ingestion request for directory: {directory_path}")
            response = await client.post(
                f"{INGESTION_ORCHESTRATION_SERVICE_URL}/ingest_directory",
                json={"directory_path": directory_path}
            )
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            result = response.json()
            print("Ingestion service response:")
            # Pretty print the JSON response for better readability
            import json
            print(json.dumps(result, indent=4))

        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            print(f"Request error occurred: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Client to trigger directory ingestion.")
    parser.add_argument(
        "directory", 
        type=str, 
        help="The absolute path to the directory of images to ingest."
    )
    args = parser.parse_args()

    # Example usage:
    # python scripts/batch_processing_client.py "/path/to/your/image_directory"
    # For testing, you can create a dummy directory with a few files.
    # Make sure the Ingestion Orchestration Service is running.

    asyncio.run(run_ingestion_for_directory(args.directory)) 