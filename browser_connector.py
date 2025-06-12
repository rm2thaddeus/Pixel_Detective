#!/usr/bin/env python3
"""
Browser Connector for MCP Browser Tools
This script starts a browser session and provides the interface for browser automation.
"""

import time
import json
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import threading
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrowserConnector:
    def __init__(self):
        self.driver = None
        self.server = None
        
    def start_browser(self):
        """Start Chrome browser with debugging enabled"""
        try:
            print("🌐 Starting Browser Connector for MCP Browser Tools...")
            
            # Chrome options for MCP compatibility
            chrome_options = Options()
            chrome_options.add_argument("--remote-debugging-port=9222")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            # Enable logging for debugging
            chrome_options.add_experimental_option("useAutomationExtension", False)
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            
            # Set up Chrome driver
            service = Service(ChromeDriverManager().install())
            
            print("🚀 Launching Chrome browser...")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Navigate to a test page
            self.driver.get("https://example.com")
            print("✅ Browser started successfully!")
            print("🔗 Chrome debugging available at: http://localhost:9222")
            print("📱 Browser Tools MCP can now connect to this browser")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            print(f"❌ Failed to start browser")
            return False
    
    def take_screenshot(self, filename="screenshot.png"):
        """Take a screenshot of the current page"""
        if self.driver:
            try:
                screenshot_path = f"screenshots/{filename}"
                self.driver.save_screenshot(screenshot_path)
                print(f"📸 Screenshot saved: {screenshot_path}")
                return screenshot_path
            except Exception as e:
                logger.error(f"Failed to take screenshot: {e}")
                return None
        return None
    
    def get_page_info(self):
        """Get current page information"""
        if self.driver:
            try:
                return {
                    "title": self.driver.title,
                    "url": self.driver.current_url,
                    "page_source_length": len(self.driver.page_source)
                }
            except Exception as e:
                logger.error(f"Failed to get page info: {e}")
                return None
        return None
    
    def navigate_to(self, url):
        """Navigate to a specific URL"""
        if self.driver:
            try:
                self.driver.get(url)
                print(f"🌐 Navigated to: {url}")
                return True
            except Exception as e:
                logger.error(f"Failed to navigate to {url}: {e}")
                return False
        return False
    
    def close(self):
        """Close the browser and cleanup"""
        if self.driver:
            try:
                self.driver.quit()
                print("🔒 Browser closed successfully")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
        
        if self.server:
            try:
                self.server.shutdown()
                print("🔒 Server stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping server: {e}")

def main():
    """Main function to start the browser connector"""
    connector = BrowserConnector()
    
    try:
        # Start the browser
        if connector.start_browser():
            print("\n🎉 Browser Connector is ready!")
            print("📋 Available commands:")
            print("   - Browser Tools MCP can now connect")
            print("   - Chrome DevTools: http://localhost:9222")
            print("   - Press Ctrl+C to stop")
            
            # Keep the script running
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n🛑 Stopping Browser Connector...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        connector.close()
        print("👋 Browser Connector stopped")

if __name__ == "__main__":
    main()