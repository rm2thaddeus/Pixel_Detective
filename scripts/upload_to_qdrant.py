#!/usr/bin/env python3
"""
Script to upload existing embeddings and metadata to Qdrant database.
"""

import os
import sys
import numpy as np
import pandas as pd

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.qdrant_connector import QdrantDB

def upload_existing_data_to_qdrant(embeddings_path, metadata_path, collection_name="image_collection"):
    """
    Upload existing embeddings and metadata to Qdrant.
    
    Args:
        embeddings_path: Path to the embeddings .npy file
        metadata_path: Path to the metadata .csv file
        collection_name: Name of the Qdrant collection
    """
    print(f"Loading embeddings from: {embeddings_path}")
    print(f"Loading metadata from: {metadata_path}")
    
    # Load existing data
    try:
        embeddings = np.load(embeddings_path)
        metadata_df = pd.read_csv(metadata_path)
        print(f"Loaded {len(embeddings)} embeddings and {len(metadata_df)} metadata records")
        
        if len(embeddings) != len(metadata_df):
            print(f"WARNING: Mismatch between embeddings ({len(embeddings)}) and metadata ({len(metadata_df)}) counts")
            min_length = min(len(embeddings), len(metadata_df))
            embeddings = embeddings[:min_length]
            metadata_df = metadata_df.iloc[:min_length]
            print(f"Using first {min_length} records")
        
    except Exception as e:
        print(f"Error loading data: {e}")
        return False
    
    # Initialize Qdrant
    try:
        print("Connecting to Qdrant...")
        qdrant_db = QdrantDB(collection_name=collection_name, host="localhost", port=6333)
        print("Connected to Qdrant successfully!")
        
        # Check current collection info
        info = qdrant_db.get_collection_info()
        if info:
            print(f"Collection '{collection_name}' info: {info.points_count} points")
        
    except Exception as e:
        print(f"Error connecting to Qdrant: {e}")
        return False
    
    # Prepare data for upload
    try:
        print("Preparing data for upload...")
        
        # Convert metadata DataFrame to list of dictionaries
        metadata_list = []
        image_paths = []
        
        for idx, row in metadata_df.iterrows():
            # Convert row to dictionary and clean up
            meta_dict = row.to_dict()
            
            # Ensure we have a path field
            if 'path' in meta_dict:
                path = meta_dict['path']
            else:
                # Fallback - try to construct path or use filename
                path = meta_dict.get('filename', f'image_{idx}.jpg')
            
            image_paths.append(path)
            
            # Clean up NaN values
            clean_meta = {}
            for key, value in meta_dict.items():
                if pd.notna(value):  # Only include non-NaN values
                    if isinstance(value, (int, float, str, bool)):
                        clean_meta[key] = value
                    else:
                        clean_meta[key] = str(value)
            
            metadata_list.append(clean_meta)
        
        print(f"Prepared {len(image_paths)} image paths and metadata records")
        
    except Exception as e:
        print(f"Error preparing data: {e}")
        return False
    
    # Upload to Qdrant in batches
    try:
        print("Uploading to Qdrant...")
        batch_size = 32
        
        success_count, failure_count = qdrant_db.add_images_batch(
            image_paths=image_paths,
            embeddings=embeddings,
            metadata_list=metadata_list,
            batch_size=batch_size
        )
        
        print(f"\nUpload completed!")
        print(f"Success: {success_count} images")
        print(f"Failures: {failure_count} images")
        
        # Check final collection info
        info = qdrant_db.get_collection_info()
        if info:
            print(f"Final collection '{collection_name}' info: {info.points_count} points")
        
        return success_count > 0
        
    except Exception as e:
        print(f"Error uploading to Qdrant: {e}")
        return False

def main():
    """Main function to run the upload process."""
    # Default paths
    base_dir = "Library Test"
    embeddings_path = os.path.join(base_dir, "embeddings.npy")
    metadata_path = os.path.join(base_dir, "metadata.csv")
    
    # Check if files exist
    if not os.path.exists(embeddings_path):
        print(f"Error: Embeddings file not found at {embeddings_path}")
        return False
    
    if not os.path.exists(metadata_path):
        print(f"Error: Metadata file not found at {metadata_path}")
        return False
    
    # Run the upload
    print("Starting upload to Qdrant...")
    print("="*50)
    
    success = upload_existing_data_to_qdrant(embeddings_path, metadata_path)
    
    print("="*50)
    if success:
        print("✅ Upload completed successfully!")
    else:
        print("❌ Upload failed!")
    
    return success

if __name__ == "__main__":
    main() 