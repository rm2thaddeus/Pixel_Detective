from qdrant_client import QdrantClient, models
from qdrant_client.http.models import PointStruct, UpdateStatus, Filter, FieldCondition, MatchValue
import uuid
import os
import numpy as np # For type hinting and numpy array checks

class QdrantDB:
    def __init__(self, collection_name="image_collection", host="localhost", port=6333, in_memory=False, prefer_grpc=False, api_key=None, timeout=10.0):
        """
        Initialize a connection to Qdrant vector database.

        Args:
            collection_name (str): Name of the collection to use.
            host (str): Qdrant host.
            port (int): Qdrant port.
            in_memory (bool): If True, use in-memory Qdrant. Host and port are ignored.
            prefer_grpc (bool): If True, use gRPC for communication.
            api_key (str, optional): API key for Qdrant Cloud.
            timeout (float): Connection timeout in seconds.
        """
        if in_memory:
            self.client = QdrantClient(":memory:")
            print("Initialized QdrantDB in-memory.")
        else:
            self.client = QdrantClient(host=host, port=port, prefer_grpc=prefer_grpc, api_key=api_key, timeout=timeout)
            print(f"Initialized QdrantDB client for {host}:{port}")
        
        self.collection_name = collection_name
        self.vector_size = 512  # Assuming CLIP ViT-B/32 embeddings

        # Ensure the collection exists
        try:
            self.client.get_collection(collection_name=self.collection_name)
            print(f"Collection '{self.collection_name}' already exists.")
        except Exception as e:
            # More specific check if collection does not exist
            # This depends on the exact exception qdrant_client throws for non-existent collections
            # For now, we assume any exception means it might not exist or is inaccessible
            print(f"Collection '{self.collection_name}' not found or error accessing: {e}. Attempting to create.")
            try:
                self.client.recreate_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_size,
                        distance=models.Distance.COSINE
                    )
                )
                print(f"Collection '{self.collection_name}' created successfully.")
            except Exception as create_e:
                print(f"Failed to create collection '{self.collection_name}': {create_e}")
                raise # Re-raise if creation fails, as it's critical

    def _prepare_vector(self, embedding):
        if hasattr(embedding, 'tolist'):
            vector = embedding.tolist()
        elif isinstance(embedding, np.ndarray):
            vector = embedding.astype(float).tolist()
        else:
            vector = list(map(float, embedding))
        
        if len(vector) != self.vector_size:
            # print(f"Warning: Embedding has incorrect dimension {len(vector)}, expected {self.vector_size}. Skipping.")
            return None # Return None to indicate an issue
        return vector

    def add_image(self, image_path, embedding, metadata=None):
        """
        Adds a single image to the Qdrant database.
        """
        if embedding is None:
            print(f"Skipping {image_path} due to missing embedding.")
            return False

        vector = self._prepare_vector(embedding)
        if vector is None:
            print(f"Skipping {image_path} due to invalid embedding dimension.")
            return False

        image_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, image_path))
        payload = metadata if metadata is not None else {}
        payload['filename'] = os.path.basename(image_path)
        payload['path'] = image_path

        try:
            response = self.client.upsert(
                collection_name=self.collection_name,
                points=[PointStruct(id=image_id, vector=vector, payload=payload)]
            )
            if response.status == UpdateStatus.COMPLETED:
                # print(f"Successfully added/updated {image_path} (ID: {image_id})")
                return True
            else:
                print(f"Failed to add/update {image_path}. Qdrant status: {response.status}")
                return False
        except Exception as e:
            print(f"Error adding image {image_path} to Qdrant: {e}")
            return False

    def add_images_batch(self, image_paths, embeddings, metadata_list=None, batch_size=32):
        """
        Adds multiple images to the Qdrant database in batches.
        Args:
            image_paths (list): List of image file paths.
            embeddings (list or np.ndarray): List of embeddings or 2D numpy array.
            metadata_list (list, optional): List of metadata dictionaries. Defaults to None.
            batch_size (int): Number of points to send in a single Qdrant request.
        Returns:
            tuple: (success_count, failure_count)
        """
        if not image_paths or embeddings is None or len(image_paths) != len(embeddings):
            print("Invalid input for batch addition: image_paths, embeddings length mismatch or empty.")
            return 0, len(image_paths) if image_paths else 0

        if metadata_list is None:
            metadata_list = [{} for _ in range(len(image_paths))]
        elif len(metadata_list) != len(image_paths):
            print("Warning: metadata_list length does not match image_paths length. Using empty metadata for some.")
            # Adjust metadata_list to match image_paths length, filling with empty dicts if necessary
            adjusted_metadata = [({} if i >= len(metadata_list) else metadata_list[i]) for i in range(len(image_paths))]
            metadata_list = adjusted_metadata

        points_to_upsert = []
        success_count = 0
        failure_count = 0

        for i in range(len(image_paths)):
            image_path = image_paths[i]
            embedding = embeddings[i]
            metadata = metadata_list[i]

            if embedding is None:
                print(f"Skipping {image_path} in batch due to missing embedding.")
                failure_count += 1
                continue
            
            vector = self._prepare_vector(embedding)
            if vector is None:
                print(f"Skipping {image_path} in batch due to invalid embedding dimension.")
                failure_count += 1
                continue

            image_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, image_path))
            payload = metadata if metadata is not None else {}
            payload['filename'] = os.path.basename(image_path)
            payload['path'] = image_path
            
            points_to_upsert.append(PointStruct(id=image_id, vector=vector, payload=payload))

            if len(points_to_upsert) >= batch_size or (i == len(image_paths) - 1 and points_to_upsert):
                try:
                    response = self.client.upsert(
                        collection_name=self.collection_name,
                        points=points_to_upsert
                    )
                    if response.status == UpdateStatus.COMPLETED:
                        success_count += len(points_to_upsert)
                        # print(f"Successfully upserted batch of {len(points_to_upsert)} points.")
                    else:
                        print(f"Failed to upsert batch. Qdrant status: {response.status}")
                        failure_count += len(points_to_upsert)
                except Exception as e:
                    print(f"Error during batch upsert to Qdrant: {e}")
                    failure_count += len(points_to_upsert)
                finally:
                    points_to_upsert = [] # Clear batch
        
        print(f"Batch addition complete. Success: {success_count}, Failures: {failure_count}")
        return success_count, failure_count

    def search_by_vector(self, query_vector, limit=5):
        """
        Search for similar images using a query vector.
        """
        vector = self._prepare_vector(query_vector)
        if vector is None:
            print("Invalid query vector dimension.")
            return []

        try:
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=limit,
                with_payload=True
            )
            
            results = []
            for hit in search_result:
                if hit.payload and 'path' in hit.payload:
                    results.append((hit.payload['path'], hit.score))
                else:
                    results.append((hit.id, hit.score))
            return results
        except Exception as e:
            print(f"Error searching Qdrant: {e}")
            return []

    def get_collection_info(self):
        """Returns information about the collection."""
        try:
            return self.client.get_collection(collection_name=self.collection_name)
        except Exception as e:
            print(f"Error getting collection info for '{self.collection_name}': {e}")
            return None

    def delete_collection(self):
        """Deletes the collection. Use with caution!"""
        try:
            self.client.delete_collection(collection_name=self.collection_name)
            print(f"Collection '{self.collection_name}' deleted successfully.")
            return True
        except Exception as e:
            print(f"Error deleting collection '{self.collection_name}': {e}")
            return False 

    def delete_image(self, image_path: str) -> bool:
        """
        Deletes a single image from the Qdrant database by its path.
        """
        # Compute the deterministic ID based on the image path
        image_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, image_path))
        try:
            # Delete points matching this path in the payload
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.Filters(
                    must=[models.FieldCondition(key="path", match=models.MatchValue(value=image_path))]
                )
            )
            print(f"Deleted {image_path} (ID: {image_id}) from collection '{self.collection_name}'.")
            return True
        except Exception as e:
            print(f"Error deleting image {image_path} from Qdrant: {e}")
            return False 

    def hybrid_search(self, query_vector, metadata_filter=None, limit=5):
        """
        Hybrid search: vector similarity + metadata filter.
        Args:
            query_vector: The embedding vector for the query.
            metadata_filter: Qdrant filter dict (or None).
            limit: Number of results to return.
        Returns:
            List of (path, score) tuples.
        """
        vector = self._prepare_vector(query_vector)
        if vector is None:
            print("Invalid query vector dimension.")
            return []

        # Convert dict filter to Qdrant models.Filters if needed
        filter_obj = None
        if metadata_filter:
            # Handle both old MUST format and new SHOULD format
            should_conditions = []
            must_conditions = []
            
            # Handle SHOULD conditions (new format)
            for cond in metadata_filter.get("should", []):
                should_conditions.append(FieldCondition(
                    key=cond["key"], 
                    match=MatchValue(value=cond["match"]["value"])
                ))
            
            # Handle MUST conditions (old format - for compatibility)
            for cond in metadata_filter.get("must", []):
                must_conditions.append(FieldCondition(
                    key=cond["key"], 
                    match=MatchValue(value=cond["match"]["value"])
                ))
            
            # Create filter with appropriate conditions
            if should_conditions and must_conditions:
                filter_obj = Filter(should=should_conditions, must=must_conditions)
            elif should_conditions:
                filter_obj = Filter(should=should_conditions)
            elif must_conditions:
                filter_obj = Filter(must=must_conditions)

        try:
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=limit,
                with_payload=True,
                query_filter=filter_obj
            )
            results = []
            for hit in search_result:
                if hit.payload and 'path' in hit.payload:
                    results.append((hit.payload['path'], hit.score))
                else:
                    results.append((hit.id, hit.score))
            return results
        except Exception as e:
            print(f"Error in hybrid search Qdrant: {e}")
            return []

    def query_hybrid_search(self, query_vector, metadata_filter=None, limit=5):
        """
        Proper hybrid search using Qdrant's Query API with RRF fusion.
        Args:
            query_vector: The embedding vector for the query.
            metadata_filter: Qdrant Filter object (models.Filter) or None.
            limit: Number of results to return.
        Returns:
            List of (path, score) tuples.
        """
        vector = self._prepare_vector(query_vector)
        if vector is None:
            print("Invalid query vector dimension.")
            return []

        try:
            if metadata_filter:
                # Hybrid search with metadata boosting using Query API
                search_result = self.client.query_points(
                    collection_name=self.collection_name,
                    prefetch=[
                        models.Prefetch(
                            query=vector,
                            limit=limit * 2,  # Get more vector candidates
                        ),
                        models.Prefetch(
                            query=vector,
                            query_filter=metadata_filter,
                            limit=limit,  # Metadata-boosted candidates
                        )
                    ],
                    query=models.FusionQuery(fusion=models.Fusion.RRF),
                    limit=limit,
                    with_payload=True
                )
                points = search_result.points
            else:
                # Pure vector search
                points = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=vector,
                    limit=limit,
                    with_payload=True
                )
            
            results = []
            for hit in points:
                if hit.payload and 'path' in hit.payload:
                    results.append((hit.payload['path'], hit.score))
                else:
                    results.append((hit.id, hit.score))
            return results
            
        except Exception as e:
            print(f"Error in query-based hybrid search: {e}")
            # Fallback to regular search
            return self.search_by_vector(query_vector, limit=limit) 