#!/usr/bin/env python3
"""
🔍 Loading Screen UI Test
Tests the loading screen UI behavior and responsiveness without browser tools.
"""

import requests
import time
import json
from typing import Dict, List


class LoadingScreenUITest:
    """Test the loading screen UI behavior"""
    
    def __init__(self, streamlit_url: str = "http://localhost:8501"):
        self.streamlit_url = streamlit_url
        
    def test_page_load_speed(self) -> Dict:
        """Test how quickly the page loads"""
        print("🚀 Testing page load speed...")
        
        load_times = []
        for i in range(3):
            start_time = time.time()
            try:
                response = requests.get(self.streamlit_url, timeout=10)
                load_time = time.time() - start_time
                load_times.append(load_time)
                
                # Check if response contains expected content
                content_size = len(response.content)
                print(f"  Load {i+1}: {load_time:.3f}s (Size: {content_size:,} bytes)")
                
            except Exception as e:
                print(f"  Load {i+1}: FAILED - {str(e)}")
                load_times.append(float('inf'))
        
        avg_load_time = sum(load_times) / len(load_times)
        
        result = {
            'test': 'page_load_speed',
            'avg_load_time': avg_load_time,
            'all_load_times': load_times,
            'status': 'PASS' if avg_load_time < 1.0 else 'FAIL'
        }
        
        print(f"✅ Average load time: {avg_load_time:.3f}s")
        return result
    
    def test_streamlit_health(self) -> Dict:
        """Test Streamlit health endpoint"""
        print("🏥 Testing Streamlit health...")
        
        try:
            health_url = f"{self.streamlit_url}/_stcore/health"
            response = requests.get(health_url, timeout=5)
            
            result = {
                'test': 'streamlit_health',
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds(),
                'status': 'PASS' if response.status_code == 200 else 'FAIL'
            }
            
            print(f"✅ Health check: {response.status_code} ({response.elapsed.total_seconds():.3f}s)")
            
        except Exception as e:
            result = {
                'test': 'streamlit_health',
                'error': str(e),
                'status': 'FAIL'
            }
            print(f"❌ Health check failed: {str(e)}")
        
        return result
    
    def test_static_resources(self) -> Dict:
        """Test if static resources load quickly"""
        print("📦 Testing static resources...")
        
        # Common Streamlit static resources
        static_resources = [
            "/_stcore/static/css/bootstrap.min.css",
            "/_stcore/static/js/bootstrap.bundle.min.js"
        ]
        
        resource_times = []
        for resource in static_resources:
            try:
                start_time = time.time()
                response = requests.get(f"{self.streamlit_url}{resource}", timeout=5)
                load_time = time.time() - start_time
                resource_times.append(load_time)
                
                print(f"  {resource}: {load_time:.3f}s ({response.status_code})")
                
            except Exception as e:
                print(f"  {resource}: FAILED - {str(e)}")
                resource_times.append(float('inf'))
        
        avg_resource_time = sum(resource_times) / len(resource_times) if resource_times else float('inf')
        
        result = {
            'test': 'static_resources',
            'avg_resource_time': avg_resource_time,
            'resource_times': resource_times,
            'status': 'PASS' if avg_resource_time < 0.5 else 'FAIL'
        }
        
        print(f"✅ Average resource load time: {avg_resource_time:.3f}s")
        return result
    
    def test_loading_screen_accessibility(self) -> Dict:
        """Test basic accessibility of the loading screen"""
        print("♿ Testing loading screen accessibility...")
        
        try:
            response = requests.get(self.streamlit_url, timeout=10)
            content = response.text.lower()
            
            # Check for accessibility indicators
            accessibility_checks = {
                'has_title': '<title>' in content,
                'has_meta_viewport': 'viewport' in content,
                'has_lang_attribute': 'lang=' in content,
                'has_semantic_elements': any(tag in content for tag in ['<main>', '<section>', '<article>', '<header>']),
                'has_aria_labels': 'aria-' in content
            }
            
            passed_checks = sum(accessibility_checks.values())
            total_checks = len(accessibility_checks)
            
            result = {
                'test': 'accessibility',
                'checks': accessibility_checks,
                'passed_checks': passed_checks,
                'total_checks': total_checks,
                'score': (passed_checks / total_checks) * 100,
                'status': 'PASS' if passed_checks >= total_checks * 0.6 else 'FAIL'
            }
            
            print(f"✅ Accessibility score: {result['score']:.1f}% ({passed_checks}/{total_checks})")
            
        except Exception as e:
            result = {
                'test': 'accessibility',
                'error': str(e),
                'status': 'FAIL'
            }
            print(f"❌ Accessibility test failed: {str(e)}")
        
        return result
    
    def test_loading_screen_performance_indicators(self) -> Dict:
        """Test for performance indicators in the HTML"""
        print("⚡ Testing performance indicators...")
        
        try:
            response = requests.get(self.streamlit_url, timeout=10)
            content = response.text.lower()
            
            # Check for performance-related content
            performance_indicators = {
                'has_css_optimization': 'style' in content,
                'has_javascript_defer': 'defer' in content or 'async' in content,
                'has_meta_charset': 'charset=' in content,
                'reasonable_size': len(response.content) < 500000,  # Less than 500KB
                'has_caching_headers': 'cache-control' in str(response.headers).lower()
            }
            
            passed_indicators = sum(performance_indicators.values())
            total_indicators = len(performance_indicators)
            
            result = {
                'test': 'performance_indicators',
                'indicators': performance_indicators,
                'passed_indicators': passed_indicators,
                'total_indicators': total_indicators,
                'content_size': len(response.content),
                'score': (passed_indicators / total_indicators) * 100,
                'status': 'PASS' if passed_indicators >= total_indicators * 0.6 else 'FAIL'
            }
            
            print(f"✅ Performance score: {result['score']:.1f}% ({passed_indicators}/{total_indicators})")
            print(f"✅ Content size: {len(response.content):,} bytes")
            
        except Exception as e:
            result = {
                'test': 'performance_indicators',
                'error': str(e),
                'status': 'FAIL'
            }
            print(f"❌ Performance test failed: {str(e)}")
        
        return result
    
    def run_all_tests(self) -> Dict:
        """Run all UI tests"""
        print("🔍 Loading Screen UI Test Suite")
        print("=" * 50)
        
        tests = [
            self.test_page_load_speed,
            self.test_streamlit_health,
            self.test_static_resources,
            self.test_loading_screen_accessibility,
            self.test_loading_screen_performance_indicators
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
    """Run the UI test suite"""
    tester = LoadingScreenUITest()
    
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
    with open('loading_ui_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: loading_ui_test_results.json")
    
    if results['overall_status'] == 'PASS':
        print("🎉 All UI tests passed! Loading screen UI is working well.")
    else:
        print("⚠️ Some UI tests failed. Check the results for details.")


if __name__ == "__main__":
    main()