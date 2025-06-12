import streamlit as st
import torch

class LazySessionManager:
    @staticmethod
    def init_core_state():
        pass

def get_cached_model_manager():
    from models.lazy_model_manager import LazyModelManager
    if 'model_manager' not in st.session_state:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        st.session_state.model_manager = LazyModelManager(device)
    return st.session_state.model_manager

def get_cached_database_manager():
    # This function is not implemented yet, but the test calls it.
    # I'll add a placeholder to avoid an import error.
    if 'db_manager' not in st.session_state:
        # In a real application, you would initialize your database manager here.
        st.session_state.db_manager = "dummy_db_manager"
    return st.session_state.db_manager
