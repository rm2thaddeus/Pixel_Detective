import re
from typing import Dict, Any, Tuple, List

# Metadata fields as extracted by metadata_extractor.py
METADATA_FIELDS = [
    'year', 'month', 'location', 'city', 'country', 'caption', 'date_taken', 'date_modified',
    'camera_make', 'camera_model', 'camera_serial',
    'lens_model', 'lens_make', 'lens_info', 'lens_id', 'lens_serial',
    'aperture', 'focal_length', 'shutter_speed', 'iso',
    'exposure_program', 'white_balance', 'flash_fired',
    'tags', 'keywords', 'subject', 'file_extension', 'image_format', 'color_mode', 'resolution',
    'width', 'height', 'aspect_ratio', 'filename', 'path', 'file_size_mb'
]

# Simple regex patterns for demo purposes (can be extended)
YEAR_PATTERN = re.compile(r'(19|20)\d{2}')
MONTHS = [
    'january', 'february', 'march', 'april', 'may', 'june',
    'july', 'august', 'september', 'october', 'november', 'december'
]

# Camera and lens brands (expandable)
CAMERA_BRANDS = [
    'sony', 'canon', 'nikon', 'fuji', 'fujifilm', 'leica', 'olympus', 'panasonic', 'pentax', 'ricoh', 'hasselblad',
    'apple', 'samsung', 'google', 'lumix', 'sigma', 'phase one', 'mamiya', 'minolta', 'kodak', 'casio', 'epson', 'xiaomi'
]
LENS_KEYWORDS = [
    'zeiss', 'sigma', 'tamron', 'tokina', 'canon', 'nikon', 'sony', 'fujinon', 'leica', 'olympus', 'panasonic', 'pentax', 'ricoh', 'hasselblad'
]

APERTURE_PATTERN = re.compile(r'f\/?\s?(\d+\.?\d*)', re.IGNORECASE)
FOCAL_LENGTH_PATTERN = re.compile(r'(\d+\.?\d*)\s?mm', re.IGNORECASE)
ISO_PATTERN = re.compile(r'iso\s?(\d+)', re.IGNORECASE)
SHUTTER_PATTERN = re.compile(r'(1/\d+s|\d+\.?\d*s)', re.IGNORECASE)


def parse_query(query: str) -> Tuple[Dict[str, Any], str]:
    """
    Parse a free-text query into metadata constraints and a remaining text query.
    Returns (metadata_dict, remaining_text).
    """
    query_lower = query.lower()
    metadata = {}
    remaining = query

    # Extract year
    year_match = YEAR_PATTERN.search(query_lower)
    if year_match:
        metadata['year'] = year_match.group()
        remaining = remaining.replace(year_match.group(), '')

    # Extract month
    for month in MONTHS:
        if month in query_lower:
            metadata['month'] = month
            remaining = re.sub(month, '', remaining, flags=re.IGNORECASE)
            break

    # Camera make/model
    for brand in CAMERA_BRANDS:
        if brand in query_lower:
            metadata['camera_make'] = brand
            remaining = re.sub(brand, '', remaining, flags=re.IGNORECASE)
            break

    # Lens brand/model
    for lens in LENS_KEYWORDS:
        if lens in query_lower:
            metadata['lens_make'] = lens
            remaining = re.sub(lens, '', remaining, flags=re.IGNORECASE)
            break

    # Aperture (e.g., f/2.8)
    aperture_match = APERTURE_PATTERN.search(query_lower)
    if aperture_match:
        metadata['aperture'] = f"f/{aperture_match.group(1)}"
        remaining = re.sub(APERTURE_PATTERN, '', remaining)

    # Focal length (e.g., 50mm)
    focal_match = FOCAL_LENGTH_PATTERN.search(query_lower)
    if focal_match:
        metadata['focal_length'] = f"{focal_match.group(1)}mm"
        remaining = re.sub(FOCAL_LENGTH_PATTERN, '', remaining)

    # ISO (e.g., ISO 100)
    iso_match = ISO_PATTERN.search(query_lower)
    if iso_match:
        metadata['iso'] = iso_match.group(1)
        remaining = re.sub(ISO_PATTERN, '', remaining)

    # Shutter speed (e.g., 1/200s, 2s)
    shutter_match = SHUTTER_PATTERN.search(query_lower)
    if shutter_match:
        metadata['shutter_speed'] = shutter_match.group(1)
        remaining = re.sub(SHUTTER_PATTERN, '', remaining)

    # Example: extract tags (words after 'tag:' or '#')
    tag_matches = re.findall(r'(?:tag:|#)(\w+)', query_lower)
    if tag_matches:
        metadata['tags'] = tag_matches
        for tag in tag_matches:
            remaining = re.sub(f'(tag:|#){tag}', '', remaining, flags=re.IGNORECASE)

    # Example: extract keywords (words after 'keyword:' or 'kw:')
    keyword_matches = re.findall(r'(?:keyword:|kw:)(\w+)', query_lower)
    if keyword_matches:
        metadata['keywords'] = keyword_matches
        for kw in keyword_matches:
            remaining = re.sub(f'(keyword:|kw:){kw}', '', remaining, flags=re.IGNORECASE)

    # Clean up remaining text
    remaining = ' '.join(remaining.split())
    return metadata, remaining


def build_qdrant_filter(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a Qdrant-compatible filter from metadata dict.
    """
    if not metadata:
        return {}
    must = []
    for key, value in metadata.items():
        if isinstance(value, list):
            for v in value:
                must.append({"key": key, "match": {"value": v}})
        else:
            must.append({"key": key, "match": {"value": value}})
    return {"must": must}


# Example usage (for testing)
if __name__ == "__main__":
    q = "happy family 2017 strasbourg canon #vacation f/2.8 50mm iso100 1/200s"
    meta, rem = parse_query(q)
    print("Metadata:", meta)
    print("Remaining text:", rem)
    print("Qdrant filter:", build_qdrant_filter(meta)) 