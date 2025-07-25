#!/usr/bin/env python3
"""
Test the improved file path handling
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mdfmcp.server import MdfMcpServer

async def test_path_resolution():
    """Test various path resolution scenarios"""
    server = MdfMcpServer()
    
    # Test cases
    test_cases = [
        # Relative path (should work if file exists in current directory)
        "test_automotive_data.mf4",
        
        # Just filename
        "test_automotive_data.mf4",
        
        # Non-existent file (should show helpful error)
        "nonexistent.mf4",
        
        # Case mismatch (should work)
        "TEST_AUTOMOTIVE_DATA.MF4",
    ]
    
    print("Testing improved file path handling:\n")
    
    for i, test_path in enumerate(test_cases, 1):
        print(f"Test {i}: '{test_path}'")
        try:
            args = {"file_path": test_path}
            result = await server._handle_open_mdf(args)
            
            # Extract text content
            if result and hasattr(result[0], 'text'):
                response = result[0].text
                if "session_id" in response:
                    print("✅ Success - File opened")
                    # Parse session_id to close it
                    import json
                    session_data = json.loads(response)
                    session_id = session_data["session_id"]
                    await server._handle_close_mdf({"session_id": session_id})
                else:
                    print(f"❌ Failed - {response[:100]}...")
            else:
                print("❌ No response")
                
        except Exception as e:
            print(f"❌ Exception - {e}")
        
        print()

if __name__ == "__main__":
    asyncio.run(test_path_resolution())