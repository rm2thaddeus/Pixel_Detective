import logging
import io
import os
import tempfile
from typing import Optional, Tuple

from PIL import Image

try:
    import rawpy
except ImportError:
    rawpy = None

logger = logging.getLogger(__name__)


def decode_and_prep_image(
    file_path: str,
) -> Tuple[Optional[Image.Image], Optional[str]]:
    """
    Reads an image file from a path, decodes it, and returns a PIL image.
    Handles standard formats and common RAW formats.
    """
    filename = os.path.basename(file_path)
    extension = os.path.splitext(filename)[1].lower()
    raw_exts = {".dng", ".cr2", ".nef", ".arw", ".rw2", ".orf"}

    try:
        # For RAW files, use rawpy
        if rawpy and extension in raw_exts:
            try:
                with rawpy.imread(file_path) as raw:
                    rgb = raw.postprocess(use_camera_wb=True)
                    image = Image.fromarray(rgb).convert("RGB")
                return image, None
            except Exception as raw_e:
                logger.error(f"Rawpy failed for {filename}: {raw_e}", exc_info=True)
                # Fallback to PIL just in case it's a non-standard raw file that PIL can handle
                pass
        
        # For standard formats (and as a fallback for rawpy), use PIL
        with open(file_path, "rb") as f:
            image_data = f.read()
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        return image, None

    except Exception as e:
        logger.error(
            f"Failed to decode image {filename}: {e}", exc_info=True
        )
        return None, f"Failed to decode image: {e}" 