"""
Database operations for the Pixel Detective app.
"""
import os
import numpy as np
import pandas as pd
import streamlit as st
from utils.logger import logger
from config import DB_EMBEDDINGS_FILE, DB_METADATA_FILE
from metadata_extractor import extract_metadata
from models.clip_model import process_image
from models.blip_model import generate_caption
from utils.image_utils import get_image_list

def database_exists(folder_path):
    """
    Check if a database exists in the specified folder.
    
    Args:
        folder_path (str): Path to the folder to check.
        
    Returns:
        bool: True if the database exists, False otherwise.
    """
    db_embeddings_path = os.path.join(folder_path, DB_EMBEDDINGS_FILE)
    db_metadata_path = os.path.join(folder_path, DB_METADATA_FILE)
    result = os.path.exists(db_embeddings_path) and os.path.exists(db_metadata_path)
    
    if result:
        logger.info(f"Database found in {folder_path}")
    else:
        logger.info(f"Database not found in {folder_path}")
    
    return result

def save_database(folder_path, embeddings, metadata_df):
    """
    Save the database to the specified folder.
    
    Args:
        folder_path (str): Path to the folder to save the database.
        embeddings (numpy.ndarray): Image embeddings.
        metadata_df (pandas.DataFrame): Metadata for the images.
        
    Returns:
        bool: True if the database was saved successfully, False otherwise.
    """
    try:
        # Save embeddings as numpy array
        embeddings_path = os.path.join(folder_path, DB_EMBEDDINGS_FILE)
        np.save(embeddings_path, embeddings)
        
        # Clean metadata to avoid recursion issues
        clean_metadata = metadata_df.copy()
        
        # Ensure path and filename columns exist
        if 'path' not in clean_metadata.columns:
            clean_metadata['path'] = [str(img_path) for img_path in st.session_state.image_files]
        if 'filename' not in clean_metadata.columns:
            clean_metadata['filename'] = [os.path.basename(p) for p in clean_metadata['path']]
        
        # Convert complex objects to strings to avoid serialization issues
        for column in clean_metadata.columns:
            if clean_metadata[column].apply(lambda x: isinstance(x, (dict, list))).any():
                clean_metadata[column] = clean_metadata[column].apply(lambda x: str(x) if isinstance(x, (dict, list)) else x)
        
        # Save metadata as CSV instead of JSON for better compatibility
        metadata_path = os.path.join(folder_path, DB_METADATA_FILE)
        clean_metadata.to_csv(metadata_path, index=False)
        
        logger.info(f"Database saved to {folder_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving database: {e}")
        return False

def load_database(db_folder):
    """
    Load the database from the specified folder.
    
    Args:
        db_folder (str): Path to the folder containing the database.
        
    Returns:
        bool: True if the database was loaded successfully, False otherwise.
    """
    embeddings_path = os.path.join(db_folder, DB_EMBEDDINGS_FILE)
    metadata_path = os.path.join(db_folder, DB_METADATA_FILE)
    if os.path.exists(embeddings_path) and os.path.exists(metadata_path):
        try:
            st.session_state.embeddings = np.load(embeddings_path)
            st.session_state.images_data = pd.read_csv(metadata_path)
            st.session_state.database_built = True
            
            # Also set image_files from the loaded paths
            if 'path' in st.session_state.images_data.columns:
                st.session_state.image_files = st.session_state.images_data['path'].tolist()
            
            logger.info(f"Database loaded successfully from {db_folder}")
            st.success("Database loaded successfully!")
            return True
        except Exception as e:
            logger.error(f"Error loading database: {e}")
            return False
    return False

