# 🚀 Performance Testing Script for Pixel Detective Optimizations
# 📌 Purpose: Validate performance improvements and benchmark optimizations
# 🎯 Mission: Prove the optimizations work and measure improvements
# 💡 Based on: Streamlit Background tasks.md research

import time
import logging
import threading
import sys
import os
from typing import Dict, List, Any
from dataclasses import dataclass
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for comparison"""
    startup_time: float = 0.0
    ui_render_time: float = 0.0
    model_load_time: float = 0.0
    first_interaction_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    success: bool = False
    error_message: str = ""


class PerformanceTester:
    """
    Comprehensive performance testing for Pixel Detective optimizations.
    
    Tests:
    1. Startup time comparison (old vs optimized)
    2. Model loading performance
    3. Memory usage optimization
    4. Background loading effectiveness
    5. UI responsiveness
    """
    
    def __init__(self):
        self.results: Dict[str, PerformanceMetrics] = {}
        
    def run_all_tests(self) -> Dict[str, PerformanceMetrics]:
        """Run all performance tests"""
        logger.info("🚀 Starting comprehensive performance tests...")
        
        # Test 1: Optimized system
        logger.info("Testing optimized system...")
        self.results["optimized"] = self.test_optimized_system()
        
        # Test 2: Legacy system (for comparison)
        logger.info("Testing legacy system...")
        self.results["legacy"] = self.test_legacy_system()
        
        # Test 3: Background loading effectiveness
        logger.info("Testing background loading...")
        self.results["background_loading"] = self.test_background_loading()
        
        # Test 4: Memory efficiency
        logger.info("Testing memory efficiency...")
        self.results["memory_efficiency"] = self.test_memory_efficiency()
        
        # Generate comparison report
        self.generate_report()
        
        return self.results
    
    def test_optimized_system(self) -> PerformanceMetrics:
        """Test the optimized system performance"""
        metrics = PerformanceMetrics()
        
        try:
            # Test startup time
            start_time = time.time()
            
            # Import optimized components
            from core.optimized_model_manager import get_optimized_model_manager
            from core.fast_startup_manager import get_fast_startup_manager
            from utils.optimized_session_state import get_optimized_session_state
            
            ui_start = time.time()
            
            # Simulate UI rendering (fast components only)
            startup_manager = get_fast_startup_manager()
            progress = startup_manager.start_fast_startup()
            
            metrics.ui_render_time = time.time() - ui_start
            
            # Test model manager initialization (should be instant)
            model_start = time.time()
            model_manager = get_optimized_model_manager()
            
            # Start background preloading
            model_manager.preload_models_async()
            
            # Wait for models to be ready
            timeout = 60.0
            wait_start = time.time()
            
            while time.time() - wait_start < timeout:
                if model_manager.are_all_models_ready():
                    break
                time.sleep(0.5)
            
            metrics.model_load_time = time.time() - model_start
            metrics.startup_time = time.time() - start_time
            
            # Test first interaction time
            interaction_start = time.time()
            
            # Simulate getting a model (should be instant if preloaded)
            try:
                clip_model, clip_preprocess = model_manager.get_clip_model(timeout=5.0)
                metrics.first_interaction_time = time.time() - interaction_start
                metrics.success = True
            except Exception as e:
                logger.error(f"Model interaction failed: {e}")
                metrics.error_message = str(e)
            
            # Get memory usage
            metrics.memory_usage_mb = self._get_memory_usage()
            
        except Exception as e:
            logger.error(f"Optimized system test failed: {e}")
            metrics.error_message = str(e)
            metrics.startup_time = time.time() - start_time
        
        return metrics
    
    def test_legacy_system(self) -> PerformanceMetrics:
        """Test the legacy system performance"""
        metrics = PerformanceMetrics()
        
        try:
            start_time = time.time()
            
            # Import legacy components
            from models.lazy_model_manager import LazyModelManager
            import torch
            
            ui_start = time.time()
            
            # Simulate legacy UI rendering (with heavy imports)
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            
            metrics.ui_render_time = time.time() - ui_start
            
            # Test legacy model loading (blocking)
            model_start = time.time()
            
            model_manager = LazyModelManager(device)
            
            # Load models synchronously (legacy behavior)
            clip_model, clip_preprocess = model_manager.get_clip_model_for_search()
            blip_model, blip_processor = model_manager.get_blip_model_for_caption()
            
            metrics.model_load_time = time.time() - model_start
            metrics.startup_time = time.time() - start_time
            
            # Test first interaction time
            interaction_start = time.time()
            
            # Simulate model usage
            try:
                # This should be instant since models are already loaded
                clip_model, clip_preprocess = model_manager.get_clip_model_for_search()
                metrics.first_interaction_time = time.time() - interaction_start
                metrics.success = True
            except Exception as e:
                logger.error(f"Legacy model interaction failed: {e}")
                metrics.error_message = str(e)
            
            # Get memory usage
            metrics.memory_usage_mb = self._get_memory_usage()
            
        except Exception as e:
            logger.error(f"Legacy system test failed: {e}")
            metrics.error_message = str(e)
            metrics.startup_time = time.time() - start_time
        
        return metrics
    
    def test_background_loading(self) -> PerformanceMetrics:
        """Test background loading effectiveness"""
        metrics = PerformanceMetrics()
        
        try:
            start_time = time.time()
            
            from core.optimized_model_manager import OptimizedModelManager
            import torch
            
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model_manager = OptimizedModelManager(device)
            
            # Start background loading
            model_manager.preload_models_async()
            
            # Measure how quickly we can get UI ready
            ui_ready_time = time.time() - start_time
            
            # Wait for background loading to complete
            timeout = 60.0
            wait_start = time.time()
            
            while time.time() - wait_start < timeout:
                if model_manager.are_all_models_ready():
                    break
                time.sleep(0.1)
            
            total_time = time.time() - start_time
            background_load_time = time.time() - wait_start
            
            metrics.ui_render_time = ui_ready_time
            metrics.model_load_time = background_load_time
            metrics.startup_time = total_time
            metrics.success = model_manager.are_all_models_ready()
            
            if not metrics.success:
                metrics.error_message = "Background loading timed out"
            
            metrics.memory_usage_mb = self._get_memory_usage()
            
        except Exception as e:
            logger.error(f"Background loading test failed: {e}")
            metrics.error_message = str(e)
            metrics.startup_time = time.time() - start_time
        
        return metrics
    
    def test_memory_efficiency(self) -> PerformanceMetrics:
        """Test memory efficiency improvements"""
        metrics = PerformanceMetrics()
        
        try:
            start_time = time.time()
            
            # Test memory usage with optimized manager
            from core.optimized_model_manager import OptimizedModelManager
            import torch
            import gc
            
            # Clear memory first
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            initial_memory = self._get_memory_usage()
            
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model_manager = OptimizedModelManager(device)
            
            # Load models
            model_manager.preload_models_async()
            
            # Wait for loading
            timeout = 60.0
            wait_start = time.time()
            
            while time.time() - wait_start < timeout:
                if model_manager.are_all_models_ready():
                    break
                time.sleep(0.5)
            
            final_memory = self._get_memory_usage()
            memory_increase = final_memory - initial_memory
            
            metrics.startup_time = time.time() - start_time
            metrics.memory_usage_mb = memory_increase
            metrics.success = model_manager.are_all_models_ready()
            
            # Test memory cleanup
            model_manager.cleanup_unused_models(keep_recent_minutes=0.0)
            
            cleanup_memory = self._get_memory_usage()
            memory_after_cleanup = cleanup_memory - initial_memory
            
            logger.info(f"Memory usage: Initial={initial_memory:.1f}MB, "
                       f"After loading={final_memory:.1f}MB (+{memory_increase:.1f}MB), "
                       f"After cleanup={cleanup_memory:.1f}MB (+{memory_after_cleanup:.1f}MB)")
            
        except Exception as e:
            logger.error(f"Memory efficiency test failed: {e}")
            metrics.error_message = str(e)
            metrics.startup_time = time.time() - start_time
        
        return metrics
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except ImportError:
            # Fallback to basic memory check
            try:
                import torch
                if torch.cuda.is_available():
                    return torch.cuda.memory_allocated(0) / 1024 / 1024
            except:
                pass
            return 0.0
    
    def generate_report(self):
        """Generate a comprehensive performance report"""
        logger.info("📊 Generating performance report...")
        
        report = {
            "timestamp": time.time(),
            "test_results": {},
            "comparisons": {},
            "recommendations": []
        }
        
        # Add raw results
        for test_name, metrics in self.results.items():
            report["test_results"][test_name] = {
                "startup_time": metrics.startup_time,
                "ui_render_time": metrics.ui_render_time,
                "model_load_time": metrics.model_load_time,
                "first_interaction_time": metrics.first_interaction_time,
                "memory_usage_mb": metrics.memory_usage_mb,
                "success": metrics.success,
                "error_message": metrics.error_message
            }
        
        # Generate comparisons
        if "optimized" in self.results and "legacy" in self.results:
            opt = self.results["optimized"]
            leg = self.results["legacy"]
            
            if opt.success and leg.success:
                startup_improvement = ((leg.startup_time - opt.startup_time) / leg.startup_time) * 100
                ui_improvement = ((leg.ui_render_time - opt.ui_render_time) / leg.ui_render_time) * 100
                model_improvement = ((leg.model_load_time - opt.model_load_time) / leg.model_load_time) * 100
                
                report["comparisons"] = {
                    "startup_time_improvement_percent": startup_improvement,
                    "ui_render_improvement_percent": ui_improvement,
                    "model_load_improvement_percent": model_improvement,
                    "memory_difference_mb": opt.memory_usage_mb - leg.memory_usage_mb
                }
                
                # Generate recommendations
                if startup_improvement > 50:
                    report["recommendations"].append("✅ Excellent startup time improvement achieved")
                elif startup_improvement > 20:
                    report["recommendations"].append("✅ Good startup time improvement")
                else:
                    report["recommendations"].append("⚠️ Startup time improvement could be better")
                
                if ui_improvement > 80:
                    report["recommendations"].append("✅ Outstanding UI responsiveness improvement")
                elif ui_improvement > 50:
                    report["recommendations"].append("✅ Good UI responsiveness improvement")
                else:
                    report["recommendations"].append("⚠️ UI responsiveness needs more optimization")
        
        # Save report
        report_path = "performance_test_results.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        self._print_summary(report)
        
        logger.info(f"📄 Full report saved to: {report_path}")
    
    def _print_summary(self, report: Dict[str, Any]):
        """Print a human-readable summary"""
        print("\n" + "="*80)
        print("🚀 PIXEL DETECTIVE PERFORMANCE TEST RESULTS")
        print("="*80)
        
        # Test results
        for test_name, results in report["test_results"].items():
            print(f"\n📊 {test_name.upper()} SYSTEM:")
            print(f"   Startup Time:     {results['startup_time']:.2f}s")
            print(f"   UI Render Time:   {results['ui_render_time']:.3f}s")
            print(f"   Model Load Time:  {results['model_load_time']:.2f}s")
            print(f"   Memory Usage:     {results['memory_usage_mb']:.1f}MB")
            print(f"   Success:          {'✅' if results['success'] else '❌'}")
            if results['error_message']:
                print(f"   Error:            {results['error_message']}")
        
        # Comparisons
        if "comparisons" in report:
            comp = report["comparisons"]
            print(f"\n🔥 PERFORMANCE IMPROVEMENTS:")
            print(f"   Startup Time:     {comp.get('startup_time_improvement_percent', 0):.1f}% faster")
            print(f"   UI Rendering:     {comp.get('ui_render_improvement_percent', 0):.1f}% faster")
            print(f"   Model Loading:    {comp.get('model_load_improvement_percent', 0):.1f}% faster")
            print(f"   Memory Usage:     {comp.get('memory_difference_mb', 0):.1f}MB difference")
        
        # Recommendations
        if report["recommendations"]:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in report["recommendations"]:
                print(f"   {rec}")
        
        print("\n" + "="*80)


def main():
    """Run the performance tests"""
    print("🚀 Pixel Detective Performance Testing Suite")
    print("Testing optimizations based on Streamlit Background tasks.md research")
    print("-" * 80)
    
    tester = PerformanceTester()
    results = tester.run_all_tests()
    
    print("\n✅ Performance testing completed!")
    print("Check performance_test_results.json for detailed results.")


if __name__ == "__main__":
    main() 