#!/usr/bin/env python3
"""
Manual testing script for MDF MCP Server
This script creates sample data and tests basic server functionality
"""

import json
import asyncio
import tempfile
from pathlib import Path
import sys

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from mdfmcp.server import MdfMcpServer
    from asammdf import MDF, Signal
    import numpy as np
except ImportError as e:
    print(f"Import error: {e}")
    print("Please install requirements: pip install -r requirements.txt")
    sys.exit(1)

def create_test_file():
    """Create a temporary test MDF file"""
    with tempfile.NamedTemporaryFile(suffix='.mf4', delete=False) as tmp:
        print(f"Creating test file: {tmp.name}")
        
        # Generate test signals
        duration = 30.0  # seconds
        sample_rate = 100.0  # Hz
        time_samples = int(duration * sample_rate)
        timestamps = np.linspace(0, duration, time_samples, dtype=np.float64)
        
        signals = [
            Signal(
                samples=(50 + 30 * np.sin(2 * np.pi * timestamps / 5)).astype(np.float32),
                timestamps=timestamps,
                name="Vehicle_Speed", 
                unit="km/h",
                comment="Simulated vehicle speed"
            ),
            Signal(
                samples=(2000 + 1500 * np.sin(2 * np.pi * timestamps / 8)).astype(np.float32),
                timestamps=timestamps,
                name="Engine_RPM",
                unit="RPM", 
                comment="Engine rotational speed"
            ),
            Signal(
                samples=(85 + 10 * np.tanh((timestamps - 5) / 5) + np.random.normal(0, 1, time_samples)).astype(np.float32),
                timestamps=timestamps,
                name="Engine_Temp",
                unit="°C",
                comment="Engine temperature with warmup"
            )
        ]
        
        with MDF(version='4.10') as mdf:
            mdf.append(signals, comment="Manual test data")
            mdf.save(tmp.name, overwrite=True)
        
        return tmp.name

