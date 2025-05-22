import streamlit as st
import umap
import plotly.express as px
from streamlit_plotly_events import plotly_events
import pandas as pd
import os
from utils.logger import logger
import plotly.graph_objects as go

# Add cached UMAP computation function
@st.cache_data
def compute_umap(vectors, n_neighbors, min_dist):
    """
    Cached UMAP projection of the list-of-list embeddings.
    """
    import numpy as np
    arr = np.array(vectors)
    # UMAP can't have n_neighbors >= n_samples
    if n_neighbors >= len(arr):
        n_neighbors = len(arr) -1 
    if n_neighbors < 2 and len(arr) > 1 : # UMAP requires n_neighbors >= 2 generally
        n_neighbors = 2
    elif n_neighbors < 1 and len(arr) <=1 : # if only one sample, avoid error
         n_neighbors = 1


    if n_neighbors < 1 : # Final fallback if still problematic
        logger.warning(f"Adjusted n_neighbors to 1 due to small dataset size ({len(arr)} points). UMAP may not be meaningful.")
        # For a single point, UMAP is trivial; for very few points, it's constrained.
        # Handle single point case to avoid UMAP error directly.
        if len(arr) == 1:
            return np.array([[0,0]]) # Return a single point at origin
        # If n_neighbors is still < 1, but more than 1 point, it's an issue.
        # However, previous logic should prevent this. Defaulting to 1 if it somehow gets here.
        n_neighbors = 1


    reducer = umap.UMAP(n_neighbors=n_neighbors, min_dist=min_dist, random_state=42, transform_seed=42)
    return reducer.fit_transform(arr)

def render_latent_space_tab():
    """
    Renders the Latent Space Explorer tab for embedding visualization.
    """
    st.header("🔮 Latent Space Explorer")

    try:
        df = st.session_state.db_manager.get_latent_space_data()
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

    # UMAP projection
    if 'x' in df_display.columns and 'y' in df_display.columns and df_display['x'].notnull().all() and df_display['y'].notnull().all():
        df_display['umap_x'] = df_display['x']
        df_display['umap_y'] = df_display['y']
    else:
        try:
            vectors_display = df_display['vector'].tolist()
            coords = compute_umap(vectors_display, n_neighbors_val, min_dist_val)
            df_display['umap_x'] = coords[:, 0].astype(float)
            df_display['umap_y'] = coords[:, 1].astype(float)
        except Exception as e:
            logger.error(f"UMAP computation failed: {e}")
            st.warning("No data available for latent space visualization.")
            return

    # --- DBSCAN clustering ---
    try:
        from sklearn.cluster import DBSCAN
        import numpy as np
        X = df_display[['umap_x', 'umap_y']].values
        db = DBSCAN(eps=dbscan_eps, min_samples=3).fit(X)
        df_display['cluster'] = db.labels_
        n_clusters = len(set(db.labels_)) - (1 if -1 in db.labels_ else 0)
        st.write(f"DBSCAN found {n_clusters} clusters (label -1 = noise)")
    except Exception as e:
        logger.error(f"DBSCAN clustering failed: {e}")
        df_display['cluster'] = 0
        n_clusters = 1

    # Color by cluster
    color_by = 'cluster'
    color_data_for_plot = df_display['cluster']
    # Outliers (label -1) will be colored gray
    cluster_colors = px.colors.qualitative.Plotly + ["#888888"]  # Add gray for noise
    color_map = {c: cluster_colors[i % len(cluster_colors)] for i, c in enumerate(sorted(df_display['cluster'].unique()))}
    color_map[-1] = "#888888"  # gray for noise
    marker_colors = df_display['cluster'].map(color_map)

    hover_name = 'filename' if 'filename' in df_display.columns else None

    # Minimal scatter plot: plot umap_x vs umap_y, colored by cluster
    fig = go.Figure(
        data=go.Scatter(
            x=df_display['umap_x'],
            y=df_display['umap_y'],
            mode='markers',
            marker=dict(
                size=marker_size,
                color=marker_colors,
                opacity=1,
                symbol='circle'
            ),
            text=df_display['filename'] if 'filename' in df_display.columns else None
        )
    )

    fig.update_layout(
        template='plotly_dark',
        xaxis_title='umap_x',
        yaxis_title='umap_y',
        showlegend=False,
        autosize=True,
        margin=dict(l=10, r=10, b=10, t=40, pad=4),
    )

    st.plotly_chart(fig, use_container_width=True)
    return 