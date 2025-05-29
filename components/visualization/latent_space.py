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
from components.task_orchestrator import submit as submit_task, is_running as is_task_running # Import TaskOrchestrator

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

    # FIXED: Check if we're in a proper Streamlit context before accessing session state
    try:
        # Only access session state if we're in the main UI thread
        if not hasattr(st, 'session_state'):
            st.warning("Latent space visualization not available yet. Please complete the initial setup first.")
            return
            
        # LAZY LOADING: Initialize search state only when tab is accessed
        LazySessionManager.init_search_state()

        db_manager = st.session_state.get('db_manager', None)
        if db_manager is None:
            st.info("🔄 Database manager not ready. Please build the database first using the sidebar.")
            # Attempt to get it if not present, might have been set by another process/tab
            try:
                db_manager = LazySessionManager.ensure_database_manager(create_if_missing=False) # Don't auto-create here
                if db_manager is None:
                    return # Still not available
            except Exception:
                 return # Failed to get it
            
        try:
            df = db_manager.get_latent_space_data()
        except Exception as e:
            logger.error(f"Error retrieving latent space data: {e}")
            st.warning("Error retrieving latent space data. Please ensure the database is built properly.")
            return
    except Exception as e:
        logger.error(f"Error retrieving latent space data: {e}")
        st.warning("No data available for latent space visualization. Please ensure the database is built first.")
        return

    if df is None or df.empty or 'vector' not in df.columns:
        logger.warning("Latent space DataFrame is empty or missing 'vector' column.")
        st.warning("No data available for latent space visualization. DataFrame empty or 'vector' column missing.")
        return

    # Ensure vectors are not null before proceeding
    if df['vector'].isnull().any():
        logger.warning("Latent space DataFrame contains null values in 'vector' column.")
        st.warning("Data for latent space visualization is incomplete (null vectors found).")
        # Optionally, filter out rows with null vectors if appropriate
        # df = df[df['vector'].notnull()]
        # if df.empty:
        #     return
        return # Or simply don't proceed with nulls

    # Minimal: no sampling, no sidebar info, just plot all points
    df_display_initial = df.copy()

    # UMAP parameters
    n_neighbors_val = st.sidebar.slider("UMAP n_neighbors", min_value=2, max_value=min(100, len(df_display_initial)-1 if len(df_display_initial)>1 else 2), value=min(15, max(2, len(df_display_initial) - 1 if len(df_display_initial)>1 else 2)))
    min_dist_val = st.sidebar.slider("UMAP min_dist", min_value=0.01, max_value=0.99, value=0.1, step=0.01)

    # DBSCAN parameters
    dbscan_eps = st.sidebar.slider("DBSCAN eps (cluster radius)", min_value=0.1, max_value=5.0, value=0.7, step=0.1)
    dbscan_min_samples = st.sidebar.slider("DBSCAN min_samples", min_value=1, max_value=20, value=3, step=1)
    
    marker_size = st.sidebar.slider("Point size", min_value=3, max_value=30, value=10, step=1)

    def _run_latent_space_computation_task(embeddings_list, umap_n_neighbors, umap_min_dist, cluster_eps, cluster_min_samples):
        try:
            st.session_state.latent_space_results = None # Clear previous results
            embeddings_np = np.array(embeddings_list)
            if embeddings_np.size == 0 or embeddings_np.ndim != 2:
                raise ValueError("Embeddings are empty or not 2D after conversion to numpy array.")

            embeddings_2d = reduce_dimensionality_umap(embeddings_np, n_neighbors=umap_n_neighbors, min_dist=umap_min_dist)
            cluster_labels = cluster_embeddings(embeddings_2d, eps=cluster_eps, min_samples=cluster_min_samples)
            
            st.session_state.latent_space_results = {
                'embeddings_2d': embeddings_2d.tolist(), # store as list for session state
                'cluster_labels': cluster_labels.tolist(),
            }
            st.session_state.latent_space_status = "completed"
        except Exception as e:
            logger.error(f"Error during latent space computation task: {e}", exc_info=True)
            st.session_state.latent_space_status = "error"
            st.session_state.latent_space_error_message = str(e)

    if st.button("📊 Generate Latent Space Visualization"):
        if not is_task_running("latent_space_computation_task"):
            st.session_state.latent_space_status = "running"
            st.session_state.latent_space_results = None 
            
            # Extract raw embeddings to pass to the task
            # Ensure 'vector' column contains numpy arrays or lists that can be converted
            raw_embeddings = df_display_initial['vector'].apply(lambda x: x.tolist() if isinstance(x, np.ndarray) else x).tolist()

            submit_task("latent_space_computation_task", 
                        _run_latent_space_computation_task, 
                        raw_embeddings,
                        n_neighbors_val, 
                        min_dist_val, 
                        dbscan_eps, 
                        dbscan_min_samples)
        else:
            st.info("Latent space computation is already in progress.")

    task_status = st.session_state.get("latent_space_status")

    if task_status == "running" or is_task_running("latent_space_computation_task"):
        st.spinner("🌌 Calculating cosmic connections in your image universe...")

    elif task_status == "completed" and st.session_state.get('latent_space_results'):
        results_data = st.session_state.get('latent_space_results')
        embeddings_2d_list = results_data['embeddings_2d']
        cluster_labels_list = results_data['cluster_labels']

        if not embeddings_2d_list or not cluster_labels_list:
            st.error("Computation completed but results are empty.")
            return

        df_display = df_display_initial.copy() # Use a fresh copy of the original dataframe
        # Ensure indices align if df_display_initial was filtered or modified
        if len(df_display) != len(embeddings_2d_list):
            st.error(f"Dataframe length ({len(df_display)}) does not match results length ({len(embeddings_2d_list)}). Please regenerate.")
            # Potentially reset state or offer to regenerate
            st.session_state.latent_space_status = None 
            st.session_state.latent_space_results = None
            return
            
        df_display['x'] = [item[0] for item in embeddings_2d_list]
        df_display['y'] = [item[1] for item in embeddings_2d_list]
        df_display['cluster'] = cluster_labels_list
        
        unique_clusters = np.unique(cluster_labels_list)
        n_clusters = len(unique_clusters) - (1 if -1 in unique_clusters else 0)
        noise_points = np.sum(np.array(cluster_labels_list) == -1)
                
                st.write(f"**Clustering Results:**")
        st.write(f"- Number of clusters found: {n_clusters}")
        st.write(f"- Noise points (not clustered): {noise_points}")
                
                fig = px.scatter(
                    df_display, 
                    x='x', 
                    y='y', 
                    color='cluster',
                    hover_data=['path', 'caption'] if 'caption' in df_display.columns else ['path'],
                    title="Image Embeddings in 2D Latent Space (Colored by Cluster)",
            color_continuous_scale=px.colors.qualitative.Plotly # Using a qualitative colormap
                )
                fig.update_traces(marker=dict(size=marker_size))
                fig.update_layout(
                    width=800,
                    height=600,
                    xaxis_title="UMAP Dimension 1",
                    yaxis_title="UMAP Dimension 2"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                if st.checkbox("Show cluster details"):
                    for cluster_id in sorted(unique_clusters):
                cluster_data = df_display[df_display['cluster'] == cluster_id]
                        if cluster_id == -1:
                    st.write(f"**Noise points (cluster -1):** {len(cluster_data)} images")
                        else:
                    st.write(f"**Cluster {cluster_id}:** {len(cluster_data)} images")
                            
                cluster_images = cluster_data['path'].head(3).tolist()
                            if cluster_images:
                                cols = st.columns(len(cluster_images))
                                for i, img_path in enumerate(cluster_images):
                                    with cols[i]:
                                        try:
                                st.image(img_path, width=150)
                                        except Exception as e:
                                            st.write(f"Error loading {img_path}: {e}")
                
    elif task_status == "error":
        st.error(f"Error during latent space computation: {st.session_state.get('latent_space_error_message', 'Unknown error')}")
    
    elif task_status is None and 'latent_space_results' not in st.session_state:
        st.info("Click 'Generate Latent Space Visualization' to begin.") 