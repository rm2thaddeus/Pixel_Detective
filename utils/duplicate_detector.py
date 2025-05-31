import os
import hashlib
from collections import defaultdict
from typing import Dict, List, Tuple
from utils.metadata_extractor import extract_metadata
import imagehash
from PIL import Image


def compute_sha256(file_path: str, chunk_size: int = 8192) -> str:
    """Compute SHA-256 hash of a file's contents."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def scan_folder_for_hashes(folder: str, exts: Tuple[str, ...] = ('.jpg', '.jpeg', '.png', '.dng', '.tif', '.tiff', '.bmp', '.gif', '.raw')) -> Dict[str, List[str]]:
    """
    Recursively scan a folder for image files, compute SHA-256 hashes, and build a hash-to-file mapping.
    Returns: {hash: [file1, file2, ...]}
    """
    hash_map = defaultdict(list)
    for root, _, files in os.walk(folder):
        for fname in files:
            if fname.lower().endswith(exts):
                fpath = os.path.join(root, fname)
                try:
                    file_hash = compute_sha256(fpath)
                    hash_map[file_hash].append(fpath)
                except Exception as e:
                    print(f"Error hashing {fpath}: {e}")
    return dict(hash_map)


def get_exif_for_files(file_list: List[str]) -> Dict[str, dict]:
    """Extract key EXIF fields for each file using extract_metadata."""
    exif_map = {}
    for fpath in file_list:
        try:
            meta = extract_metadata(fpath)
            # Only keep key fields for duplicate review
            exif_map[fpath] = {
                'date_taken': meta.get('date_taken'),
                'camera_serial': meta.get('camera_serial'),
                'camera_make': meta.get('camera_make'),
                'camera_model': meta.get('camera_model'),
            }
        except Exception as e:
            exif_map[fpath] = {'error': str(e)}
    return exif_map


def find_duplicates(hash_map: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Return only hashes with more than one file (i.e., duplicates)."""
    return {h: files for h, files in hash_map.items() if len(files) > 1}


def print_duplicate_report(duplicates: Dict[str, List[str]], exif_map: Dict[str, dict] = None):
    """Print a summary of duplicate files, optionally with EXIF info."""
    if not duplicates:
        print("No exact duplicates found.")
        return
    print(f"Found {len(duplicates)} sets of duplicates:")
    for h, files in duplicates.items():
        print(f"\nHash: {h}")
        for f in files:
            print(f"  {f}")
            if exif_map and f in exif_map:
                exif = exif_map[f]
                exif_str = ', '.join(f"{k}: {v}" for k, v in exif.items() if v)
                if exif_str:
                    print(f"    EXIF: {exif_str}")


def compute_phash(file_path: str) -> str:
    """Compute perceptual hash (phash) of an image file."""
    try:
        with Image.open(file_path) as img:
            return str(imagehash.phash(img))
    except Exception as e:
        print(f"Error computing phash for {file_path}: {e}")
        return None


def scan_folder_for_phashes(folder: str, exts: tuple = ('.jpg', '.jpeg', '.png', '.dng', '.tif', '.tiff', '.bmp', '.gif', '.raw')) -> dict:
    """Scan a folder and compute phash for all images. Returns {phash: [file1, file2, ...]}"""
    phash_map = defaultdict(list)
    for root, _, files in os.walk(folder):
        for fname in files:
            if fname.lower().endswith(exts):
                fpath = os.path.join(root, fname)
                phash = compute_phash(fpath)
                if phash:
                    phash_map[phash].append(fpath)
    return dict(phash_map)


def find_near_duplicates_by_phash(folder: str, threshold: int = 5, exts: tuple = ('.jpg', '.jpeg', '.png', '.dng', '.tif', '.tiff', '.bmp', '.gif', '.raw')) -> list:
    """
    Find near-duplicate images in a folder using phash. Returns a list of sets of file paths.
    Images are grouped if their phash Hamming distance <= threshold.
    """
    from itertools import combinations
    file_phash = {}
    for root, _, files in os.walk(folder):
        for fname in files:
            if fname.lower().endswith(exts):
                fpath = os.path.join(root, fname)
                phash = compute_phash(fpath)
                if phash:
                    file_phash[fpath] = phash
    # Compare all pairs
    groups = []
    used = set()
    files = list(file_phash.keys())
    for i, f1 in enumerate(files):
        if f1 in used:
            continue
        group = [f1]
        for j in range(i+1, len(files)):
            f2 = files[j]
            if f2 in used:
                continue
            h1 = imagehash.hex_to_hash(file_phash[f1])
            h2 = imagehash.hex_to_hash(file_phash[f2])
            if h1 - h2 <= threshold:
                group.append(f2)
                used.add(f2)
        if len(group) > 1:
            groups.append(group)
            used.update(group)
    return groups


def print_phash_near_duplicate_report(groups: list):
    """Print a summary of near-duplicate image groups found by phash."""
    if not groups:
        print("No near-duplicates found by perceptual hash.")
        return
    print(f"Found {len(groups)} sets of near-duplicates (phash):")
    for i, group in enumerate(groups, 1):
        print(f"\nGroup {i}:")
        for f in group:
            print(f"  {f}") 