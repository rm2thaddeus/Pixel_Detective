# 📂 File Path: /project_root/metadata_extractor.py
# 📌 Purpose: This file is responsible for extracting metadata from image files, focusing on XMP data.
# 🔄 Latest Changes: Added detailed comments to improve code readability and maintainability.
# ⚙️ Key Logic: Utilizes Python's os, xml.etree.ElementTree, and PIL libraries to extract and process metadata.
# 🧠 Reasoning: Chosen for its efficiency in handling image metadata extraction and compatibility with various image formats.

import os
import xml.etree.ElementTree as ET
from PIL import Image
import json
from datetime import datetime

def extract_metadata(image_path):
    """Extract metadata from an image file, focusing on XMP data."""
    metadata = {}
    
    # Basic file information
    filename = os.path.basename(image_path)
    metadata['filename'] = filename
    metadata['file_size_mb'] = round(os.path.getsize(image_path) / (1024 * 1024), 2)
    metadata['file_extension'] = os.path.splitext(filename)[1].lower()
    metadata['path'] = image_path
    
    # Basic image properties and EXIF data using PIL
    try:
        img = Image.open(image_path)
        metadata['width'] = img.width
        metadata['height'] = img.height
        metadata['aspect_ratio'] = round(img.width / img.height, 2) if img.height > 0 else 0
        metadata['resolution'] = f"{img.width}x{img.height}"
        metadata['image_format'] = img.format
        metadata['color_mode'] = img.mode
        
        # Extract EXIF data
        exif_data = extract_exif(img)
        if exif_data:
            # Update metadata with EXIF data
            metadata.update(exif_data)
            
        img.close()
    except Exception as e:
        print(f"Error getting basic image info from {image_path}: {e}")
    
    # Extract XMP Data
    try:
        # Try to find embedded XMP in the image file
        xmp_data = None
        with open(image_path, 'rb') as f:
            data = f.read()
        
        # Look for embedded XMP
        if b'<x:xmpmeta' in data and b'</x:xmpmeta>' in data:
            start_idx = data.find(b'<x:xmpmeta')
            end_idx = data.find(b'</x:xmpmeta>') + len(b'</x:xmpmeta>')
            xmp_data = data[start_idx:end_idx].decode('utf-8', errors='ignore')
        
        # If not found, check for a sidecar XMP file
        if not xmp_data:
            sidecar_path = os.path.splitext(image_path)[0] + '.xmp'
            if os.path.exists(sidecar_path):
                with open(sidecar_path, 'rb') as f:
                    sidecar_data = f.read()
                
                if b'<x:xmpmeta' in sidecar_data:
                    start_idx = sidecar_data.find(b'<x:xmpmeta')
                    end_idx = sidecar_data.find(b'</x:xmpmeta>') + len(b'</x:xmpmeta>')
                    xmp_data = sidecar_data[start_idx:end_idx].decode('utf-8', errors='ignore')
                else:
                    xmp_data = sidecar_data.decode('utf-8', errors='ignore')
        
        # Process XMP data if found
        if xmp_data:
            try:
                root = ET.fromstring(xmp_data)
                
                # Define common XMP namespaces
                namespaces = {
                    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                    'dc': 'http://purl.org/dc/elements/1.1/',
                    'xmp': 'http://ns.adobe.com/xap/1.0/',
                    'lr': 'http://ns.adobe.com/lightroom/1.0/',
                    'exif': 'http://ns.adobe.com/exif/1.0/',
                    'tiff': 'http://ns.adobe.com/tiff/1.0/',
                    'photoshop': 'http://ns.adobe.com/photoshop/1.0/',
                    'crs': 'http://ns.adobe.com/camera-raw-settings/1.0/',
                    'x': 'adobe:ns:meta/',
                    'aux': 'http://ns.adobe.com/exif/1.0/aux/',
                    'MicrosoftPhoto': 'http://ns.microsoft.com/photo/1.0/',
                    'cipa': 'http://cipa.jp/exif/1.0/'
                }
                
                # Map XMP fields to desired output fields - more comprehensive mapping
                field_mapping = {
                    # EXIF fields
                    '{http://ns.adobe.com/exif/1.0/}FNumber': 'aperture',
                    '{http://ns.adobe.com/exif/1.0/}ApertureValue': 'aperture',
                    '{http://ns.adobe.com/exif/1.0/}Make': 'camera_make',
                    '{http://ns.adobe.com/exif/1.0/}Model': 'camera_model',
                    '{http://ns.adobe.com/exif/1.0/}DateTimeOriginal': 'date_taken',
                    '{http://ns.adobe.com/exif/1.0/}DateTime': 'date_taken',
                    '{http://ns.adobe.com/exif/1.0/}CreateDate': 'date_taken',
                    '{http://ns.adobe.com/exif/1.0/}ExposureProgram': 'exposure_program',
                    '{http://ns.adobe.com/exif/1.0/}Flash': 'flash_fired',
                    '{http://ns.adobe.com/exif/1.0/}FocalLength': 'focal_length',
                    '{http://ns.adobe.com/exif/1.0/}FocalLengthIn35mmFilm': 'focal_length',
                    '{http://ns.adobe.com/exif/1.0/}ISO': 'iso',
                    '{http://ns.adobe.com/exif/1.0/}ISOSpeedRatings': 'iso',
                    '{http://ns.adobe.com/exif/1.0/}ISOSpeedRating': 'iso',
                    '{http://ns.adobe.com/exif/1.0/}ExposureTime': 'shutter_speed',
                    '{http://ns.adobe.com/exif/1.0/}ShutterSpeedValue': 'shutter_speed',
                    '{http://ns.adobe.com/exif/1.0/}WhiteBalance': 'white_balance',
                    '{http://ns.adobe.com/exif/1.0/aux}Lens': 'lens_model',
                    '{http://ns.adobe.com/exif/1.0/}LensModel': 'lens_model',
                    '{http://cipa.jp/exif/1.0/}LensModel': 'lens_model',
                    '{http://ns.adobe.com/exif/1.0/}LensInfo': 'lens_info',
                    '{http://ns.adobe.com/exif/1.0/}LensMake': 'lens_make',
                    '{http://ns.adobe.com/exif/1.0/aux}LensID': 'lens_id',
                    '{http://ns.adobe.com/exif/1.0/aux}LensSerialNumber': 'lens_serial',
                    '{http://ns.adobe.com/exif/1.0/}BodySerialNumber': 'camera_serial',
                    
                    # TIFF fields
                    '{http://ns.adobe.com/tiff/1.0/}Make': 'camera_make',
                    '{http://ns.adobe.com/tiff/1.0/}Model': 'camera_model',
                    
                    # XMP fields
                    '{http://ns.adobe.com/xap/1.0/}CreateDate': 'date_taken',
                    '{http://ns.adobe.com/xap/1.0/}ModifyDate': 'date_modified',
                    '{http://ns.adobe.com/xap/1.0/}Make': 'camera_make',
                    '{http://ns.adobe.com/xap/1.0/}Model': 'camera_model',
                    
                    # Microsoft Photo fields
                    '{http://ns.microsoft.com/photo/1.0/}CameraManufacturer': 'camera_make',
                    '{http://ns.microsoft.com/photo/1.0/}CameraModel': 'camera_model',
                    '{http://ns.microsoft.com/photo/1.0/}LensManufacturer': 'lens_make',
                    '{http://ns.microsoft.com/photo/1.0/}LensModel': 'lens_model',
                    
                    # Camera Raw fields
                    '{http://ns.adobe.com/camera-raw-settings/1.0/}WhiteBalance': 'white_balance',
                    '{http://ns.adobe.com/camera-raw-settings/1.0/}Temperature': 'color_temperature',
                    
                    # Photoshop fields
                    '{http://ns.adobe.com/photoshop/1.0/}DateCreated': 'date_taken',
                }
                
                # Process exposure program values
                exposure_program_map = {
                    '0': 'Not Defined',
                    '1': 'Manual',
                    '2': 'Normal',
                    '3': 'Aperture Priority',
                    '4': 'Shutter Priority',
                    '5': 'Creative',
                    '6': 'Action',
                    '7': 'Portrait',
                    '8': 'Landscape'
                }
                
                # Process white balance values
                white_balance_map = {
                    '0': 'Auto',
                    '1': 'Manual'
                }
                
                # Process flash fired values
                flash_map = {
                    '0': 'False',
                    '1': 'True',
                    '9': 'True',  # Flash fired, compulsory flash mode
                    '16': 'False',  # Flash did not fire, compulsory flash mode
                }
                
                # Extract all XMP properties
                for description in root.findall('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description'):
                    for key, value in description.attrib.items():
                        if '}' in key:  # Namespace is present
                            # Skip certain attributes
                            if key.endswith('}about'):
                                continue
                                
                            # Map to desired field name if available
                            field_name = field_mapping.get(key, None)
                            if field_name:
                                # Apply formatting to specific fields
                                if field_name == 'aperture' and value:
                                    try:
                                        # Format aperture as f/N.N
                                        f_value = float(value)
                                        metadata[field_name] = f"f/{f_value:.1f}"
                                    except:
                                        metadata[field_name] = value
                                elif field_name == 'focal_length' and value:
                                    # Add mm to focal length
                                    if 'mm' not in value:
                                        metadata[field_name] = f"{value}mm"
                                    else:
                                        metadata[field_name] = value
                                elif field_name == 'shutter_speed' and value:
                                    try:
                                        # Format shutter speed as seconds
                                        speed = float(value)
                                        metadata[field_name] = f"{speed:.5f}s"
                                    except:
                                        metadata[field_name] = value
                                elif field_name == 'exposure_program' and value:
                                    metadata[field_name] = exposure_program_map.get(value, value)
                                elif field_name == 'white_balance' and value:
                                    metadata[field_name] = white_balance_map.get(value, value)
                                elif field_name == 'flash_fired' and value:
                                    metadata[field_name] = flash_map.get(value, value)
                                elif field_name == 'date_taken' and value:
                                    # Try to format date consistently
                                    try:
                                        # Parse various date formats
                                        for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y:%m:%d %H:%M:%S'):
                                            try:
                                                dt = datetime.strptime(value.split('+')[0].split('.')[0], fmt)
                                                metadata[field_name] = dt.strftime('%Y-%m-%d %H:%M:%S')
                                                break
                                            except ValueError:
                                                continue
                                    except:
                                        metadata[field_name] = value
                                else:
                                    metadata[field_name] = value
                            else:
                                # Store unknown fields temporarily for diagnostic purposes
                                # We'll clean these up later
                                short_key = key.split('}')[-1]
                                if short_key in ('Make', 'Model', 'LensModel', 'LensMake', 'LensInfo', 'LensID', 
                                                'FNumber', 'FocalLength', 'ISOSpeedRatings', 'ISO', 'ExposureTime', 
                                                'Flash', 'WhiteBalance', 'ExposureProgram', 'BodySerialNumber', 
                                                'LensSerialNumber', 'CameraSerialNumber'):
                                    metadata[short_key] = value
                    
                    # Process child elements
                    for child in description:
                        tag = child.tag
                        if '}' in tag:
                            ns, local_name = tag.split('}', 1)
                            ns = ns.strip('{')
                            
                            # Map to desired field name if available
                            full_tag = '{' + ns + '}' + local_name
                            field_name = field_mapping.get(full_tag, local_name)
                            
                            # Handle different types of elements
                            if child.text and child.text.strip():
                                if field_name in ('camera_make', 'camera_model', 'lens_model', 
                                                'aperture', 'focal_length', 'iso', 'shutter_speed',
                                                'flash_fired', 'white_balance', 'exposure_program',
                                                'date_taken'):
                                    
                                    # Apply the same formatting as above
                                    if field_name == 'aperture' and child.text:
                                        try:
                                            f_value = float(child.text)
                                            metadata[field_name] = f"f/{f_value:.1f}"
                                        except:
                                            metadata[field_name] = child.text.strip()
                                    elif field_name == 'focal_length' and child.text:
                                        if 'mm' not in child.text:
                                            metadata[field_name] = f"{child.text.strip()}mm"
                                        else:
                                            metadata[field_name] = child.text.strip()
                                    elif field_name == 'date_taken' and child.text:
                                        try:
                                            for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y:%m:%d %H:%M:%S'):
                                                try:
                                                    dt = datetime.strptime(child.text.split('+')[0].split('.')[0], fmt)
                                                    metadata[field_name] = dt.strftime('%Y-%m-%d %H:%M:%S')
                                                    break
                                                except ValueError:
                                                    continue
                                        except:
                                            metadata[field_name] = child.text.strip()
                                    else:
                                        metadata[field_name] = child.text.strip()
                                else:
                                    metadata[field_name] = child.text.strip()
                            elif len(list(child)) > 0:  # Has child elements (like Bag or Seq)
                                values = []
                                for item in child.findall('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li'):
                                    if item.text:
                                        values.append(item.text.strip())
                                if values:
                                    metadata[field_name] = values
                
                # Extract tags/subject
                tags = []
                
                # Look for dc:subject tags
                for subject in root.findall(".//{http://purl.org/dc/elements/1.1/}subject"):
                    for item in subject.findall(".//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li"):
                        if item.text:
                            # Split by semicolon and strip whitespace
                            for tag in item.text.split(';'):
                                tag = tag.strip()
                                if tag:
                                    tags.append(tag)
                
                # Look for hierarchicalSubject tags
                for subject in root.findall(".//{http://ns.adobe.com/lightroom/1.0/}hierarchicalSubject"):
                    for item in subject.findall(".//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li"):
                        if item.text:
                            # Split by semicolon and strip whitespace
                            for tag in item.text.split(';'):
                                tag = tag.strip()
                                if tag:
                                    tags.append(tag)
                
                # Deduplicate tags
                if tags:
                    unique_tags = []
                    for tag in tags:
                        if tag not in unique_tags:
                            unique_tags.append(tag)
                    metadata['tags'] = unique_tags
                    metadata['subject'] = unique_tags
                
                # Map any temporary fields to their proper names
                field_name_map = {
                    'Make': 'camera_make',
                    'Model': 'camera_model',
                    'CameraManufacturer': 'camera_make',
                    'CameraModel': 'camera_model',
                    'LensModel': 'lens_model',
                    'LensMake': 'lens_make',
                    'LensInfo': 'lens_info',
                    'LensID': 'lens_id',
                    'BodySerialNumber': 'camera_serial',
                    'CameraSerialNumber': 'camera_serial',
                    'LensSerialNumber': 'lens_serial',
                    'FNumber': 'aperture',
                    'FocalLength': 'focal_length',
                    'ISOSpeedRatings': 'iso', 
                    'ISO': 'iso',
                    'ExposureTime': 'shutter_speed',
                    'Flash': 'flash_fired',
                    'WhiteBalance': 'white_balance',
                    'ExposureProgram': 'exposure_program'
                }
                
                for temp_key, proper_key in field_name_map.items():
                    if temp_key in metadata and proper_key not in metadata:
                        value = metadata[temp_key]
                        
                        # Apply formatting to specific fields
                        if proper_key == 'aperture' and value:
                            try:
                                # Format aperture as f/N.N
                                f_value = float(value)
                                metadata[proper_key] = f"f/{f_value:.1f}"
                            except:
                                metadata[proper_key] = value
                        elif proper_key == 'focal_length' and value:
                            # Add mm to focal length
                            if 'mm' not in value:
                                metadata[proper_key] = f"{value}mm"
                            else:
                                metadata[proper_key] = value
                        elif proper_key == 'shutter_speed' and value:
                            try:
                                # Format shutter speed as seconds
                                speed = float(value)
                                metadata[proper_key] = f"{speed:.5f}s"
                            except:
                                metadata[proper_key] = value
                        elif proper_key == 'exposure_program' and value:
                            metadata[proper_key] = exposure_program_map.get(value, value)
                        elif proper_key == 'white_balance' and value:
                            metadata[proper_key] = white_balance_map.get(value, value)
                        elif proper_key == 'flash_fired' and value:
                            metadata[proper_key] = flash_map.get(value, value)
                        else:
                            metadata[proper_key] = value
                        
                        # Remove temporary key
                        del metadata[temp_key]
            
                # Clean up and format camera and lens information
                _format_camera_lens_info(metadata)
            
            except ET.ParseError as e:
                print(f"Error parsing XMP data from {image_path}: {e}")
            except Exception as e:
                print(f"Error processing XMP data from {image_path}: {e}")
    
    except Exception as e:
        print(f"Error reading file {image_path}: {e}")
    
    # Remove unwanted fields
    fields_to_remove = ['xmp']  # Keep 'Keywords'
    for field in list(metadata.keys()):
        if field in fields_to_remove and (not metadata[field] or metadata[field] == []):
            del metadata[field]
        # Convert any remaining lists to semicolon-separated strings
        if isinstance(metadata[field], list):
            metadata[field] = "; ".join(str(item) for item in metadata[field])
    
    return metadata

