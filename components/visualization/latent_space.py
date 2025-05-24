"""
Latent Space Explorer for Pixel Detective with lazy loading optimizations.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import umap
from sklearn.cluster import DBSCAN
from utils.logger import logger
from utils.lazy_session_state import LazySessionManager

def reduce_dimensionality_umap(embeddings, n_neighbors=15, min_dist=0.1, n_components=2):
    """
    Apply UMAP for dimensionality reduction.
    """
    try:
        reducer = umap.UMAP(n_neighbors=n_neighbors, min_dist=min_dist, n_components=n_components, random_state=42)
        embedding_2d = reducer.fit_transform(embeddings)
        return embedding_2d
    except Exception as e:
        logger.error(f"Error in UMAP dimensionality reduction: {e}")
        raise

def cluster_embeddings(embeddings_2d, eps=0.7, min_samples=3):
    """
    Apply DBSCAN clustering on the 2D embeddings.
    """
    try:
        clustering = DBSCAN(eps=eps, min_samples=min_samples)
        cluster_labels = clustering.fit_predict(embeddings_2d)
        return cluster_labels
    except Exception as e:
        logger.error(f"Error in DBSCAN clustering: {e}")
        return np.zeros(len(embeddings_2d))  # Return all points as one cluster

def render_latent_space_tab():
    """
    Renders the Latent Space Explorer tab for embedding visualization with lazy loading optimizations.
    """
    st.header("🔮 Latent Space Explorer")

    # 🚀 LAZY LOADING: Initialize search state only when tab is accessed
    LazySessionManager.init_search_state()

    try:
        # 🚀 LAZY LOADING: Get database manager only when needed
        db_manager = LazySessionManager.ensure_database_manager()
        df = db_manager.get_latent_space_data()
    except Exception as e:
        logger.error(f"Error retrieving latent space data: {e}")
        st.warning("No data available for latent space visualization.")
        return

    if df is None or df.empty or 'vector' not in df.columns or df['vector'].isnull().any():
        logger.warning("Latent space DataFrame is empty, missing 'vector', or contains nulls.")
        st.warning("No data available for latent space visualization.")
        return

    st.write("DF shape:", df.shape)
    st.write("DF columns:", df.columns)
    if not df.empty:
        st.write("First row vector (as list):", df['vector'].iloc[0].tolist())
        st.write("Vector shape:", df['vector'].iloc[0].shape)
        st.write("All vectors identical:", all((v == df['vector'].iloc[0]).all() for v in df['vector']))
    else:
        st.write("No data")
    st.write("Any nulls in vector:", df['vector'].isnull().any())
    st.write("Vector type:", type(df['vector'].iloc[0]) if not df.empty else "No data")

    # Remove debug st.write() calls
    # Minimal: no sampling, no sidebar info, just plot all points
    df_display = df.copy()

    # UMAP parameters (fixed minimal values)
    n_neighbors_val = min(15, max(2, len(df_display) - 1))
    min_dist_val = 0.1

    # Add a slider for marker size
    marker_size = st.slider("Point size", min_value=3, max_value=30, value=10, step=1)

    # Add a slider for DBSCAN eps parameter
    dbscan_eps = st.sidebar.slider("DBSCAN eps (cluster radius)", min_value=0.1, max_value=5.0, value=0.7, step=0.1)

    if st.button("Generate Latent Space Visualization"):
        with st.spinner("Processing embeddings and generating visualization..."):
            try:
                # Extract embeddings from the 'vector' column
                embeddings = np.array(df_display['vector'].tolist())
                
                # Apply UMAP for dimensionality reduction
                st.write("Applying UMAP dimensionality reduction...")
                embeddings_2d = reduce_dimensionality_umap(embeddings, n_neighbors=n_neighbors_val, min_dist=min_dist_val)
                
                # Apply DBSCAN clustering
                st.write("Applying DBSCAN clustering...")
                cluster_labels = cluster_embeddings(embeddings_2d, eps=dbscan_eps)
                
                # Add 2D coordinates and cluster labels to the dataframe
                df_display['x'] = embeddings_2d[:, 0]
                df_display['y'] = embeddings_2d[:, 1]
                df_display['cluster'] = cluster_labels
                
                # Count clusters
                unique_clusters = np.unique(cluster_labels)
                n_clusters = len(unique_clusters) - (1 if -1 in unique_clusters else 0)  # Exclude noise (-1)
                noise_points = np.sum(cluster_labels == -1)
                
                st.write(f"**Clustering Results:**")
                st.write(f"- Number of clusters: {n_clusters}")
                st.write(f"- Noise points: {noise_points}")
                
                # Create the scatter plot
                fig = px.scatter(
                    df_display, 
                    x='x', 
                    y='y', 
                    color='cluster',
                    hover_data=['path', 'caption'] if 'caption' in df_display.columns else ['path'],
                    title="Image Embeddings in 2D Latent Space (Colored by Cluster)",
                    color_continuous_scale='viridis'
                )
                
                # Update marker size
                fig.update_traces(marker=dict(size=marker_size))
                
                # Update layout
                fig.update_layout(
                    width=800,
                    height=600,
                    xaxis_title="UMAP Dimension 1",
                    yaxis_title="UMAP Dimension 2"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Optionally, show cluster information
                if st.checkbox("Show cluster details"):
                    for cluster_id in sorted(unique_clusters):
                        if cluster_id == -1:
                            st.write(f"**Noise points (cluster -1):** {noise_points} images")
                        else:
                            cluster_size = np.sum(cluster_labels == cluster_id)
                            st.write(f"**Cluster {cluster_id}:** {cluster_size} images")
                            
                            # Show some sample images from this cluster
                            cluster_images = df_display[df_display['cluster'] == cluster_id]['path'].head(3).tolist()
                            if cluster_images:
                                cols = st.columns(len(cluster_images))
                                for i, img_path in enumerate(cluster_images):
                                    with cols[i]:
                                        try:
                                            st.image(img_path, use_container_width=True)
                                            st.caption(f"Sample from cluster {cluster_id}")
                                        except Exception as e:
                                            st.write(f"Error loading {img_path}: {e}")
                
            except Exception as e:
                st.error(f"Error generating visualization: {e}")
                logger.error(f"Error in latent space visualization: {e}", exc_info=True) 