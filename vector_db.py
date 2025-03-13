# 📂 File Path: /project_root/vector_db.py
# 📌 Purpose: This file manages interactions with the Qdrant vector database for storing and retrieving image embeddings.
# 🔄 Latest Changes: 
#   - Added detailed comments to improve code readability and maintainability
#   - Added batch processing support for efficient GPU memory management
#   - Implemented memory-efficient processing for large image collections
# ⚙️ Key Logic: Utilizes QdrantClient for in-memory vector storage and retrieval, supporting image search operations.
# 🧠 Reasoning: Chosen for its efficient handling of high-dimensional vector data and ease of integration with Python applications.

from qdrant_client import QdrantClient
from qdrant_client.http import models
import os
import json
import numpy as np
import torch
import gc
from tqdm import tqdm
import logging
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QdrantDB:
    def __init__(self, collection_name="image_collection", batch_size=50):
        """
        Initialize a connection to Qdrant vector database.
        
        Args:
            collection_name (str): Name of the collection to use
            batch_size (int): Size of batches for processing images
        """
        # Create a local Qdrant instance
        self.client = QdrantClient(":memory:")  # In-memory storage for simple usage
        self.collection_name = collection_name
        self.batch_size = batch_size
        
        # Store a mapping of image paths to their IDs in the database
        self.image_to_id = {}
        self.id_to_image = {}
        self.metadata_cache = {}
        self.next_id = 0
        
        # Initialize the collection
        self._init_collection()
    
    def _init_collection(self):
        """Initialize the vector collection if it doesn't exist."""
        # CLIP embedding size is 512
        vector_size = 512
        
        # Create collection
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE
            )
        )
    
    def add_image(self, image_path, embedding, metadata=None):
        """
        Adds a single image to the Qdrant database.

        Args:
            image_path (str): The path to the image file.
            embedding (numpy.ndarray): The image embedding vector.
            metadata (dict, optional): Metadata associated with the image. Defaults to None.
        """
        image_id = str(uuid.uuid4())

        if metadata is None:
            metadata = {}

        # Store the mapping of image path to ID
        self.image_to_id[image_path] = image_id
        self.id_to_image[image_id] = image_path
        self.metadata_cache[image_path] = metadata

        # Add metadata about the file itself
        metadata['filename'] = os.path.basename(image_path)
        metadata['path'] = image_path

        # Upsert the point into the collection
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=image_id,
                    vector=embedding.tolist(),
                    payload=metadata
                )
            ]
        )
    
    def add_images_batch(self, image_paths, embeddings, metadata_list=None):
        """
        Add multiple images to the database in a batch.
        
        Args:
            image_paths (list): List of image file paths
            embeddings (list or np.ndarray): List of embeddings or 2D numpy array
            metadata_list (list, optional): List of metadata dictionaries
        """
        if metadata_list is None:
            metadata_list = [None] * len(image_paths)
        
        # Ensure embeddings is a numpy array
        if not isinstance(embeddings, np.ndarray):
            embeddings = np.array(embeddings, dtype=np.float32)
        
        # Normalize embeddings if they're not already normalized
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        valid_indices = norms > 0
        embeddings[valid_indices] = embeddings[valid_indices] / norms[valid_indices]
        
        # Prepare points for batch insertion
        points = []
        for i, (image_path, embedding, metadata) in enumerate(zip(image_paths, embeddings, metadata_list)):
            image_id = self.next_id
            self.next_id += 1
            
            # Process metadata
            clean_metadata = self._process_metadata(metadata, image_path)
            
            # Store mappings
            self.image_to_id[image_path] = image_id
            self.id_to_image[image_id] = image_path
            self.metadata_cache[image_path] = clean_metadata
            
            # Create point
            points.append(
                models.PointStruct(
                    id=image_id,
                    vector=embedding.tolist(),
                    payload=clean_metadata
                )
            )
        
        # Upsert all points in a single batch
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
    
    def _process_metadata(self, metadata, image_path):
        """
        Process metadata to ensure it's serializable and properly formatted.
        
        Args:
            metadata (dict): Metadata dictionary
            image_path (str): Path to the image file
            
        Returns:
            dict: Processed metadata
        """
        if metadata:
            # Filter out non-serializable values
            clean_metadata = {}
            for key, value in metadata.items():
                try:
                    # Test if it can be serialized
                    json.dumps({key: value})
                    clean_metadata[key] = value
                except (TypeError, OverflowError):
                    # Skip non-serializable values or convert them to strings
                    if isinstance(value, (list, dict)):
                        try:
                            # If it's a list of strings (like tags), try to keep it as a list
                            if all(isinstance(item, str) for item in value):
                                clean_metadata[key] = [str(item) for item in value]
                            else:
                                clean_metadata[key] = str(value)
                        except:
                            pass
                    else:
                        try:
                            clean_metadata[key] = str(value)
                        except:
                            pass
            
            # If tags exist in either capitalization, ensure both versions exist
            if 'tags' in clean_metadata and 'Tags' not in clean_metadata:
                clean_metadata['Tags'] = clean_metadata['tags']
            elif 'Tags' in clean_metadata and 'tags' not in clean_metadata:
                clean_metadata['tags'] = clean_metadata['Tags']
                
            # If caption exists, ensure it's included in Keywords
            if 'caption' in clean_metadata:
                caption = clean_metadata['caption']
                if 'Keywords' not in clean_metadata or not clean_metadata['Keywords']:
                    clean_metadata['Keywords'] = [caption]
                else:
                    # If Keywords exists but doesn't contain the caption, add it
                    if isinstance(clean_metadata['Keywords'], list):
                        if caption not in clean_metadata['Keywords']:
                            clean_metadata['Keywords'].append(caption)
                    else:
                        # If Keywords is not a list, convert it to a list and add the caption
                        clean_metadata['Keywords'] = [clean_metadata['Keywords'], caption]
        else:
            clean_metadata = {}
        
        # Add metadata about the file itself
        clean_metadata['filename'] = os.path.basename(image_path)
        clean_metadata['path'] = image_path
        
        return clean_metadata
    
    def process_images_in_batches(self, image_paths, embedding_function, metadata_function=None, batch_size=None):
        """
        Process a list of images in batches to manage GPU memory efficiently.
        
        Args:
            image_paths (list): List of image file paths
            embedding_function (callable): Function to generate embeddings for images
            metadata_function (callable, optional): Function to extract metadata for images
            batch_size (int, optional): Size of batches, defaults to self.batch_size
            
        Returns:
            tuple: (embeddings, metadata_list)
        """
        if batch_size is None:
            batch_size = self.batch_size
        
        total_images = len(image_paths)
        all_embeddings = []
        all_metadata = []
        
        # Process images in batches
        for i in range(0, total_images, batch_size):
            batch_paths = image_paths[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(total_images-1)//batch_size + 1} ({len(batch_paths)} images)")
            
            # Process all images in the batch at once for embeddings
            batch_embeddings = []
            try:
                # Try to process entire batch at once if embedding_function supports it
                if hasattr(embedding_function, 'process_batch'):
                    batch_embeddings = embedding_function.process_batch(batch_paths)
                else:
                    # Fall back to individual processing
                    for path in batch_paths:
                        embedding = embedding_function(path)
                        batch_embeddings.append(embedding)
            except Exception as e:
                logger.error(f"Error processing batch: {e}")
                # Fall back to individual processing on error
                batch_embeddings = []
                for path in batch_paths:
                    try:
                        embedding = embedding_function(path)
                        batch_embeddings.append(embedding)
                    except Exception as e:
                        logger.error(f"Error processing image {path}: {e}")
                        # Use zero vector as fallback
                        batch_embeddings.append(np.zeros(512, dtype=np.float32))
            
            # Extract metadata if a function is provided
            batch_metadata = []
            if metadata_function:
                for path in batch_paths:
                    try:
                        metadata = metadata_function(path)
                        batch_metadata.append(metadata)
                    except Exception as e:
                        logger.error(f"Error extracting metadata for {path}: {e}")
                        batch_metadata.append({})
            else:
                batch_metadata = [None] * len(batch_paths)
            
            # Add the batch to the database
            self.add_images_batch(batch_paths, batch_embeddings, batch_metadata)
            
            # Extend the full lists
            all_embeddings.extend(batch_embeddings)
            all_metadata.extend(batch_metadata)
            
            # Only clean up if necessary
            if GPU_MEMORY_EFFICIENT and i + batch_size < total_images:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
        
        return np.array(all_embeddings), all_metadata
    
    def search_by_vector(self, query_vector, limit=5):
        """
        Search for similar images using a query vector.
        
        Args:
            query_vector (np.ndarray): Query embedding
            limit (int, optional): Maximum number of results to return
            
        Returns:
            List of tuples (image_path, score)
        """
        # Ensure query vector is a numpy array
        if not isinstance(query_vector, np.ndarray):
            query_vector = np.array(query_vector, dtype=np.float32)
        
        # Normalize the query vector if it's not already normalized
        norm = np.linalg.norm(query_vector)
        if norm > 0:
            query_vector = query_vector / norm
        
        # Search for similar vectors
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector.tolist(),
            limit=limit
        )
        
        # Convert results to (image_path, score) format
        results = []
        for hit in search_result:
            image_id = hit.id
            if image_id in self.id_to_image:
                image_path = self.id_to_image[image_id]
                results.append((image_path, hit.score))
        
        return results
    
    def get_metadata(self, image_path):
        """
        Get metadata for an image.
        
        Args:
            image_path (str): Path to the image
            
        Returns:
            dict: Metadata for the image
        """
        if image_path in self.metadata_cache:
            return self.metadata_cache[image_path]
        
        if image_path in self.image_to_id:
            image_id = self.image_to_id[image_path]
            response = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[image_id]
            )
            if response and len(response) > 0:
                metadata = response[0].payload
                self.metadata_cache[image_path] = metadata
                return metadata
        
        return None