def extract_exif(img):
    """Extract EXIF metadata from PIL Image object"""
    exif_data = {}
    
    # Define EXIF tag mappings - standard tags
    exif_tags = {
        0x010F: 'camera_make',         # Make
        0x0110: 'camera_model',        # Model
        0x0112: 'orientation',         # Orientation
        0x829A: 'shutter_speed_raw',   # ExposureTime 
        0x829D: 'f_number_raw',        # FNumber
        0x8827: 'iso',                 # ISOSpeedRatings
        0x9003: 'date_taken',          # DateTimeOriginal
        0x9004: 'date_digitized',      # DateTimeDigitized
        0x920A: 'focal_length_raw',    # FocalLength
        0xA002: 'width',               # ExifImageWidth
        0xA003: 'height',              # ExifImageHeight
        0xA405: 'focal_length_35mm',   # FocalLengthIn35mmFilm
        0xA406: 'scene_type',          # SceneCaptureType
        0xA408: 'contrast',            # Contrast
        0xA409: 'saturation',          # Saturation
        0xA40A: 'sharpness',           # Sharpness
        0x8822: 'exposure_program',    # ExposureProgram
        0x9202: 'aperture_value',      # ApertureValue
        0x9204: 'exposure_bias',       # ExposureBiasValue
        0x9207: 'metering_mode',       # MeteringMode
        0x9209: 'flash',               # Flash
        0xA431: 'serial_number',       # BodySerialNumber
        0xA433: 'lens_make',           # LensMake
        0xA434: 'lens_model',          # LensModel
        0xA435: 'lens_serial',         # LensSerialNumber
    }
    
    # Try to get EXIF data
    try:
        exif = img._getexif()
        if exif:
            for tag, value in exif.items():
                if tag in exif_tags:
                    field_name = exif_tags[tag]
                    
                    # Format certain values
                    if field_name == 'shutter_speed_raw' and value:
                        try:
                            # Convert to fraction if needed and format
                            if isinstance(value, tuple) and len(value) == 2:
                                speed = value[0] / value[1]
                            else:
                                speed = float(value)
                            # Format shutter speed as seconds or fraction
                            if speed >= 1:
                                exif_data['shutter_speed'] = f"{speed:.1f}s"
                            else:
                                denominator = int(1/speed)
                                exif_data['shutter_speed'] = f"1/{denominator}s"
                        except:
                            exif_data['shutter_speed'] = str(value)
                    
                    elif field_name == 'f_number_raw' and value:
                        try:
                            # Handle different formats (float or rational)
                            if isinstance(value, tuple) and len(value) == 2:
                                f_value = value[0] / value[1]
                            else:
                                f_value = float(value)
                            exif_data['aperture'] = f"f/{f_value:.1f}"
                        except:
                            exif_data['aperture'] = str(value)
                    
                    elif field_name == 'focal_length_raw' and value:
                        try:
                            # Handle different formats
                            if isinstance(value, tuple) and len(value) == 2:
                                focal = value[0] / value[1]
                            else:
                                focal = float(value)
                            exif_data['focal_length'] = f"{focal:.1f}mm"
                        except:
                            exif_data['focal_length'] = str(value)
                    
                    elif field_name == 'flash' and value is not None:
                        # Map flash values
                        flash_map = {
                            0: 'No Flash',
                            1: 'Flash Fired',
                            5: 'Flash Fired, Return not detected',
                            7: 'Flash Fired, Return detected',
                            9: 'Flash Fired, Compulsory',
                            16: 'No Flash, Compulsory',
                            24: 'No Flash, Auto',
                            25: 'Flash Fired, Auto',
                            29: 'Flash Fired, Auto, Return not detected',
                            31: 'Flash Fired, Auto, Return detected',
                        }
                        exif_data['flash_fired'] = flash_map.get(value, str(value))
                    
                    elif field_name == 'exposure_program' and value is not None:
                        # Map exposure program values
                        program_map = {
                            0: 'Not Defined',
                            1: 'Manual',
                            2: 'Normal',
                            3: 'Aperture Priority',
                            4: 'Shutter Priority',
                            5: 'Creative',
                            6: 'Action',
                            7: 'Portrait',
                            8: 'Landscape',
                        }
                        exif_data['exposure_program'] = program_map.get(value, str(value))
                    
                    elif field_name == 'date_taken' and value:
                        # Format date consistently
                        try:
                            dt = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                            exif_data[field_name] = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            exif_data[field_name] = value
                    
                    else:
                        # Store other values as-is
                        exif_data[field_name] = value
    except Exception as e:
        print(f"Error extracting EXIF data: {e}")
    
    return exif_data

