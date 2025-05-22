import streamlit as st
import umap
import plotly.express as px
from streamlit_plotly_events import plotly_events

# Add cached UMAP computation function
@st.cache_data
def compute_umap(vectors, n_neighbors, min_dist):
    """
    Cached UMAP projection of the list-of-list embeddings.
    """
    import numpy as np
    arr = np.array(vectors)
    reducer = umap.UMAP(n_neighbors=n_neighbors, min_dist=min_dist, random_state=42)
    return reducer.fit_transform(arr)

def render_latent_space_tab():
    """
    Renders the Latent Space Explorer tab for embedding visualization.
    """
    st.header("🔮 Latent Space Explorer")

    if not st.session_state.get('database_built', False):
        st.warning("Please build or load the database first.")
        return

    # Fetch latent space data
    try:
        df = st.session_state.db_manager.get_latent_space_data()
    except Exception as e:
        st.error(f"Error retrieving latent space data: {e}")
        return

    # Sampling for large datasets
    num_points = len(df)
    if num_points > 2000:
        sample_size = st.sidebar.slider(
            "Number of points to visualize (sampling)",
            min_value=500,
            max_value=num_points,
            value=2000,
            step=500,
        )
        st.sidebar.write(f"Visualizing {sample_size}/{num_points} points")
        df = df.sample(n=sample_size, random_state=42).reset_index(drop=True)

    # Sidebar controls for visualization
    st.sidebar.header("Visualization Settings")
    metadata_fields = [c for c in df.columns if c not in ['vector', 'path']]
    color_by = st.sidebar.selectbox("Color by", metadata_fields)
    n_neighbors = st.sidebar.slider("UMAP n_neighbors", min_value=2, max_value=50, value=15)
    min_dist = st.sidebar.slider("UMAP min_dist", min_value=0.0, max_value=1.0, value=0.1, step=0.01)

    # Extract vectors
    vectors = df['vector'].tolist()

    # Compute UMAP projection (cached)
    with st.spinner("Computing UMAP projection..."):
        coords = compute_umap(vectors, n_neighbors, min_dist)

    df['x'] = coords[:, 0]
    df['y'] = coords[:, 1]

    # Create scatter plot
    hover_fields = [c for c in df.columns if c not in ['vector', 'x', 'y']]
    is_numeric = df[color_by].dtype.kind in 'biufc'
    fig = px.scatter(
        df,
        x='x', y='y',
        color=color_by,
        hover_data=hover_fields,
        title="UMAP Projection of Image Embeddings",
        width=800,
        height=600,
        template='plotly_dark',
        color_continuous_scale='Viridis' if is_numeric else None,
        color_discrete_sequence=px.colors.qualitative.D3 if not is_numeric else None,
    )
    fig.update_traces(marker=dict(size=6, opacity=0.7))
    fig.update_layout(
        legend_title_text=color_by,
        dragmode='lasso',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='white',
    )

    # Render the Plotly chart and enable click + lasso selection
    st.plotly_chart(fig, use_container_width=True)
    selected = plotly_events(
        fig,
        click_event=True,
        select_event=True,
        override_height=600,
        override_width=800,
        key="latent_space"
    )

    # Display selected images
    if selected:
        st.subheader("Selected Images")
        cols = st.columns(min(len(selected), 5))
        for sel, col in zip(selected, cols):
            idx = sel.get('pointIndex')
            image_path = df.iloc[idx]['path']
            with col:
                st.image(image_path, caption=image_path, use_container_width=True) 