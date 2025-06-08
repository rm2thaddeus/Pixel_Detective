#!/usr/bin/env python3
# Requires: pip install requests

import os, sys, base64, json, time, argparse

import requests


def load_images(folder):
    exts = ('.jpg', '.jpeg', '.png', '.dng', '.heic', '.tiff')
    images = []
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(exts):
                images.append(os.path.join(root, f))
    return images


def main():
    parser = argparse.ArgumentParser(description="Benchmark ML inference service batch endpoint")
    parser.add_argument('--folder', required=True, help="Path to image folder")
    parser.add_argument('--url', default='http://localhost:8001/api/v1/batch_embed_and_caption', help="ML inference batch endpoint URL")
    args = parser.parse_args()

    images = load_images(args.folder)
    if not images:
        print(f"No images found in {args.folder}")
        sys.exit(1)

    items = []
    for path in images:
        with open(path, 'rb') as f:
            data = f.read()
        b64 = base64.b64encode(data).decode('utf-8')
        items.append({
            'unique_id': os.path.basename(path),
            'filename': os.path.basename(path),
            'image_base64': b64
        })

    payload = {'images': items}
    print(f"Sending {len(items)} images to {args.url}")
    start = time.time()
    resp = requests.post(args.url, json=payload)
    elapsed = time.time() - start
    print(f"Elapsed time: {elapsed:.2f}s, status: {resp.status_code}")

    if resp.ok:
        results = resp.json().get('results', [])
        success = sum(1 for r in results if not r.get('error'))
        print(f"Success: {success}/{len(results)} images processed without error")
    else:
        print("Error response:", resp.text)


if __name__ == '__main__':
    main() 