def save_metadata_json(image_path, output_dir=None):
    """Extract metadata from an image and save it as JSON"""
    metadata = extract_metadata(image_path)
    
    if output_dir is None:
        output_dir = os.path.dirname(image_path)
    
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    json_path = os.path.join(output_dir, f"{base_name}_metadata.json")
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    return json_path

def _format_camera_lens_info(metadata):
    """Format and clean camera and lens information"""
    # Ensure consistent naming for camera make/model fields
    if 'camera_make' in metadata and 'camera_model' in metadata:
        # Remove camera make from model if it's duplicated
        if metadata['camera_model'].startswith(metadata['camera_make']):
            metadata['camera_model'] = metadata['camera_model'][len(metadata['camera_make']):].strip()
        
        # If camera model is empty after cleaning, use original value
        if not metadata['camera_model']:
            metadata['camera_model'] = metadata.get('Model', '')
    
    # Clean lens model information
    if 'lens_model' in metadata:
        # Remove lens make from model if present and make exists
        if 'lens_make' in metadata and metadata['lens_model'].startswith(metadata['lens_make']):
            metadata['lens_model'] = metadata['lens_model'][len(metadata['lens_make']):].strip()
        
        # Format lens focal length and aperture if it's in the model string
        # Example: "24.0-70.0 mm f/2.8" -> clean it up if needed
        if 'mm' in metadata['lens_model'].lower() and 'f/' in metadata['lens_model'].lower():
            pass  # Keep as is, already well formatted 