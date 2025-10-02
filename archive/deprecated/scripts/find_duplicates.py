import os
import sys
import argparse
import csv

# Add the parent directory to sys.path so Python can find the project modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logger import logger
from utils.duplicate_detector import (
    scan_folder_for_hashes,
    get_exif_for_files,
    find_duplicates,
    print_duplicate_report,
    find_near_duplicates_by_phash,
    print_phash_near_duplicate_report
)

def save_duplicates_csv(duplicates, exif_map, out_path, with_exif=False):
    """Save duplicate sets to a CSV file, optionally with EXIF info."""
    if with_exif:
        fieldnames = ['hash', 'file_path', 'date_taken', 'camera_serial', 'camera_make', 'camera_model']
    else:
        fieldnames = ['hash', 'file_path']
    with open(out_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for h, files in duplicates.items():
            for f in files:
                row = {'hash': h, 'file_path': f}
                if with_exif and exif_map and f in exif_map:
                    row.update(exif_map[f])
                writer.writerow(row)
    logger.info(f"Duplicate report saved to {out_path}")

def main():
    parser = argparse.ArgumentParser(description="Find exact and near-duplicate images by content and perceptual hash.")
    parser.add_argument('--folder', type=str, required=True, help='Path to the image folder to scan')
    parser.add_argument('--save-report', action='store_true', help='Save duplicate report as CSV')
    parser.add_argument('--with-exif', action='store_true', help='Include EXIF info in report/printout')
    parser.add_argument('--phash', action='store_true', help='Find near-duplicates using perceptual hash (phash)')
    parser.add_argument('--phash-threshold', type=int, default=5, help='Hamming distance threshold for phash near-duplicates (default: 5)')
    args = parser.parse_args()

    folder = args.folder
    if not os.path.isdir(folder):
        logger.error(f"Provided folder does not exist: {folder}")
        return
    logger.info(f"Scanning folder for images: {folder}")
    hash_map = scan_folder_for_hashes(folder)
    logger.info(f"Scanned {sum(len(v) for v in hash_map.values())} files.")
    duplicates = find_duplicates(hash_map)
    if args.with_exif and duplicates:
        all_files = [f for files in duplicates.values() for f in files]
        logger.info("Extracting EXIF info for duplicate files...")
        exif_map = get_exif_for_files(all_files)
    else:
        exif_map = None
    print_duplicate_report(duplicates, exif_map if args.with_exif else None)
    if args.save_report and duplicates:
        out_path = os.path.join(folder, 'duplicate_report.csv')
        save_duplicates_csv(duplicates, exif_map, out_path, with_exif=args.with_exif)

    # Perceptual hash near-duplicate detection
    if args.phash:
        logger.info(f"Finding near-duplicates using phash (threshold={args.phash_threshold})...")
        phash_groups = find_near_duplicates_by_phash(folder, threshold=args.phash_threshold)
        print_phash_near_duplicate_report(phash_groups)

if __name__ == "__main__":
    try:
        logger.info("=== Starting Duplicate Detection Script ===")
        main()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True) 