# Function to append new images to an existing database
def append_images_to_database(db_folder, new_folder, batch_size=50):
    """
    Append new images from a folder to an existing database.
    
    Args:
        db_folder (str): Path to the folder containing the existing database
        new_folder (str): Path to the folder containing new images to add
        batch_size (int): Size of batches for processing images
    """
    import os
    import glob
    import numpy as np
    import pandas as pd
    from models.clip_model import load_clip_model, process_image, unload_clip_model
    from models.blip_model import load_blip_model, generate_caption, unload_blip_model
    from metadata_extractor import extract_metadata
    from config import DB_EMBEDDINGS_FILE, DB_METADATA_FILE, GPU_MEMORY_EFFICIENT
    
    # Check if database exists
    embeddings_path = os.path.join(db_folder, DB_EMBEDDINGS_FILE)
    metadata_path = os.path.join(db_folder, DB_METADATA_FILE)
    
    if not os.path.exists(embeddings_path) or not os.path.exists(metadata_path):
        logger.error(f"Database not found in {db_folder}")
        return False
    
    # Load existing database
    existing_embeddings = np.load(embeddings_path)
    existing_metadata = pd.read_csv(metadata_path)
    
    # Get list of existing image paths
    existing_paths = set(existing_metadata['path'].tolist())
    
    # Get list of new images
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif']
    new_image_files = []
    
    for ext in image_extensions:
        found = glob.glob(os.path.join(new_folder, ext))
        new_image_files.extend(found)
    
    # Filter out images that are already in the database
    new_image_files = [path for path in new_image_files if path not in existing_paths]
    
    if not new_image_files:
        logger.info("No new images found to add to the database")
        return False
    
    logger.info(f"Found {len(new_image_files)} new images to add to the database")
    
    # Check if both models can fit in GPU memory
    from app import can_load_both_models
    can_fit_both = can_load_both_models()
    
    new_embeddings = []
    new_metadata_records = []
    
    if can_fit_both:
        # Load both models at once
        load_clip_model()
        load_blip_model()
        
        # Process images in batches
        for i in range(0, len(new_image_files), batch_size):
            batch_paths = new_image_files[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(new_image_files)-1)//batch_size + 1} ({len(batch_paths)} images)")
            
            batch_embeddings = []
            batch_metadata = []
            
            for image_path in batch_paths:
                # Process the image and compute its embedding
                embedding = process_image(image_path)
                batch_embeddings.append(embedding)
                
                # Extract metadata for the image
                metadata = extract_metadata(image_path)
                
                # Generate BLIP caption for the image
                caption = generate_caption(image_path, metadata)
                
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
                
                metadata["path"] = image_path  # Record the image path
                batch_metadata.append(metadata)
            
            # Add batch results to the full lists
            new_embeddings.extend(batch_embeddings)
            new_metadata_records.extend(batch_metadata)
            
            # Clean up GPU memory after each batch
            if GPU_MEMORY_EFFICIENT:
                torch.cuda.empty_cache()
                gc.collect()
        
        # Unload models
        unload_clip_model()
        unload_blip_model()
    else:
        # Process in two passes if both models can't fit in memory
        logger.info("Processing images in two passes to manage GPU memory")
        
        # First pass: Generate all CLIP embeddings
        load_clip_model()
        
        # Process images in batches
        for i in range(0, len(new_image_files), batch_size):
            batch_paths = new_image_files[i:i+batch_size]
            logger.info(f"CLIP pass - Batch {i//batch_size + 1}/{(len(new_image_files)-1)//batch_size + 1} ({len(batch_paths)} images)")
            
            batch_embeddings = []
            batch_metadata = []
            
            for image_path in batch_paths:
                # Process the image and compute its embedding
                embedding = process_image(image_path)
                batch_embeddings.append(embedding)
                
                # Extract metadata for the image (doesn't require GPU)
                metadata = extract_metadata(image_path)
                metadata["path"] = image_path  # Record the image path
                batch_metadata.append(metadata)
            
            # Add batch results to the full lists
            new_embeddings.extend(batch_embeddings)
            new_metadata_records.extend(batch_metadata)
            
            # Clean up GPU memory after each batch
            if GPU_MEMORY_EFFICIENT:
                torch.cuda.empty_cache()
                gc.collect()
        
        # Unload CLIP model
        unload_clip_model()
        
        # Second pass: Generate all BLIP captions
        load_blip_model()
        
        # Process images in batches
        for i in range(0, len(new_image_files), batch_size):
            batch_paths = new_image_files[i:i+batch_size]
            batch_metadata = new_metadata_records[i:i+batch_size]
            
            logger.info(f"BLIP pass - Batch {i//batch_size + 1}/{(len(new_image_files)-1)//batch_size + 1} ({len(batch_paths)} images)")
            
            for j, (image_path, metadata) in enumerate(zip(batch_paths, batch_metadata)):
                # Generate BLIP caption for the image
                caption = generate_caption(image_path, metadata)
                
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
            
            # Clean up GPU memory after each batch
            if GPU_MEMORY_EFFICIENT and i > 0 and i % batch_size == 0:
                torch.cuda.empty_cache()
                gc.collect()
        
        # Unload BLIP model
        unload_blip_model()
    
    # Convert new embeddings to numpy array
    new_embeddings_array = np.array(new_embeddings)
    
    # Combine with existing embeddings
    combined_embeddings = np.vstack([existing_embeddings, new_embeddings_array])
    
    # Convert new metadata records to DataFrame
    new_metadata_df = pd.DataFrame(new_metadata_records)
    
    # Combine with existing metadata
    combined_metadata = pd.concat([existing_metadata, new_metadata_df], ignore_index=True)
    
    # Save combined data
    np.save(embeddings_path, combined_embeddings)
    combined_metadata.to_csv(metadata_path, index=False)
    
    logger.info(f"Successfully added {len(new_image_files)} new images to the database")
    return True 