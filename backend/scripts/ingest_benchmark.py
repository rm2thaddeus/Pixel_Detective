#!/usr/bin/env python3
# Requires: pip install requests

import sys, time, argparse
import requests


def main():
    parser = argparse.ArgumentParser(description="Benchmark ingestion orchestration service")
    parser.add_argument('--folder', required=True, help="Path to image folder")
    parser.add_argument('--url', default='http://localhost:8002', help="Base URL of ingestion service")
    parser.add_argument('--collection', default='optimization_test', help="Target Qdrant collection name")
    args = parser.parse_args()

    base_url = args.url.rstrip('/')

    # Create collection (ignore if already exists)
    try:
        resp = requests.post(f"{base_url}/api/v1/collections", json={"collection_name": args.collection})
        if resp.ok:
            print(f"Collection '{args.collection}' created.")
        else:
            print(f"Collection create status: {resp.status_code}, message: {resp.text}")
    except Exception as e:
        print(f"Error creating collection: {e}")

    # Select collection
    try:
        resp = requests.post(f"{base_url}/api/v1/collections/select", json={"collection_name": args.collection})
        if resp.ok:
            print(f"Selected collection '{args.collection}'.")
        else:
            print(f"Collection select status: {resp.status_code}, message: {resp.text}")
    except Exception as e:
        print(f"Error selecting collection: {e}")

    # Start ingestion job
    try:
        resp = requests.post(f"{base_url}/api/v1/ingest/", json={"directory_path": args.folder})
        resp.raise_for_status()
        job_id = resp.json().get('job_id')
        print(f"Ingestion job started: {job_id}")
    except Exception as e:
        print(f"Error starting ingestion job: {e}")
        sys.exit(1)

    # Poll status until completed
    start = time.time()
    status = ''
    while True:
        try:
            status_resp = requests.get(f"{base_url}/api/v1/ingest/status/{job_id}")
            status_resp.raise_for_status()
            data = status_resp.json()
            status = data.get('status')
            progress = data.get('progress', 0)
            print(f"Progress: {progress:.1f}%")
            if status in ('completed', 'failed'):
                break
        except Exception as e:
            print(f"Error fetching status: {e}")
            break
        time.sleep(1)

    elapsed = time.time() - start
    print(f"Ingestion {status} in {elapsed:.2f} seconds.")
    # Optionally print result details
    result = data.get('result')
    if result:
        print(f"Result: {result}")


if __name__ == '__main__':
    main() 