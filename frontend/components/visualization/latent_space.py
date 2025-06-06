"""
Latent Space Explorer for Pixel Detective with lazy loading optimizations.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import umap
from sklearn.cluster import DBSCAN
from utils.logger import logger
from frontend.core import service_api
import asyncio
import os
from frontend.styles.style_injector import create_loading_spinner
from frontend.components.skeleton_screens import SkeletonScreens
from frontend.components.accessibility import AccessibilityEnhancer

# Define keys for sliders to ensure consistency
UMAP_N_NEIGHBORS_KEY = "umap_n_neighbors_slider_key" # Made keys more unique
UMAP_MIN_DIST_KEY = "umap_min_dist_slider_key"
DBSCAN_EPS_KEY = "dbscan_eps_slider_key"
DBSCAN_MIN_SAMPLES_KEY = "dbscan_min_samples_slider_key"
MARKER_SIZE_KEY = "marker_size_slider_key"

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
    AccessibilityEnhancer.add_skip_navigation()
    SkeletonScreens.inject_skeleton_styles()

    if not hasattr(st, 'session_state'):
        st.warning("Latent space visualization not available yet.")
        return
            
    # Initialize state for latent space data
    if 'latent_space_data_df' not in st.session_state:
        st.session_state.latent_space_data_df = None
    if 'latent_space_error' not in st.session_state:
        st.session_state.latent_space_error = None
    if 'latent_space_loading' not in st.session_state:
        st.session_state.latent_space_loading = False
    # For UMAP/DBSCAN computation results
    if 'latent_space_viz_results' not in st.session_state:
        st.session_state.latent_space_viz_results = None
    if 'latent_space_viz_status' not in st.session_state: # e.g., "idle", "running", "completed", "error"
        st.session_state.latent_space_viz_status = "idle"
    if 'latent_space_viz_error_message' not in st.session_state:
        st.session_state.latent_space_viz_error_message = None

    async def _fetch_and_set_latent_space_data():
        st.session_state.latent_space_loading = True
        st.session_state.latent_space_error = None
        st.session_state.latent_space_data_df = None
        st.session_state.latent_space_viz_results = None
        st.session_state.latent_space_viz_status = "idle"
        try:
            raw_data = await service_api.get_all_vectors_for_latent_space()
            if raw_data and not raw_data.get("error"):
                vectors_list = raw_data.get("vectors", [])
                if vectors_list:
                    st.session_state.latent_space_data_df = pd.DataFrame(vectors_list)
                    st.success("Latent space data loaded successfully from backend.")
                else:
                    st.session_state.latent_space_data_df = pd.DataFrame()
                    st.info("No vector data returned from backend for latent space.")
            else:
                err_msg = raw_data.get("detail", raw_data.get("error", "Unknown error fetching latent space data."))
                st.session_state.latent_space_error = err_msg
                logger.error(f"API Error fetching latent space data: {err_msg}")
                st.session_state.latent_space_data_df = pd.DataFrame()
        except Exception as e:
            logger.error(f"Exception fetching latent space data: {e}", exc_info=True)
            st.session_state.latent_space_error = str(e)
            st.session_state.latent_space_data_df = pd.DataFrame()
        finally:
            st.session_state.latent_space_loading = False

    if st.button("🔄 Load/Refresh Latent Space Data from Backend"):
        asyncio.run(_fetch_and_set_latent_space_data())

    if st.session_state.latent_space_loading:
        SkeletonScreens.render_folder_scan_skeleton()
        create_loading_spinner("🌌 Fetching cosmic vector data from backend...")
        return

    if st.session_state.latent_space_error:
        st.error(f"Could not load latent space data: {st.session_state.latent_space_error}")
        if st.button("Retry Load"):
            asyncio.run(_fetch_and_set_latent_space_data())
            return

    df = st.session_state.get('latent_space_data_df')
    if df is None:
        st.info("Click 'Load/Refresh Latent Space Data from Backend' to visualize.")
        return
    if df.empty:
        st.info("No data available to visualize. Backend returned no vectors or an error occurred. Check logs if this persists.")
        return
    if 'vector' not in df.columns or df['vector'].apply(lambda x: x is None or (isinstance(x, list) and not x)).any():
        st.error("Fetched data is missing 'vector' column or contains null/empty vectors. Cannot proceed.")
        return

    df_display_initial = df.copy()

    # UMAP parameters from sliders
    n_neighbors_val = st.sidebar.slider("UMAP n_neighbors", min_value=2, max_value=min(100, len(df_display_initial)-1 if len(df_display_initial)>1 else 2), value=st.session_state.get(UMAP_N_NEIGHBORS_KEY, min(15, max(2, len(df_display_initial) - 1 if len(df_display_initial)>1 else 2))), key=UMAP_N_NEIGHBORS_KEY)
    min_dist_val = st.sidebar.slider("UMAP min_dist", min_value=0.01, max_value=0.99, value=st.session_state.get(UMAP_MIN_DIST_KEY, 0.1), step=0.01, key=UMAP_MIN_DIST_KEY)
    dbscan_eps_val = st.sidebar.slider("DBSCAN eps", min_value=0.1, max_value=5.0, value=st.session_state.get(DBSCAN_EPS_KEY, 0.7), step=0.1, key=DBSCAN_EPS_KEY)
    dbscan_min_samples_val = st.sidebar.slider("DBSCAN min_samples", min_value=1, max_value=20, value=st.session_state.get(DBSCAN_MIN_SAMPLES_KEY, 3), step=1, key=DBSCAN_MIN_SAMPLES_KEY)
    marker_size_val = st.sidebar.slider("Point size", min_value=3, max_value=30, value=st.session_state.get(MARKER_SIZE_KEY, 10), step=1, key=MARKER_SIZE_KEY)

    def _run_frontend_computation_task(embeddings_list, umap_n, umap_d, db_eps, db_min):
        try:
            st.session_state.latent_space_viz_results = None
            if not embeddings_list:
                 st.session_state.latent_space_viz_status = "error"
                 st.session_state.latent_space_viz_error_message = "Cannot run computation on empty embeddings list."
                 return
            embeddings_np = np.array([np.array(e) for e in embeddings_list])
            if embeddings_np.ndim != 2:
                 st.session_state.latent_space_viz_status = "error"
                 st.session_state.latent_space_viz_error_message = "Embeddings could not be formed into a 2D array."
                 return
            embeddings_2d = reduce_dimensionality_umap(embeddings_np, n_neighbors=umap_n, min_dist=umap_d)
            cluster_labels = cluster_embeddings(embeddings_2d, eps=db_eps, min_samples=db_min)
            st.session_state.latent_space_viz_results = {
                'embeddings_2d': embeddings_2d.tolist(),
                'cluster_labels': cluster_labels.tolist(),
            }
            st.session_state.latent_space_viz_status = "completed"
        except ValueError as ve:
            logger.error(f"ValueError during frontend latent space computation task: {ve}", exc_info=True)
            st.session_state.latent_space_viz_status = "error"
            st.session_state.latent_space_viz_error_message = f"Data error: {str(ve)}"
        except Exception as e:
            logger.error(f"Error during frontend latent space computation task: {e}", exc_info=True)
            st.session_state.latent_space_viz_status = "error"
            st.session_state.latent_space_viz_error_message = str(e)

    if st.button("📊 Compute & Display Visualization (UMAP/DBSCAN)"):
        st.session_state.latent_space_viz_status = "running"
        st.session_state.latent_space_viz_results = None
        raw_embeddings_for_frontend_calc = df_display_initial['vector'].tolist()
        _run_frontend_computation_task(
            raw_embeddings_for_frontend_calc,
            n_neighbors_val,
            min_dist_val,
            dbscan_eps_val,
            dbscan_min_samples_val
        )

    viz_status = st.session_state.get("latent_space_viz_status", "idle")
    if viz_status == "running":
        create_loading_spinner("🔬 Running UMAP/DBSCAN and preparing visualization...")
    elif viz_status == "completed" and st.session_state.get('latent_space_viz_results'):
        results_data = st.session_state.get('latent_space_viz_results')
        df_plot = df_display_initial.copy()
        if len(df_plot) != len(results_data['embeddings_2d']):
            st.error("Data mismatch after computation. The number of items in the source data and computed results do not align. Please reload and recompute.")
            st.session_state.latent_space_viz_status = "idle"
            st.session_state.latent_space_viz_results = None
            return
        df_plot['x'] = [item[0] for item in results_data['embeddings_2d']]
        df_plot['y'] = [item[1] for item in results_data['embeddings_2d']]
        df_plot['cluster'] = results_data['cluster_labels']
        unique_clusters = np.unique(results_data['cluster_labels'])
        n_clusters = len(unique_clusters) - (1 if -1 in unique_clusters else 0)
        noise_points = np.sum(np.array(results_data['cluster_labels']) == -1)
        st.write(f"**Clustering Results:** Found {n_clusters} clusters and {noise_points} noise points.")
        fig = px.scatter(
            df_plot, x='x', y='y', color='cluster',
            hover_data=['path', 'caption'] if 'caption' in df_plot.columns else ['path'],
            title="Image Embeddings in 2D Latent Space (Colored by Cluster)",
            color_continuous_scale=px.colors.qualitative.Plotly 
        )
        fig.update_traces(marker=dict(size=marker_size_val))
        fig.update_layout(width=800, height=600, xaxis_title="UMAP Dimension 1", yaxis_title="UMAP Dimension 2")
        st.plotly_chart(fig, use_container_width=True)
        if st.checkbox("Show cluster details table"):
            for cluster_id_val in sorted(unique_clusters):
                cluster_data_df = df_plot[df_plot['cluster'] == cluster_id_val]
                cluster_label_text = "Noise points (unclustered)" if cluster_id_val == -1 else f"Cluster {cluster_id_val}"
                st.write(f"**{cluster_label_text}:** {len(cluster_data_df)} images")
                if 'path' in cluster_data_df.columns:
                    paths_to_show = cluster_data_df['path'].head(min(3, len(cluster_data_df))).tolist()
                    if paths_to_show:
                        img_cols = st.columns(len(paths_to_show))
                        for idx, img_p in enumerate(paths_to_show):
                            with img_cols[idx]:
                                try:
                                    st.image(img_p, width=150, caption=os.path.basename(img_p))
                                except Exception as img_load_err:
                                    st.caption(f"Cannot load: {os.path.basename(img_p)}")
                                    logger.debug(f"Error loading image {img_p} in cluster view: {img_load_err}")
                    else:
                        st.caption("No image paths to display for this cluster.")
                else:
                    st.caption("Path information not available in data for this cluster.")
    elif viz_status == "error":
        st.error(f"Error during visualization computation: {st.session_state.get('latent_space_viz_error_message', 'Unknown error')}")
        if st.button("Retry Computation"):
             st.session_state.latent_space_viz_status = "idle"
             st.experimental_rerun()
    # No specific message if idle and data is loaded, button prompts to compute. 