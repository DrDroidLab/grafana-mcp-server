#!/usr/bin/env python3
"""
Manual test script to test Grafana connection
Save as test_grafana_connection.py in your project root
"""

import os
import sys
import logging

# Add src to Python path BEFORE importing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from grafana_mcp_server.processor.grafana_processor import GrafanaApiProcessor


# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_grafana_connection():
    """Test connection to Grafana"""
    
    print("🚀 Testing Grafana MCP Server Connection")
    print("=" * 50)
    
    # Configuration - you can modify these or use environment variables
    grafana_host = "https://microservices-grafana.demo.drdroid.io/"
    grafana_api_key = "glsa_YOXrsrlG9WLeOWVSypBjrIl1l7vnh4X0_20f72563"
    ssl_verify = "true"
    
    print(f"Host: {grafana_host}")
    print(f"SSL Verify: {ssl_verify}")
    print("Auth Method: API Key")
    
    processor = GrafanaApiProcessor(
        grafana_host=grafana_host,
        grafana_api_key=grafana_api_key,
        ssl_verify=ssl_verify
    )
    
    print("\n📡 Testing connection...")
    
    try:
        result = processor.test_connection()
        if result:
            print("✅ SUCCESS: Connected to Grafana API!")
            print("🎉 The Grafana MCP Server can communicate with your Grafana instance.")
        else:
            print("❌ FAILED: Could not connect to Grafana API")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Check if Grafana is running and accessible")
        print("2. Verify your credentials (API key or username/password)")
        print("3. Check if the URL is correct")
        print("4. For HTTPS with self-signed certs, try GRAFANA_SSL_VERIFY=false")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    # You can set these environment variables or modify the values above
    print("💡 Configuration options:")
    print("Set environment variables:")
    print("  export GRAFANA_HOST='http://localhost:3000'")
    print("  export GRAFANA_API_KEY='your-api-key'  # OR")
    print("  export GRAFANA_USERNAME='admin'")
    print("  export GRAFANA_PASSWORD='admin'")
    print("  export GRAFANA_SSL_VERIFY='true'")
    print()
    
    test_grafana_connection()