def build_database(db_folder, image_list):
    """
    Build a new database from a list of images.
    This extracts each image's metadata—including tags—and then saves embeddings and metadata.
    """
    if not image_list:
        logger.error("No images found to build database")
        st.error("No images found in the specified folder.")
        return False
    
    try:
        # Set total images for progress tracking
        st.session_state.total_images = len(image_list)
        st.session_state.image_files = image_list
        
        embeddings = []        # To store image embeddings
        metadata_records = []  # To store metadata dictionaries
        
        for i, image_path in enumerate(image_list):
            # Update progress in session state
            st.session_state.current_image_index = i + 1
            
            # Process the image and compute its embedding
            embedding = process_image(image_path)
            embeddings.append(embedding)
            
            # Extract metadata for the image
            try:
                metadata = extract_metadata(image_path)
                
                # Generate BLIP caption for the image
                caption = generate_caption(image_path)
                
                # Add the caption to metadata
                metadata["caption"] = caption
                
                # Always include the caption in Keywords
                if "Keywords" not in metadata or not metadata["Keywords"]:
                    metadata["Keywords"] = [caption]
                else:
                    # If Keywords exists but doesn't contain the caption, add it
                    if isinstance(metadata["Keywords"], list):
                        if caption not in metadata["Keywords"]:
                            metadata["Keywords"].append(caption)
                    else:
                        # If Keywords is not a list, convert it to a list and add the caption
                        metadata["Keywords"] = [metadata["Keywords"], caption]
                
                # Look for the "tags" field and, if not found, fallback to "Keywords"
                if "tags" not in metadata or not metadata["tags"]:
                    metadata["tags"] = metadata.get("Keywords", [])
            except Exception as e:
                logger.error(f"Error extracting metadata from {image_path}: {e}")
                metadata = {"tags": [], "caption": f"Caption for {os.path.basename(image_path)}"}
            
            metadata["path"] = image_path  # Record the image path
            metadata["filename"] = os.path.basename(image_path)
            metadata_records.append(metadata)
            
            # Optionally update progress every 10 images
            if i % 10 == 0 and hasattr(st, 'rerun'):
                st.rerun()
        
        st.session_state.db_building_complete = True
        
        # Convert embeddings to a numpy array and metadata records to a DataFrame
        embeddings_np = np.array(embeddings)
        metadata_df = pd.DataFrame(metadata_records)
        
        # Save the database
        if save_database(db_folder, embeddings_np, metadata_df):
            st.session_state.embeddings = embeddings_np
            st.session_state.images_data = metadata_df
            st.session_state.database_built = True
            st.success("Database built and saved successfully!")
            return True
        else:
            st.error("Failed to save database.")
            return False
    except Exception as e:
        logger.error(f"Error building database: {e}")
        st.error(f"Error building database: {e}")
        return False

def append_images_to_database(db_folder, new_folder):
    """
    Append new images from `new_folder` to the existing database in `db_folder`.
    Only processes images that are not already included.
    """
    # Load existing database
    embeddings_path = os.path.join(db_folder, DB_EMBEDDINGS_FILE)
    metadata_path = os.path.join(db_folder, DB_METADATA_FILE)
    if not (os.path.exists(embeddings_path) and os.path.exists(metadata_path)):
        st.error("No existing database found in the target folder.")
        return False

    existing_embeddings = np.load(embeddings_path)
    existing_metadata_df = pd.read_csv(metadata_path)
    existing_image_files = set(existing_metadata_df['path'].tolist())

    # Scan new folder (recursively, using our updated get_image_list)
    new_images = get_image_list(new_folder)
    # Filter out images already present
    new_images = [img for img in new_images if img not in existing_image_files]
    logger.info(f"Found {len(new_images)} new images in {new_folder}")

    if not new_images:
        st.info("No new images found in the new folder.")
        return True

    new_embeddings = []
    new_metadata_records = []

    total_new = len(new_images)
    st.session_state.total_new_images = total_new  # For progress tracking

    for i, image_path in enumerate(new_images):
        st.session_state.current_new_image_index = i+1

        # Process image and compute embedding
        embedding = process_image(image_path)
        new_embeddings.append(embedding)

        # Extract metadata with tags (fall back to Keywords)
        try:
            metadata = extract_metadata(image_path)
            
            # Generate BLIP caption for the image
            caption = generate_caption(image_path)
            
            # Add the caption to metadata
            metadata["caption"] = caption
            
            # Always include the caption in Keywords
            if "Keywords" not in metadata or not metadata["Keywords"]:
                metadata["Keywords"] = [caption]
            else:
                # If Keywords exists but doesn't contain the caption, add it
                if isinstance(metadata["Keywords"], list):
                    if caption not in metadata["Keywords"]:
                        metadata["Keywords"].append(caption)
                else:
                    # If Keywords is not a list, convert it to a list and add the caption
                    metadata["Keywords"] = [metadata["Keywords"], caption]
            
            # Look for the "tags" field and, if not found, fallback to "Keywords"
            if "tags" not in metadata or not metadata["tags"]:
                metadata["tags"] = metadata.get("Keywords", [])
        except Exception as e:
            logger.error(f"Error extracting metadata from {image_path}: {e}")
            metadata = {"tags": [], "caption": f"Caption for {os.path.basename(image_path)}"}

        metadata["path"] = image_path
        metadata["filename"] = os.path.basename(image_path)
        new_metadata_records.append(metadata)

        # Optionally update progress every 10 images
        if i % 10 == 0 and hasattr(st, 'rerun'):
            st.rerun()

    # Combine new data with existing data
    combined_embeddings = np.vstack([existing_embeddings, np.array(new_embeddings)])
    new_metadata_df = pd.DataFrame(new_metadata_records)
    combined_metadata_df = pd.concat([existing_metadata_df, new_metadata_df], ignore_index=True)

    # Save the updated database
    if save_database(db_folder, combined_embeddings, combined_metadata_df):
        st.session_state.embeddings = combined_embeddings
        st.session_state.images_data = combined_metadata_df
        st.session_state.database_built = True
        st.success(f"Added {len(new_images)} new images to the database!")
        return True
    else:
        st.error("Failed to save the updated database.")
        return False 