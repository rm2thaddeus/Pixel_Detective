# 📂 File Path: /project_root/vector_db.py
# 📌 Purpose: This file manages interactions with the Qdrant vector database for storing and retrieving image embeddings.
# 🔄 Latest Changes: Added detailed comments to improve code readability and maintainability.
# ⚙️ Key Logic: Utilizes QdrantClient for in-memory vector storage and retrieval, supporting image search operations.
# 🧠 Reasoning: Chosen for its efficient handling of high-dimensional vector data and ease of integration with Python applications.

from qdrant_client import QdrantClient
from qdrant_client.http import models
import os
import json
import numpy as np

class QdrantDB:
    def __init__(self, collection_name="image_collection"):
        """Initialize a connection to Qdrant vector database."""
        # Create a local Qdrant instance
        self.client = QdrantClient(":memory:")  # In-memory storage for simple usage
        self.collection_name = collection_name
        
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
        Add an image embedding to the database.
        
        Args:
            image_path (str): Path to the image file
            embedding (np.ndarray): Vector embedding of the image
            metadata (dict, optional): Additional metadata for the image
        """
        image_id = self.next_id
        self.next_id += 1
        
        # Ensure embedding is a numpy array
        if not isinstance(embedding, np.ndarray):
            embedding = np.array(embedding, dtype=np.float32)
        
        # Normalize the embedding vector if it's not already normalized
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        # Convert metadata to a serializable format
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
                        
            metadata = clean_metadata
        else:
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