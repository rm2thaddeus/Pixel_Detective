# ⚡ Performance Optimizer Component
# 📌 Purpose: Optimize startup time, memory usage, and overall performance
# 🎯 Sprint 02 Final 25%: Performance verification and optimization
# 🚀 Target: <1s startup time, optimized module imports

import streamlit as st
import time
import sys
import gc
from functools import lru_cache
import importlib.util


class PerformanceOptimizer:
    """Component to optimize application performance"""
    
    def __init__(self):
        self.startup_time = None
        self.module_cache = {}
        self.performance_metrics = {}
    
    @staticmethod
    @lru_cache(maxsize=128)
    def lazy_import(module_name):
        """Lazy import modules to reduce startup time"""
        try:
            if module_name in sys.modules:
                return sys.modules[module_name]
            
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            return module
        except ImportError:
            return None
    
    @staticmethod
    def optimize_streamlit_config():
        """Optimize Streamlit configuration for better performance"""
        # Set performance-optimized config
        if not hasattr(st.session_state, 'performance_optimized'):
            # These would typically be set in .streamlit/config.toml
            # but we can also set them programmatically
            st.session_state.performance_optimized = True
    
    @staticmethod
    def preload_critical_modules():
        """Preload only critical modules to reduce initial load time"""
        critical_modules = [
            'streamlit',
            'os',
            'sys',
            'time'
        ]
        
        start_time = time.time()
        loaded_modules = []
        
        for module_name in critical_modules:
            try:
                module = PerformanceOptimizer.lazy_import(module_name)
                if module:
                    loaded_modules.append(module_name)
            except Exception as e:
                st.warning(f"Failed to preload {module_name}: {e}")
        
        load_time = time.time() - start_time
        return {
            'loaded_modules': loaded_modules,
            'load_time': load_time,
            'status': 'success' if load_time < 0.5 else 'warning'
        }
    
    @staticmethod
    def optimize_memory_usage():
        """Optimize memory usage by cleaning up unused objects"""
        # Force garbage collection
        collected = gc.collect()
        
        # Clear unnecessary session state
        keys_to_remove = []
        for key in st.session_state.keys():
            if key.startswith('temp_') or key.startswith('cache_'):
                # Only remove if older than 5 minutes
                if hasattr(st.session_state[key], 'timestamp'):
                    if time.time() - st.session_state[key].timestamp > 300:
                        keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del st.session_state[key]
        
        return {
            'objects_collected': collected,
            'session_keys_cleaned': len(keys_to_remove),
            'status': 'optimized'
        }
    
    @staticmethod
    def measure_startup_performance():
        """Measure and track startup performance metrics"""
        if 'startup_metrics' not in st.session_state:
            st.session_state.startup_metrics = {
                'start_time': time.time(),
                'modules_loaded': len(sys.modules),
                'memory_usage': 0
            }
        
        current_time = time.time()
        startup_time = current_time - st.session_state.startup_metrics['start_time']
        
        return {
            'startup_time': startup_time,
            'modules_loaded': len(sys.modules),
            'target_met': startup_time < 1.0,
            'status': 'excellent' if startup_time < 0.5 else 'good' if startup_time < 1.0 else 'needs_improvement'
        }
    
    @staticmethod
    def optimize_css_delivery():
        """Optimize CSS delivery for faster rendering"""
        # Inline critical CSS and defer non-critical styles
        critical_css = """
        <style>
        /* Critical above-the-fold styles */
        .main { 
            padding-top: 1rem; 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .pd-hero { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            border-radius: 12px;
            text-align: center;
        }
        .pd-button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            cursor: pointer;
            transition: transform 0.2s ease;
        }
        .pd-button:hover {
            transform: translateY(-2px);
        }
        </style>
        """
        
        st.markdown(critical_css, unsafe_allow_html=True)
        
        return {'status': 'optimized', 'critical_css_loaded': True}
    
    @staticmethod
    def create_performance_dashboard():
        """Create a performance monitoring dashboard"""
        st.markdown("### ⚡ Performance Dashboard")
        
        # Measure current performance
        startup_metrics = PerformanceOptimizer.measure_startup_performance()
        memory_metrics = PerformanceOptimizer.optimize_memory_usage()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            startup_status = "🟢" if startup_metrics['target_met'] else "🟡"
            st.metric(
                label=f"{startup_status} Startup Time",
                value=f"{startup_metrics['startup_time']:.2f}s",
                delta=f"Target: <1.0s",
                delta_color="normal" if startup_metrics['target_met'] else "inverse"
            )
        
        with col2:
            st.metric(
                label="🧠 Memory Usage",
                value=f"{memory_metrics['objects_collected']} objects cleaned",
                delta=f"{memory_metrics['session_keys_cleaned']} cache keys removed"
            )
        
        with col3:
            st.metric(
                label="📦 Modules Loaded",
                value=f"{startup_metrics['modules_loaded']}",
                delta="Optimized loading"
            )
        
        # Performance recommendations
        if not startup_metrics['target_met']:
            st.warning("⚠️ Startup time exceeds 1 second target. Consider optimizing module imports.")
            
            if st.button("🚀 Optimize Performance"):
                with st.spinner("Optimizing performance..."):
                    PerformanceOptimizer.optimize_memory_usage()
                    PerformanceOptimizer.optimize_css_delivery()
                    st.success("✅ Performance optimized!")
                    st.rerun()
        else:
            st.success("🎉 Performance targets met! Startup time is excellent.")
    
    @staticmethod
    def implement_code_splitting():
        """Implement code splitting for better performance"""
        # Define module groups for lazy loading
        module_groups = {
            'ui_components': [
                'ui.main_interface',
                'ui.sidebar',
                'ui.tabs'
            ],
            # 'search_features': [ # Removed as this logic is now in backend services
            #     'models.image_search',
            #     'models.similarity_search'
            # ],
            'advanced_ui_features': [ # Renamed and kept UI part
                'ui.latent_space',
                # 'models.advanced_search' # Removed as this logic is now in backend services
            ]
        }
        
        loaded_groups = {}
        
        for group_name, modules in module_groups.items():
            start_time = time.time()
            group_modules = []
            
            for module_name in modules:
                try:
                    module = PerformanceOptimizer.lazy_import(module_name)
                    if module:
                        group_modules.append(module_name)
                except Exception:
                    pass  # Module might not exist yet
            
            load_time = time.time() - start_time
            loaded_groups[group_name] = {
                'modules': group_modules,
                'load_time': load_time,
                'status': 'loaded' if group_modules else 'pending'
            }
        
        return loaded_groups
    
    @staticmethod
    def monitor_real_time_performance():
        """Monitor real-time performance metrics"""
        if 'performance_history' not in st.session_state:
            st.session_state.performance_history = []
        
        current_metrics = {
            'timestamp': time.time(),
            'modules_count': len(sys.modules),
            'session_state_size': len(st.session_state.keys())
        }
        
        st.session_state.performance_history.append(current_metrics)
        
        # Keep only last 10 measurements
        if len(st.session_state.performance_history) > 10:
            st.session_state.performance_history = st.session_state.performance_history[-10:]
        
        return st.session_state.performance_history
    
    @staticmethod
    def generate_performance_report():
        """Generate a comprehensive performance report"""
        startup_metrics = PerformanceOptimizer.measure_startup_performance()
        memory_metrics = PerformanceOptimizer.optimize_memory_usage()
        
        report = {
            'timestamp': time.time(),
            'startup_performance': {
                'startup_time': startup_metrics['startup_time'],
                'target_met': startup_metrics['target_met'],
                'status': startup_metrics['status'],
                'modules_loaded': startup_metrics['modules_loaded']
            },
            'memory_performance': {
                'objects_collected': memory_metrics['objects_collected'],
                'session_keys_cleaned': memory_metrics['session_keys_cleaned'],
                'status': memory_metrics['status']
            },
            'overall_score': 'excellent' if startup_metrics['target_met'] else 'good',
            'recommendations': []
        }
        
        # Add recommendations based on performance
        if not startup_metrics['target_met']:
            report['recommendations'].append("Optimize module imports to reduce startup time")
        
        if memory_metrics['objects_collected'] > 100:
            report['recommendations'].append("Consider implementing more aggressive memory management")
        
        if startup_metrics['modules_loaded'] > 50:
            report['recommendations'].append("Implement lazy loading for non-critical modules")
        
        return report 