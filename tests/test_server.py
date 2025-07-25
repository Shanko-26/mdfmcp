#!/usr/bin/env python3
"""Tests for MDF MCP Server"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch
import numpy as np

try:
    from asammdf import MDF, Signal
    from src.mdfmcp.server import MdfMcpServer, MdfSession
except ImportError:
    pytest.skip("asammdf not available", allow_module_level=True)

@pytest.fixture
def sample_mdf_file():
    """Create a temporary MDF file for testing"""
    with tempfile.NamedTemporaryFile(suffix='.mf4', delete=False) as tmp:
        # Create simple test signals
        timestamps = np.linspace(0, 10, 1000, dtype=np.float64)
        
        signals = [
            Signal(
                samples=np.sin(2 * np.pi * timestamps).astype(np.float32),
                timestamps=timestamps,
                name="Sine_Wave",
                unit="V",
                comment="Test sine wave"
            ),
            Signal(
                samples=(timestamps * 10).astype(np.float32),
                timestamps=timestamps,
                name="Ramp_Signal",
                unit="A", 
                comment="Test ramp signal"
            ),
            Signal(
                samples=np.random.normal(50, 10, len(timestamps)).astype(np.float32),
                timestamps=timestamps,
                name="Noise_Signal",
                unit="°C",
                comment="Test noise signal"
            )
        ]
        
        with MDF(version='4.10') as mdf:
            mdf.append(signals, comment="Test data")
            mdf.save(tmp.name, overwrite=True)
        
        yield tmp.name
        
        # Cleanup
        Path(tmp.name).unlink(missing_ok=True)

@pytest.fixture
def server():
    """Create MDF MCP Server instance"""
    return MdfMcpServer(max_sessions=5, session_timeout=300)

class TestMdfMcpServer:
    
    def test_server_initialization(self, server):
        """Test server initializes correctly"""
        assert server.max_sessions == 5
        assert server.session_timeout == 300
        assert len(server.sessions) == 0
        assert len(server.tools) > 0
        
        # Check essential tools are present
        tool_names = [tool.name for tool in server.tools]
        assert "open_mdf" in tool_names
        assert "close_mdf" in tool_names
        assert "list_sessions" in tool_names
        assert "plot_signals" in tool_names
    
    @pytest.mark.asyncio
    async def test_open_mdf_file(self, server, sample_mdf_file):
        """Test opening an MDF file"""
        args = {"file_path": sample_mdf_file}
        result = await server._handle_open_mdf(args)
        
        assert len(result) == 1
        response = json.loads(result[0].text)
        
        assert "session_id" in response
        assert response["version"] == "4.10"
        assert response["channels_count"] == 3
        assert len(server.sessions) == 1
    
    @pytest.mark.asyncio
    async def test_open_nonexistent_file(self, server):
        """Test opening non-existent file"""
        args = {"file_path": "/nonexistent/file.mf4"}
        result = await server._handle_open_mdf(args)
        
        assert len(result) == 1
        assert "File not found" in result[0].text
        assert len(server.sessions) == 0
    
    @pytest.mark.asyncio
    async def test_list_sessions(self, server, sample_mdf_file):
        """Test listing sessions"""
        # Open a file first
        await server._handle_open_mdf({"file_path": sample_mdf_file})
        
        # List sessions
        result = await server._handle_list_sessions()
        sessions = json.loads(result[0].text)
        
        assert len(sessions) == 1
        assert "session_id" in sessions[0]
        assert "file" in sessions[0]
        assert sessions[0]["channels_count"] == 3
    
    @pytest.mark.asyncio
    async def test_list_channels(self, server, sample_mdf_file):
        """Test listing channels"""
        # Open file and get session
        open_result = await server._handle_open_mdf({"file_path": sample_mdf_file})
        session_id = json.loads(open_result[0].text)["session_id"]
        
        # List channels
        args = {"session_id": session_id}
        result = await server._handle_list_channels(args)
        channels = json.loads(result[0].text)
        
        assert channels["total_channels"] == 3
        channel_names = [ch["name"] for ch in channels["channels"]]
        assert "Sine_Wave" in channel_names
        assert "Ramp_Signal" in channel_names
        assert "Noise_Signal" in channel_names
    
    @pytest.mark.asyncio
    async def test_list_channels_with_pattern(self, server, sample_mdf_file):
        """Test listing channels with pattern filter"""
        # Open file
        open_result = await server._handle_open_mdf({"file_path": sample_mdf_file})
        session_id = json.loads(open_result[0].text)["session_id"]
        
        # List channels with pattern
        args = {"session_id": session_id, "pattern": "sine"}
        result = await server._handle_list_channels(args)
        channels = json.loads(result[0].text)
        
        assert channels["total_channels"] == 1
        assert channels["channels"][0]["name"] == "Sine_Wave"
    
    @pytest.mark.asyncio
    async def test_calculate_statistics(self, server, sample_mdf_file):
        """Test calculating signal statistics"""
        # Open file
        open_result = await server._handle_open_mdf({"file_path": sample_mdf_file})
        session_id = json.loads(open_result[0].text)["session_id"]
        
        # Calculate statistics
        args = {"session_id": session_id, "channels": ["Sine_Wave", "Ramp_Signal"]}
        result = await server._handle_calculate_statistics(args)
        stats = json.loads(result[0].text)
        
        # Check sine wave stats
        sine_stats = stats["Sine_Wave"]
        assert sine_stats["unit"] == "V"
        assert sine_stats["samples"] == 1000
        assert abs(sine_stats["mean"]) < 0.1  # Sine wave should have ~0 mean
        assert -1.1 < sine_stats["min"] < -0.9  # Min should be ~-1
        assert 0.9 < sine_stats["max"] < 1.1   # Max should be ~1
        
        # Check ramp signal stats
        ramp_stats = stats["Ramp_Signal"]
        assert ramp_stats["unit"] == "A"
        assert ramp_stats["min"] == 0.0  # Ramp starts at 0
        assert 95 < ramp_stats["max"] < 105  # Ramp ends at ~100
    
    @pytest.mark.asyncio
    async def test_mdf_get_signal(self, server, sample_mdf_file):
        """Test getting signal data"""
        # Open file
        open_result = await server._handle_open_mdf({"file_path": sample_mdf_file})
        session_id = json.loads(open_result[0].text)["session_id"]
        
        # Get signal
        args = {"session_id": session_id, "name": "Sine_Wave"}
        result = await server._handle_mdf_method("get", args)
        signal_data = json.loads(result[0].text)
        
        assert signal_data["name"] == "Sine_Wave"
        assert signal_data["unit"] == "V"
        assert signal_data["samples"] == 1000
        assert len(signal_data["first_values"]) == 10
        assert len(signal_data["last_values"]) == 10
    
    @pytest.mark.asyncio
    async def test_close_session(self, server, sample_mdf_file):
        """Test closing a session"""
        # Open file
        open_result = await server._handle_open_mdf({"file_path": sample_mdf_file})
        session_id = json.loads(open_result[0].text)["session_id"]
        
        assert len(server.sessions) == 1
        
        # Close session
        args = {"session_id": session_id}
        result = await server._handle_close_mdf(args)
        
        assert f"Closed session: {session_id}" in result[0].text
        assert len(server.sessions) == 0
    
    @pytest.mark.asyncio
    async def test_invalid_session_id(self, server):
        """Test using invalid session ID"""
        args = {"session_id": "invalid_id", "channels": ["test"]}
        result = await server._handle_calculate_statistics(args)
        
        assert "Session not found" in result[0].text
    
    @pytest.mark.asyncio
    async def test_max_sessions_limit(self, server, sample_mdf_file):
        """Test maximum sessions limit"""
        # Try to open more than max_sessions
        sessions_opened = 0
        for i in range(server.max_sessions + 1):
            result = await server._handle_open_mdf({"file_path": sample_mdf_file})
            if "session_id" in result[0].text:
                sessions_opened += 1
        
        assert sessions_opened == server.max_sessions
    
    def test_session_management(self, server):
        """Test session object functionality"""
        from unittest.mock import Mock
        
        # Create mock MDF
        mock_mdf = Mock()
        session = MdfSession(
            id="test_123",
            mdf=mock_mdf,
            file_path="/test/file.mf4",
            created_at=1000.0,
            last_accessed=1000.0,
            metadata={"test": "data"}
        )
        
        # Test touch method
        session.touch()
        assert session.last_accessed > 1000.0
        
        # Test to_dict method
        session_dict = session.to_dict()
        assert session_dict["id"] == "test_123"
        assert session_dict["file_path"] == "/test/file.mf4"
        assert session_dict["metadata"]["test"] == "data"
    
    def test_parameter_schema_generation(self, server):
        """Test parameter schema generation from method signatures"""
        from inspect import Parameter
        
        # Test integer parameter
        param = Parameter('index', Parameter.POSITIONAL_OR_KEYWORD, annotation=int)
        schema = server._parameter_to_schema('index', param)
        assert schema["type"] == "number"
        
        # Test boolean parameter
        param = Parameter('raw', Parameter.POSITIONAL_OR_KEYWORD, annotation=bool)
        schema = server._parameter_to_schema('raw', param)
        assert schema["type"] == "boolean"
        
        # Test list parameter
        param = Parameter('channels', Parameter.POSITIONAL_OR_KEYWORD, annotation=list)
        schema = server._parameter_to_schema('channels', param)
        assert schema["type"] == "array"
        
        # Test parameter with default
        param = Parameter('test', Parameter.POSITIONAL_OR_KEYWORD, default=42)
        schema = server._parameter_to_schema('test', param)
        assert schema["default"] == 42
    
    def test_cleanup_old_sessions(self, server):
        """Test cleanup of old sessions"""
        from unittest.mock import Mock
        import time
        
        # Create old session
        old_time = time.time() - server.session_timeout - 100
        mock_mdf = Mock()
        old_session = MdfSession(
            id="old_session",
            mdf=mock_mdf,
            file_path="/test.mf4",
            created_at=old_time,
            last_accessed=old_time,
            metadata={}
        )
        server.sessions["old_session"] = old_session
        
        # Create recent session
        recent_session = MdfSession(
            id="recent_session", 
            mdf=Mock(),
            file_path="/test2.mf4",
            created_at=time.time(),
            last_accessed=time.time(),
            metadata={}
        )
        server.sessions["recent_session"] = recent_session
        
        assert len(server.sessions) == 2
        
        # Cleanup old sessions
        server._cleanup_old_sessions()
        
        assert len(server.sessions) == 1
        assert "recent_session" in server.sessions
        assert "old_session" not in server.sessions

if __name__ == "__main__":
    pytest.main([__file__, "-v"])