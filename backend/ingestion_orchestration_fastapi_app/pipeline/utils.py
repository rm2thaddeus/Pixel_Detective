import os
import hashlib
import base64
import io
import logging
import asyncio
from asyncio import Queue
from typing import List as TypingList, Dict, Any, TypeVar

import exifread
from PIL import Image
import rawpy
try:
    from python_xmp_toolkit import xmp
    from python_xmp_toolkit.xmp import XMPFile
    XMP_AVAILABLE = True
except ImportError:
    XMP_AVAILABLE = False


# Suppress verbose logging from libraries
logging.getLogger("exifread").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Helper to suppress Pillow's DecompressionBombError for large images
Image.MAX_IMAGE_PIXELS = None  # No limit

def compute_sha256(file_path: str) -> str:
    """Compute SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read and update hash in chunks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def _extract_keyword_tags(path: str) -> TypingList[str]:
    """
    Extracts IPTC/XMP keyword tags from an image file.
    This is a separate, best-effort function because XMP parsing can be fragile.
    """
    tags = set()
    if XMP_AVAILABLE:
        try:
            xmpfile = XMPFile(path, 'r')
            xmp_data = xmpfile.get_xmp()
            if xmp_data:
                for prop in xmp_data:
                    # Common XMP tags for keywords
                    if prop.property_name in ('photoshop:SidecarForExtension', 'dc:subject', 'lr:hierarchicalSubject'):
                        if isinstance(prop.property_value, list):
                            for item in prop.property_value:
                                tags.add(str(item))
                        else:
                            tags.add(str(prop.property_value))
            xmpfile.close_file()
        except Exception:
            # This can fail on many file types; we just ignore it.
            pass
    
    # Also check EXIF tags which can sometimes hold keywords.
    try:
        with open(path, 'rb') as f:
            exif_tags = exifread.process_file(f, details=False)
            if 'Image XPKeywords' in exif_tags:
                # This tag is often used by Windows and is UCS2 encoded.
                try:
                    keyword_bytes = exif_tags['Image XPKeywords'].values
                    # Decode from bytes (often UCS-2) into a string, ignoring errors.
                    keywords = keyword_bytes.decode('utf-16-le', errors='ignore').rstrip('\x00')
                    tags.update([k.strip() for k in keywords.split(';') if k.strip()])
                except Exception:
                    pass  # Ignore decoding errors
    except Exception:
        pass

    return sorted(list(tags))


def extract_image_metadata(file_path: str) -> Dict[str, Any]:
    """Extracts a wealth of metadata from an image file including EXIF,
    dimensions, and format. Handles both standard images and RAW files."""
    metadata = {
        "filename": os.path.basename(file_path),
        "full_path": os.path.abspath(file_path),
        "tags": _extract_keyword_tags(file_path),
    }
    file_extension = os.path.splitext(file_path)[1].lower()
    raw_exts = ('.dng', '.cr2', '.nef', '.arw', '.rw2', '.orf')

    try:
        if file_extension in raw_exts:
            # Use rawpy for RAW files: postprocess to determine dimensions
            with rawpy.imread(file_path) as raw:
                try:
                    arr = raw.postprocess(use_camera_wb=True)
                    height, width = arr.shape[:2]
                    mode = "RGB"
                except Exception as e:
                    logger.warning(f"Could not postprocess RAW for dimensions for {file_path}: {e}")
                    width, height = -1, -1
                    mode = "unknown"
                metadata.update({
                    "width": width,
                    "height": height,
                    "format": "RAW",
                    "mode": mode
                })
        else:
            # Use Pillow for standard image formats
            with Image.open(file_path) as img:
                metadata.update({
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode
                })

    except Exception as e:
        logger.warning(f"Could not read dimensions/format for {file_path}: {e}")
        metadata.update({"width": -1, "height": -1, "format": "unknown", "mode": "unknown"})

    # Extract EXIF data using exifread, which is more robust than Pillow's EXIF handling
    try:
        with open(file_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
            for tag, value in tags.items():
                if tag not in ('JPEGThumbnail', 'TIFFThumbnail'): # Exclude thumbnails
                    # Sanitize value for JSON serialization
                    try:
                        str_val = str(value.values)
                        # clean up string representation of byte arrays
                        if str_val.startswith("b'") or str_val.startswith('b"'):
                            str_val = str_val[2:-1]
                        metadata[f"exif_{tag.replace(' ', '_')}"] = str_val
                    except:
                        pass # Ignore unserializable tags
    except Exception as e:
        logger.debug(f"Could not extract EXIF data for {file_path}: {e}")

    return metadata

def create_thumbnail_base64(image_path: str, size: tuple = (200, 200)) -> str:
    """
    Creates a base64 encoded thumbnail for an image.
    Supports both standard image formats and RAW files.
    """
    file_extension = os.path.splitext(image_path)[1].lower()
    raw_exts = ('.dng', '.cr2', '.nef', '.arw', '.rw2', '.orf')

    try:
        if file_extension in raw_exts:
            with rawpy.imread(image_path) as raw:
                # Post-process the image to get an RGB array
                # use_camera_wb=True often gives better colors
                rgb_array = raw.postprocess(use_camera_wb=True)
            img = Image.fromarray(rgb_array)
        else:
            img = Image.open(image_path)
        
        img.thumbnail(size)
        
        # Ensure image is in RGB mode for saving as JPEG
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

    except Exception as e:
        logger.error(f"Failed to create thumbnail for {image_path}: {e}", exc_info=True)
        return ""

T = TypeVar('T')

async def gather_batch(queue: Queue[T], max_size: int, timeout: float) -> TypingList[T]:
    """
    Gathers a batch of items from an asyncio queue with a timeout.

    Args:
        queue: The asyncio queue to pull items from.
        max_size: The maximum number of items in a batch.
        timeout: The maximum time to wait for the first item.

    Returns:
        A list of items, which may be empty if the timeout is reached.
    """
    batch = []
    try:
        # Wait for the first item with a timeout
        first_item = await asyncio.wait_for(queue.get(), timeout=timeout)
        batch.append(first_item)
        queue.task_done()

        # Gather remaining items without blocking
        while len(batch) < max_size:
            try:
                item = queue.get_nowait()
                batch.append(item)
                queue.task_done()
            except asyncio.QueueEmpty:
                break  # No more items in the queue
    except asyncio.TimeoutError:
        pass  # No items received within the timeout

    return batch
