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

    # Minimal: no sampling, no sidebar info, just plot all points
    df_display = df.copy()

    # UMAP parameters (fixed minimal values)
    n_neighbors_val = min(15, max(2, len(df_display) - 1))
    min_dist_val = 0.1

    # Add a slider for marker size
    marker_size = st.slider("Point size", min_value=3, max_value=30, value=10, step=1)

    # UMAP projection
    if 'x' in df_display.columns and 'y' in df_display.columns and df_display['x'].notnull().all() and df_display['y'].notnull().all():
        df_display['umap_x'] = df_display['x']
        df_display['umap_y'] = df_display['y']
    else:
        try:
            vectors_display = df_display['vector'].tolist()
            coords = compute_umap(vectors_display, n_neighbors_val, min_dist_val)
            st.write("UMAP coords shape:", coords.shape)
            st.write("First UMAP coord:", coords[0] if coords.shape[0] > 0 else "No data")
            df_display['umap_x'] = coords[:, 0].astype(float)
            df_display['umap_y'] = coords[:, 1].astype(float)
            st.write("UMAP x range:", df_display['umap_x'].min(), df_display['umap_x'].max())
            st.write("UMAP y range:", df_display['umap_y'].min(), df_display['umap_y'].max())
            st.write("df_display dtypes:", df_display.dtypes)
        except Exception as e:
            logger.error(f"UMAP computation failed: {e}")
            st.warning("No data available for latent space visualization.")
            return

    # Color by: pick first available metadata field (not vector/path/x/y)
    exclude_fields = ['vector', 'path', 'x', 'y', 'umap_x', 'umap_y']
    color_fields = [c for c in df_display.columns if c not in exclude_fields]
    color_by = color_fields[0] if color_fields else None
    color_data_for_plot = None
    if color_by:
        if pd.api.types.is_numeric_dtype(df_display[color_by]):
            color_data_for_plot = df_display[color_by]
        else:
            color_data_for_plot = df_display[color_by].astype(str).fillna("NaN")
        if color_data_for_plot.nunique() == 1 and (color_data_for_plot.iloc[0] == "NaN" or pd.isna(color_data_for_plot.iloc[0])):
            logger.warning(f"Chosen color field '{color_by}' has no valid data; disabling color.")
            color_data_for_plot = None

    hover_name = 'filename' if 'filename' in df_display.columns else None

    # Print DataFrame and dtypes for debugging
    st.write("Plotting DataFrame (full):", df_display)
    st.write("dtypes:", df_display.dtypes)

    # Minimal scatter plot: plot umap_x vs umap_y, fixed color, fixed size
    fig = go.Figure(
        data=go.Scatter(
            x=df_display['umap_x'],
            y=df_display['umap_y'],
            mode='markers',
            marker=dict(
                size=marker_size,
                color='yellow',
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