async def test_server_functionality():
    """Test main server functionality"""
    print("=" * 60)
    print("MDF MCP Server Manual Test")
    print("=" * 60)
    
    # Create test file
    test_file = create_test_file()
    print(f"Test file size: {Path(test_file).stat().st_size / 1024:.1f} KB")
    
    try:
        # Initialize server
        print("\n1. Initializing server...")
        server = MdfMcpServer(max_sessions=5)
        print(f"   Server initialized with {len(server.tools)} tools")
        
        # Test file opening
        print("\n2. Opening MDF file...")
        open_args = {"file_path": test_file}
        result = await server._handle_open_mdf(open_args)
        response = json.loads(result[0].text)
        session_id = response["session_id"]
        print(f"   Session created: {session_id}")
        print(f"   Channels: {response['channels_count']}")
        print(f"   Version: {response['version']}")
        
        # Test listing sessions
        print("\n3. Listing sessions...")
        result = await server._handle_list_sessions()
        sessions = json.loads(result[0].text)
        print(f"   Active sessions: {len(sessions)}")
        
        # Test listing channels
        print("\n4. Listing channels...")
        list_args = {"session_id": session_id}
        result = await server._handle_list_channels(list_args)
        channels_info = json.loads(result[0].text)
        print(f"   Total channels: {channels_info['total_channels']}")
        for ch in channels_info['channels']:
            print(f"   - {ch['name']} [{ch['unit']}]: {ch['comment']}")
        
        # Test getting signal data
        print("\n5. Getting signal data...")
        get_args = {"session_id": session_id, "name": "Vehicle_Speed"}
        result = await server._handle_mdf_method("get", get_args)
        signal_info = json.loads(result[0].text)
        print(f"   Signal: {signal_info['name']}")
        print(f"   Unit: {signal_info['unit']}")
        print(f"   Samples: {signal_info['samples']}")
        print(f"   Time range: {signal_info['time_range'][0]:.2f} - {signal_info['time_range'][1]:.2f} s")
        print(f"   Sample rate: {signal_info['sample_rate']:.1f} Hz")
        
        # Test statistics calculation
        print("\n6. Calculating statistics...")
        stats_args = {
            "session_id": session_id, 
            "channels": ["Vehicle_Speed", "Engine_RPM", "Engine_Temp"]
        }
        result = await server._handle_calculate_statistics(stats_args)
        stats = json.loads(result[0].text)
        
        for channel, data in stats.items():
            if "error" not in data:
                print(f"   {channel} [{data['unit']}]:")
                print(f"     Mean: {data['mean']:.2f}, Std: {data['std']:.2f}")
                print(f"     Range: {data['min']:.2f} - {data['max']:.2f}")
        
        # Test plotting (without displaying)
        print("\n7. Testing plot generation...")
        plot_args = {
            "session_id": session_id,
            "channels": ["Vehicle_Speed", "Engine_RPM"],
            "subplot": True
        }
        result = await server._handle_plot_signals(plot_args)
        print(f"   Plot generated successfully (image + {len(result)-1} text responses)")
        if len(result) > 1:
            print(f"   Message: {result[1].text}")
        
        # Test filtering
        print("\n8. Testing channel filtering...")
        filter_args = {
            "session_id": session_id,
            "channels": ["Vehicle_Speed", "Engine_RPM"]
        }
        result = await server._handle_mdf_method("filter", filter_args)
        filter_response = json.loads(result[0].text)
        new_session_id = filter_response["new_session_id"]
        print(f"   New filtered session: {new_session_id}")
        print(f"   Channels in filtered session: {filter_response['channels']}")
        
        # Test export
        print("\n9. Testing data export...")
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as export_file:
            export_args = {
                "session_id": session_id,
                "fmt": "csv",
                "filename": export_file.name,
                "channels": ["Vehicle_Speed", "Engine_RPM"]
            }
            result = await server._handle_mdf_method("export", export_args)
            export_response = json.loads(result[0].text)
            print(f"   Export status: {export_response['status']}")
            print(f"   File: {export_response['filename']}")
            print(f"   File size: {Path(export_file.name).stat().st_size / 1024:.1f} KB")
            
            # Cleanup export file
            Path(export_file.name).unlink(missing_ok=True)
        
        # Test closing sessions
        print("\n10. Closing sessions...")
        for sid in [session_id, new_session_id]:
            close_args = {"session_id": sid}
            result = await server._handle_close_mdf(close_args)
            print(f"    {result[0].text}")
        
        # Verify sessions are closed
        result = await server._handle_list_sessions()
        sessions = json.loads(result[0].text)
        print(f"    Active sessions after cleanup: {len(sessions)}")
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup test file
        Path(test_file).unlink(missing_ok=True)
        print(f"\nCleaned up test file: {test_file}")

def test_tool_generation():
    """Test tool generation and introspection"""
    print("\n" + "=" * 60)
    print("Testing Tool Generation")
    print("=" * 60)
    
    server = MdfMcpServer()
    
    print(f"Total tools generated: {len(server.tools)}")
    print("\nTool categories:")
    
    # Categorize tools
    session_tools = [t for t in server.tools if not t.name.startswith("mdf_")]
    mdf_tools = [t for t in server.tools if t.name.startswith("mdf_")]
    
    print(f"  Session management: {len(session_tools)} tools")
    for tool in session_tools:
        print(f"    - {tool.name}: {tool.description}")
    
    print(f"  MDF methods: {len(mdf_tools)} tools")
    for tool in mdf_tools:
        required_params = tool.inputSchema.get("required", [])
        print(f"    - {tool.name}: {len(required_params)} required params")
    
    print(f"\nAuto-mapped MDF methods: {len(server.EXPOSE_METHODS)}")
    for method in server.EXPOSE_METHODS:
        print(f"  - {method}")

if __name__ == "__main__":
    print("MDF MCP Server Manual Test Suite")
    print("This will create temporary test files and test server functionality")
    
    # Test tool generation first
    test_tool_generation()
    
    # Test server functionality
    asyncio.run(test_server_functionality())
    
    print("\nTo test with a real MCP client:")
    print("1. Start server: python -m mdfmcp.server")
    print("2. Configure your MCP client to use the server")
    print("3. Try commands like: open_mdf, list_channels, plot_signals")