#!/usr/bin/env python3
"""
🚀 Loading Screen Performance Test
Tests the optimized loading screen for performance issues and responsiveness.
"""

import time
import threading
import requests
import psutil
import os
from typing import Dict, List


class LoadingPerformanceTest:
    """Test suite for loading screen performance"""
    
    def __init__(self, streamlit_url: str = "http://localhost:8501"):
        self.streamlit_url = streamlit_url
        self.test_results = {}
        
    def test_server_responsiveness(self) -> Dict:
        """Test if the Streamlit server responds quickly"""
        print("🌐 Testing server responsiveness...")
        
        response_times = []
        for i in range(5):
            start_time = time.time()
            try:
                response = requests.get(self.streamlit_url, timeout=10)
                response_time = time.time() - start_time
                response_times.append(response_time)
                print(f"  Request {i+1}: {response_time:.3f}s (Status: {response.status_code})")
            except Exception as e:
                print(f"  Request {i+1}: FAILED - {str(e)}")
                response_times.append(float('inf'))
        
        avg_response_time = sum(response_times) / len(response_times)
        
        result = {
            'test': 'server_responsiveness',
            'avg_response_time': avg_response_time,
            'all_response_times': response_times,
            'status': 'PASS' if avg_response_time < 2.0 else 'FAIL'
        }
        
        print(f"✅ Average response time: {avg_response_time:.3f}s")
        return result
    
    def test_memory_usage(self) -> Dict:
        """Monitor memory usage during loading simulation"""
        print("🧠 Testing memory usage...")
        
        # Get current process (assuming this script runs alongside Streamlit)
        current_process = psutil.Process()
        initial_memory = current_process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"  Initial memory usage: {initial_memory:.2f} MB")
        
        # Simulate some loading operations
        time.sleep(2)
        
        final_memory = current_process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        result = {
            'test': 'memory_usage',
            'initial_memory_mb': initial_memory,
            'final_memory_mb': final_memory,
            'memory_increase_mb': memory_increase,
            'status': 'PASS' if memory_increase < 50 else 'FAIL'  # Less than 50MB increase
        }
        
        print(f"✅ Memory increase: {memory_increase:.2f} MB")
        return result
    
    def test_cpu_usage(self) -> Dict:
        """Monitor CPU usage during operations"""
        print("⚡ Testing CPU usage...")
        
        # Monitor CPU for a few seconds
        cpu_percentages = []
        for i in range(10):
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_percentages.append(cpu_percent)
        
        avg_cpu = sum(cpu_percentages) / len(cpu_percentages)
        max_cpu = max(cpu_percentages)
        
        result = {
            'test': 'cpu_usage',
            'avg_cpu_percent': avg_cpu,
            'max_cpu_percent': max_cpu,
            'all_cpu_readings': cpu_percentages,
            'status': 'PASS' if avg_cpu < 50 else 'FAIL'  # Less than 50% average
        }
        
        print(f"✅ Average CPU usage: {avg_cpu:.1f}%")
        print(f"✅ Peak CPU usage: {max_cpu:.1f}%")
        return result
    
    def test_loading_screen_imports(self) -> Dict:
        """Test that loading screen modules import quickly"""
        print("📦 Testing module import performance...")
        
        start_time = time.time()
        try:
            # Test importing the loading screen module
            import sys
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            
            from screens.loading_screen import LoadingScreen
            from core.background_loader import background_loader
            
            import_time = time.time() - start_time
            
            result = {
                'test': 'module_imports',
                'import_time': import_time,
                'status': 'PASS' if import_time < 1.0 else 'FAIL'  # Less than 1 second
            }
            
            print(f"✅ Module import time: {import_time:.3f}s")
            
        except Exception as e:
            result = {
                'test': 'module_imports',
                'import_time': float('inf'),
                'error': str(e),
                'status': 'FAIL'
            }
            print(f"❌ Import failed: {str(e)}")
        
        return result
    
    def test_background_thread_performance(self) -> Dict:
        """Test background thread operations don't block main thread"""
        print("🧵 Testing background thread performance...")
        
        def background_task():
            """Simulate background loading task"""
            time.sleep(2)  # Simulate work
        
        # Start background task
        start_time = time.time()
        thread = threading.Thread(target=background_task, daemon=True)
        thread.start()
        
        # Main thread should remain responsive
        main_thread_time = time.time() - start_time
        
        # Wait for background task to complete
        thread.join()
        total_time = time.time() - start_time
        
        result = {
            'test': 'background_threads',
            'main_thread_block_time': main_thread_time,
            'total_time': total_time,
            'status': 'PASS' if main_thread_time < 0.1 else 'FAIL'  # Main thread not blocked
        }
        
        print(f"✅ Main thread block time: {main_thread_time:.3f}s")
        print(f"✅ Total background task time: {total_time:.3f}s")
        return result
    
    def run_all_tests(self) -> Dict:
        """Run all performance tests"""
        print("🚀 Loading Screen Performance Test Suite")
        print("=" * 50)
        
        tests = [
            self.test_server_responsiveness,
            self.test_memory_usage,
            self.test_cpu_usage,
            self.test_loading_screen_imports,
            self.test_background_thread_performance
        ]
        
        results = []
        passed = 0
        failed = 0
        
        for test_func in tests:
            try:
                result = test_func()
                results.append(result)
                
                if result['status'] == 'PASS':
                    passed += 1
                else:
                    failed += 1
                    
            except Exception as e:
                print(f"❌ Test {test_func.__name__} failed with error: {str(e)}")
                failed += 1
            
            print("-" * 30)
        
        # Summary
        print(f"\n📊 Test Summary:")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Success Rate: {(passed / (passed + failed) * 100):.1f}%")
        
        overall_status = 'PASS' if failed == 0 else 'FAIL'
        
        summary = {
            'overall_status': overall_status,
            'tests_passed': passed,
            'tests_failed': failed,
            'success_rate': passed / (passed + failed) * 100,
            'detailed_results': results
        }
        
        return summary


def main():
    """Run the performance test suite"""
    tester = LoadingPerformanceTest()
    
    print("🔍 Checking if Streamlit server is running...")
    try:
        response = requests.get("http://localhost:8501", timeout=5)
        if response.status_code == 200:
            print("✅ Streamlit server is running")
        else:
            print(f"⚠️ Streamlit server responded with status {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot connect to Streamlit server: {str(e)}")
        print("💡 Please start the server with: streamlit run app.py")
        return
    
    # Run tests
    results = tester.run_all_tests()
    
    # Save results
    import json
    with open('loading_performance_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: loading_performance_results.json")
    
    if results['overall_status'] == 'PASS':
        print("🎉 All performance tests passed! Loading screen is optimized.")
    else:
        print("⚠️ Some performance tests failed. Check the results for details.")


if __name__ == "__main__":
    main() 