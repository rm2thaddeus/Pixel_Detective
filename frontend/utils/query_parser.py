import logging
import re
# from qdrant_client import models # Will be replaced by API calls
from typing import Dict, Any, Tuple, List, Optional

# Metadata fields as extracted by metadata_extractor.py
METADATA_FIELDS = [
    'year', 'month', 'location', 'city', 'country', 'caption', 'date_taken', 'date_modified', 'date_digitized',
    'camera_make', 'camera_model', 'camera_serial',
    'lens_model', 'lens_make', 'lens_info', 'lens_id', 'lens_serial',
    'aperture', 'focal_length', 'shutter_speed', 'iso',
    'exposure_program', 'white_balance', 'flash_fired',
    'tags', 'keywords', 'subject', 'file_extension', 'image_format', 'color_mode', 'resolution',
    'width', 'height', 'aspect_ratio', 'filename', 'path', 'file_size_mb',
    'color_temperature', 'contrast', 'saturation', 'sharpness', 'metering_mode', 'scene_type', 'exposure_bias'
]

# Aliases for metadata fields (CSV/EXIF/XMP to query fields)
FIELD_ALIASES = {
    'aperture_value': 'aperture',
    'Keywords': 'keywords',
    'focal_length_35mm': 'focal_length',
    # Add more as needed
}

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
        metadata['tags'] = [t.lower() for t in tag_matches]
        for tag in tag_matches:
            remaining = re.sub(f'(tag:|#){tag}', '', remaining, flags=re.IGNORECASE)

    # Example: extract keywords (words after 'keyword:' or 'kw:')
    keyword_matches = re.findall(r'(?:keyword:|kw:)(\w+)', query_lower)
    if keyword_matches:
        metadata['keywords'] = [k.lower() for k in keyword_matches]
        for kw in keyword_matches:
            remaining = re.sub(f'(keyword:|kw:){kw}', '', remaining, flags=re.IGNORECASE)

    # Generic key:value or key=value parsing for all metadata fields and aliases
    for field in METADATA_FIELDS + list(FIELD_ALIASES.keys()):
        canonical_field = FIELD_ALIASES.get(field, field)
        pattern = re.compile(rf'{field}\s*[:=]\s*([\w\-\.]+)', re.IGNORECASE)
        matches = pattern.findall(query)
        if matches:
            matches = [m.lower() for m in matches]
            if canonical_field in metadata:
                if isinstance(metadata[canonical_field], list):
                    metadata[canonical_field].extend(matches)
                else:
                    metadata[canonical_field] = [metadata[canonical_field]] + matches
            else:
                metadata[canonical_field] = matches if len(matches) > 1 else matches[0]
            remaining = re.sub(pattern, '', remaining)

    # Normalize all metadata field names and values to lowercase
    metadata = {k.lower(): (v.lower() if isinstance(v, str) else [i.lower() for i in v] if isinstance(v, list) else v) for k, v in metadata.items()}

    # If 'year' is requested but not present, try to extract from date_taken/date_digitized
    if 'year' in metadata and not metadata['year']:
        for date_field in ['date_taken', 'date_digitized']:
            date_val = metadata.get(date_field)
            if date_val:
                year = str(date_val)[:4]
                if year.isdigit():
                    metadata['year'] = year
                    break

    # Clean up remaining text
    remaining = ' '.join(remaining.split())
    return metadata, remaining


def build_qdrant_filter(metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    DEPRECATED: Build a Qdrant-compatible filter from metadata dict.
    UI should send raw query or extracted keywords to backend via service_api.py.
    Backend is responsible for constructing DB-specific queries.
    """
    logger.warning("DEPRECATED: build_qdrant_filter() was called. Query construction is now backend responsibility.")
    # Original logic commented out as it's no longer UI's role.
    # if not metadata:
    #     return None
    # 
    # should_conditions = []
    # 
    # for key, value in metadata.items():
    #     if isinstance(value, list):
    #         for v in value:
    #             should_conditions.append({
    #                 "key": key, 
    #                 "match": {"value": v, "case_insensitive": True}
    #             })
    #     else:
    #         should_conditions.append({
    #             "key": key, 
    #             "match": {"value": value, "case_insensitive": True}
    #         })
    # 
    # # Use SHOULD instead of MUST for softer constraints
    # if should_conditions:
    #     return {"should": should_conditions}
    # 
    # return None
    raise NotImplementedError("UI should not construct Qdrant filters. Use service_api.py.")


def build_qdrant_filter_object(metadata: Dict[str, Any]):
    """
    DEPRECATED: Build a Qdrant Filter object from metadata dict for use with Query API.
    UI should send raw query or extracted keywords to backend via service_api.py.
    Backend is responsible for constructing DB-specific queries.
    """
    logger.warning("DEPRECATED: build_qdrant_filter_object() was called. Query construction is now backend responsibility.")
    # Original logic commented out as it uses qdrant_client.models and is no longer UI's role.
    # # try:
    # #     from qdrant_client import models
    # # except ImportError:
    # #     return None
    # 
    # if not metadata:
    #     return None
    # 
    # should_conditions = []
    # 
    # for key, value in metadata.items():
    #     if isinstance(value, list):
    #         for v in value:
    #             should_conditions.append(
    #                 models.FieldCondition(
    #                     key=key, 
    #                     match=models.MatchValue(value=v)
    #                 )
    #             )
    #     else:
    #         should_conditions.append(
    #             models.FieldCondition(
    #                 key=key, 
    #                 match=models.MatchValue(value=value)
    #             )
    #         )
    # 
    # if should_conditions:
    #     return models.Filter(should=should_conditions)
    # 
    # return None
    raise NotImplementedError("UI should not construct Qdrant filter objects. Use service_api.py.")


# Example usage (for testing)
if __name__ == "__main__":
    q = "happy family 2017 strasbourg canon #vacation f/2.8 50mm iso100 1/200s"
    meta, rem = parse_query(q)
    print("Metadata:", meta)
    print("Remaining text:", rem)
    print("Qdrant filter:", build_qdrant_filter(meta)) 