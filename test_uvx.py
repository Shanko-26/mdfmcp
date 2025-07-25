#!/usr/bin/env python3
"""
Test script to verify uvx installation works correctly
"""

import subprocess
import json
import sys

def test_mcp_communication():
    """Test basic MCP communication"""
    # Test message
    init_msg = {
        "jsonrpc": "2.0", 
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "clientInfo": {"name": "test", "version": "1.0"}
        },
        "id": 1
    }
    
    # Run server with test message
    try:
        result = subprocess.run([
            sys.executable, "-m", "mdfmcp.server"
        ], 
        input=json.dumps(init_msg),
        capture_output=True,
        text=True,
        timeout=5,
        env={"PYTHONPATH": "/Users/shanko/Git/mdfmcp/src"}
        )
        
        if result.returncode == 0:
            try:
                response = json.loads(result.stdout.strip())
                if response.get("result", {}).get("serverInfo", {}).get("name") == "mdfmcp":
                    print("✅ MCP communication test PASSED")
                    return True
                else:
                    print(f"❌ Unexpected response: {response}")
            except json.JSONDecodeError:
                print(f"❌ Invalid JSON response: {result.stdout}")
        else:
            print(f"❌ Server failed with code {result.returncode}")
            print(f"STDERR: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("❌ Server timed out")
    except Exception as e:
        print(f"❌ Error: {e}")
        
    return False

if __name__ == "__main__":
    print("Testing MCP Server Communication...")
    success = test_mcp_communication()
    sys.exit(0 if success else 1)