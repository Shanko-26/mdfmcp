#!/usr/bin/env python3
"""
Test workspace-focused file search functionality
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mdfmcp.server import MdfMcpServer

async def test_workspace_search():
    """Test workspace-focused file search"""
    server = MdfMcpServer()
    
    test_cases = [
        ("vehicle_test.mf4", "Should find in data/ folder"),
        ("engine_data.mf4", "Should find in measurements/ folder"), 
        ("test_automotive_data.mf4", "Should find in current directory"),
        ("nonexistent.mf4", "Should show helpful error with workspace files"),
    ]
    
    print("Testing workspace-focused file search:\n")
    
    for filename, description in test_cases:
        print(f"Testing: {filename}")
        print(f"Expected: {description}")
        
        try:
            args = {"file_path": filename}
            result = await server._handle_open_mdf(args)
            
            if result and hasattr(result[0], 'text'):
                response = result[0].text
                if "session_id" in response:
                    print("✅ SUCCESS - File found and opened")
                    # Parse and close session
                    import json
                    session_data = json.loads(response)
                    print(f"   File: {session_data.get('file', 'unknown')}")
                    await server._handle_close_mdf({"session_id": session_data["session_id"]})
                else:
                    print("❌ FAILED")
                    # Show first part of error message
                    print(f"   Error: {response[:150]}...")
            else:
                print("❌ No response")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_workspace_search())