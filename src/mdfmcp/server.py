#!/usr/bin/env python3
"""MDF MCP Server - Production-ready implementation"""

import asyncio
import inspect
import json
import logging
import time
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
import uuid
import io
import base64

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, Resource, LoggingLevel

try:
    from asammdf import MDF, Signal
    import numpy as np
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Please install: pip install asammdf numpy pandas matplotlib")
    raise

# Configure logging - avoid stderr output for MCP compatibility  
logger = logging.getLogger(__name__)

@dataclass
class MdfSession:
    """Represents an active MDF file session"""
    id: str
    mdf: MDF
    file_path: Optional[str]
    created_at: float
    last_accessed: float
    metadata: Dict[str, Any]
    
    def touch(self):
        """Update last access time"""
        self.last_accessed = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "file_path": self.file_path,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "metadata": self.metadata
        }

class MdfMcpServer:
    """MCP Server for ASAM MDF file analysis"""
    
    # Core MDF methods to expose
    EXPOSE_METHODS = [
        'get', 'select', 'get_channel_data', 'get_channel_comment',
        'get_channel_unit', 'get_master', 'to_dataframe',
        'cut', 'filter', 'resample', 'export', 'save', 'convert',
        'iter_channels', 'iter_groups', 'get_group'
    ]
    
    # Methods requiring special handling
    SPECIAL_HANDLERS = {
        'get': '_handle_get_signal',
        'select': '_handle_select_signals',
        'to_dataframe': '_handle_to_dataframe',
        'export': '_handle_export',
        'iter_channels': '_handle_iter_channels',
        'cut': '_handle_cut',
        'filter': '_handle_filter',
        'resample': '_handle_resample'
    }
    
    def __init__(self, max_sessions: int = 10, session_timeout: int = 3600):
        self.server = Server("mdfmcp")
        self.sessions: Dict[str, MdfSession] = {}
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout
        self.tools: List[Tool] = []
        
        self._setup_logging()
        self._generate_tools()
        self._setup_handlers()
    
    def _setup_logging(self):
        """Configure server logging for MCP compatibility"""
        # MCP uses stderr for protocol communication, so we must avoid stderr output
        # Use only file logging or null handler to prevent interference
        root_logger = logging.getLogger()
        root_logger.handlers.clear()  # Remove default handlers
        
        # Add null handler to prevent any stderr output
        null_handler = logging.NullHandler()
        root_logger.addHandler(null_handler)
        root_logger.setLevel(logging.WARNING)  # Only critical errors
        
        # Optional: Add file logging if needed for debugging
        # file_handler = logging.FileHandler('/tmp/mdfmcp.log')
        # file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        # root_logger.addHandler(file_handler)
    
    def _generate_tools(self):
        """Generate MCP tools from MDF methods and custom tools"""
        
        # Session management tools
        self.tools.extend([
            Tool(
                name="open_mdf",
                description="Open an MDF file and create a new session",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the MDF file"
                        },
                        "memory": {
                            "type": "string",
                            "enum": ["full", "low", "minimum"],
                            "description": "Memory usage mode",
                            "default": "full"
                        }
                    },
                    "required": ["file_path"]
                }
            ),
            Tool(
                name="close_mdf",
                description="Close an MDF session and free resources",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"}
                    },
                    "required": ["session_id"]
                }
            ),
            Tool(
                name="list_sessions",
                description="List all active MDF sessions",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="get_file_info",
                description="Get detailed information about an MDF file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"}
                    },
                    "required": ["session_id"]
                }
            ),
            Tool(
                name="list_channels",
                description="List all channels in the MDF file with filtering",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "pattern": {
                            "type": "string",
                            "description": "Regex pattern to filter channels"
                        },
                        "group": {
                            "type": "number",
                            "description": "Specific group index"
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            Tool(
                name="plot_signals",
                description="Create a plot of one or more signals",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "channels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Channel names to plot"
                        },
                        "start_time": {"type": "number"},
                        "end_time": {"type": "number"},
                        "subplot": {
                            "type": "boolean",
                            "description": "Create subplots for each signal",
                            "default": False
                        }
                    },
                    "required": ["session_id", "channels"]
                }
            ),
            Tool(
                name="calculate_statistics",
                description="Calculate statistics for one or more channels",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "channels": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "start_time": {"type": "number"},
                        "end_time": {"type": "number"}
                    },
                    "required": ["session_id", "channels"]
                }
            )
        ])
        
        # Auto-generate tools from MDF methods
        for method_name in self.EXPOSE_METHODS:
            if hasattr(MDF, method_name):
                method = getattr(MDF, method_name)
                if callable(method) and not method_name.startswith('_'):
                    tool = self._create_tool_from_method(method_name, method)
                    if tool:
                        self.tools.append(tool)
    
    def _create_tool_from_method(self, name: str, method) -> Optional[Tool]:
        """Create MCP tool from MDF method using introspection"""
        try:
            sig = inspect.signature(method)
            doc = inspect.getdoc(method) or ""
            
            # Extract description from docstring
            description = doc.split('\n')[0] if doc else f"MDF.{name} method"
            if len(description) > 100:
                description = description[:97] + "..."
            
            properties = {
                "session_id": {
                    "type": "string",
                    "description": "MDF session identifier"
                }
            }
            required = ["session_id"]
            
            # Parse parameters
            for param_name, param in sig.parameters.items():
                if param_name in ('self', 'cls'):
                    continue
                
                prop = self._parameter_to_schema(param_name, param)
                properties[param_name] = prop
                
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)
            
            # Special cases
            if name == 'export':
                properties['fmt'] = {
                    "type": "string",
                    "enum": ["csv", "hdf5", "mat", "parquet"],
                    "description": "Export format"
                }
                required.append('fmt')
            
            return Tool(
                name=f"mdf_{name}",
                description=description,
                inputSchema={
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            )
            
        except Exception as e:
            logger.warning(f"Failed to create tool for {name}: {e}")
            return None
    
    def _parameter_to_schema(self, name: str, param) -> Dict[str, Any]:
        """Convert function parameter to JSON schema"""
        schema = {"description": f"Parameter: {name}"}
        
        # Type inference from annotation
        if param.annotation != inspect.Parameter.empty:
            ann = param.annotation
            if ann == int or str(ann) == 'int':
                schema["type"] = "number"
            elif ann == bool or str(ann) == 'bool':
                schema["type"] = "boolean"
            elif ann == list or str(ann).startswith('List'):
                schema["type"] = "array"
                schema["items"] = {"type": "string"}
            elif ann == dict or str(ann).startswith('Dict'):
                schema["type"] = "object"
            else:
                schema["type"] = "string"
        else:
            # Heuristic type inference
            if any(x in name.lower() for x in ['index', 'group', 'offset']):
                schema["type"] = "number"
            elif any(x in name.lower() for x in ['raw', 'validate', 'copy']):
                schema["type"] = "boolean"
            elif 'channels' in name:
                schema["type"] = "array"
                schema["items"] = {"type": "string"}
            else:
                schema["type"] = "string"
        
        # Add default if present
        if param.default != inspect.Parameter.empty:
            if param.default is not None:
                schema["default"] = param.default
        
        return schema
    
    def _setup_handlers(self):
        """Setup MCP protocol handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return self.tools
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[Any]:
            try:
                # Session management
                if name == "open_mdf":
                    return await self._handle_open_mdf(arguments)
                elif name == "close_mdf":
                    return await self._handle_close_mdf(arguments)
                elif name == "list_sessions":
                    return await self._handle_list_sessions()
                elif name == "get_file_info":
                    return await self._handle_get_file_info(arguments)
                elif name == "list_channels":
                    return await self._handle_list_channels(arguments)
                elif name == "plot_signals":
                    return await self._handle_plot_signals(arguments)
                elif name == "calculate_statistics":
                    return await self._handle_calculate_statistics(arguments)
                
                # Auto-mapped MDF methods
                elif name.startswith("mdf_"):
                    method_name = name[4:]
                    return await self._handle_mdf_method(method_name, arguments)
                
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
                
            except Exception as e:
                logger.error(f"Error in {name}: {e}\n{traceback.format_exc()}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            return [
                Resource(
                    uri="mdf://sessions",
                    name="Active Sessions",
                    mimeType="application/json",
                    description="List of active MDF sessions"
                ),
                Resource(
                    uri="mdf://tools",
                    name="Available Tools",
                    mimeType="application/json",
                    description="Complete list of available MDF tools"
                )
            ]
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            if uri == "mdf://sessions":
                return json.dumps([s.to_dict() for s in self.sessions.values()], indent=2)
            elif uri == "mdf://tools":
                tools_info = [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": list(tool.inputSchema.get("properties", {}).keys())
                    }
                    for tool in self.tools
                ]
                return json.dumps(tools_info, indent=2)
            return json.dumps({"error": "Unknown resource"})
    
    async def _handle_open_mdf(self, args: Dict[str, Any]) -> List[Any]:
        """Open an MDF file"""
        file_path = Path(args["file_path"])
        if not file_path.exists():
            return [TextContent(type="text", text=f"File not found: {file_path}")]
        
        # Check session limit
        if len(self.sessions) >= self.max_sessions:
            # Try to clean up old sessions
            self._cleanup_old_sessions()
            if len(self.sessions) >= self.max_sessions:
                return [TextContent(type="text", text="Maximum sessions reached. Please close some sessions.")]
        
        try:
            memory = args.get("memory", "full")
            mdf = MDF(str(file_path), memory=memory)
            
            session_id = f"mdf_{uuid.uuid4().hex[:8]}"
            metadata = {
                "version": mdf.version,
                "channels_count": len(mdf.channels_db) if hasattr(mdf, 'channels_db') else 0,
                "groups_count": len(mdf.groups) if hasattr(mdf, 'groups') else 0,
                "file_size_mb": file_path.stat().st_size / (1024 * 1024),
                "memory_mode": memory
            }
            
            session = MdfSession(
                id=session_id,
                mdf=mdf,
                file_path=str(file_path),
                created_at=time.time(),
                last_accessed=time.time(),
                metadata=metadata
            )
            
            self.sessions[session_id] = session
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "session_id": session_id,
                    "file": str(file_path.name),
                    **metadata
                }, indent=2)
            )]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to open MDF: {str(e)}")]
    
    async def _handle_close_mdf(self, args: Dict[str, Any]) -> List[Any]:
        """Close an MDF session"""
        session_id = args["session_id"]
        if session_id not in self.sessions:
            return [TextContent(type="text", text=f"Session not found: {session_id}")]
        
        session = self.sessions[session_id]
        try:
            session.mdf.close()
        except:
            pass
        
        del self.sessions[session_id]
        return [TextContent(type="text", text=f"Closed session: {session_id}")]
    
    async def _handle_list_sessions(self) -> List[Any]:
        """List all active sessions"""
        sessions_list = []
        for session in self.sessions.values():
            info = {
                "session_id": session.id,
                "file": Path(session.file_path).name if session.file_path else "unknown",
                "age_minutes": round((time.time() - session.created_at) / 60, 1),
                "idle_minutes": round((time.time() - session.last_accessed) / 60, 1),
                **session.metadata
            }
            sessions_list.append(info)
        
        return [TextContent(type="text", text=json.dumps(sessions_list, indent=2))]
    
    async def _handle_get_file_info(self, args: Dict[str, Any]) -> List[Any]:
        """Get detailed file information"""
        session = self._get_session(args["session_id"])
        if isinstance(session, list):
            return session
        
        mdf = session.mdf
        info = {
            "session_id": session.id,
            "file_path": session.file_path,
            "version": mdf.version,
            "program": getattr(mdf.header, 'program_identification', 'Unknown'),
            "start_time": str(getattr(mdf.header, 'start_time', 'Unknown')),
            "comment": getattr(mdf.header, 'comment', ''),
            "groups": len(mdf.groups) if hasattr(mdf, 'groups') else 0,
            "channels_total": len(mdf.channels_db) if hasattr(mdf, 'channels_db') else 0,
            "attachments": len(mdf.attachments) if hasattr(mdf, 'attachments') else 0
        }
        
        return [TextContent(type="text", text=json.dumps(info, indent=2))]
    
    async def _handle_list_channels(self, args: Dict[str, Any]) -> List[Any]:
        """List channels with filtering"""
        session = self._get_session(args["session_id"])
        if isinstance(session, list):
            return session
        
        mdf = session.mdf
        channels = []
        pattern = args.get("pattern")
        group_filter = args.get("group")
        
        import re
        regex = re.compile(pattern, re.IGNORECASE) if pattern else None
        
        for i, group in enumerate(mdf.groups):
            if group_filter is not None and i != group_filter:
                continue
                
            for j, channel in enumerate(group.channels):
                if hasattr(channel, 'name'):
                    name = channel.name
                    if regex and not regex.search(name):
                        continue
                    
                    channels.append({
                        "name": name,
                        "group": i,
                        "index": j,
                        "unit": getattr(channel, 'unit', ''),
                        "comment": getattr(channel, 'comment', '')
                    })
        
        result = {
            "total_channels": len(channels),
            "channels": channels[:100]  # Limit output
        }
        
        if len(channels) > 100:
            result["note"] = f"Showing first 100 of {len(channels)} channels"
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _handle_plot_signals(self, args: Dict[str, Any]) -> List[Any]:
        """Create signal plots"""
        session = self._get_session(args["session_id"])
        if isinstance(session, list):
            return session
        
        mdf = session.mdf
        channels = args["channels"]
        subplot = args.get("subplot", False)
        
        try:
            if subplot and len(channels) > 1:
                fig, axes = plt.subplots(len(channels), 1, figsize=(10, 4*len(channels)), sharex=True)
                if len(channels) == 1:
                    axes = [axes]
            else:
                fig, ax = plt.subplots(figsize=(10, 6))
                axes = [ax] * len(channels)
            
            for idx, (channel_name, ax) in enumerate(zip(channels, axes)):
                signal = mdf.get(channel_name)
                
                # Time filtering
                start = args.get("start_time", signal.timestamps[0])
                end = args.get("end_time", signal.timestamps[-1])
                mask = (signal.timestamps >= start) & (signal.timestamps <= end)
                
                ax.plot(signal.timestamps[mask], signal.samples[mask], 
                       label=f"{channel_name} [{signal.unit}]" if not subplot else None)
                
                if subplot:
                    ax.set_ylabel(f"{channel_name}\n[{signal.unit}]")
                    ax.grid(True, alpha=0.3)
                
            if subplot:
                axes[-1].set_xlabel("Time [s]")
                fig.suptitle("Signal Analysis")
            else:
                ax.set_xlabel("Time [s]")
                ax.set_ylabel("Value")
                ax.legend()
                ax.grid(True, alpha=0.3)
                ax.set_title("Signal Plot")
            
            plt.tight_layout()
            
            # Convert to base64
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            image_base64 = base64.b64encode(buf.read()).decode('utf-8')
            plt.close()
            
            return [
                ImageContent(type="image", data=image_base64, mimeType="image/png"),
                TextContent(type="text", text=f"Plotted {len(channels)} channel(s)")
            ]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error creating plot: {str(e)}")]
    
    async def _handle_calculate_statistics(self, args: Dict[str, Any]) -> List[Any]:
        """Calculate channel statistics"""
        session = self._get_session(args["session_id"])
        if isinstance(session, list):
            return session
        
        mdf = session.mdf
        channels = args["channels"]
        results = {}
        
        for channel_name in channels:
            try:
                signal = mdf.get(channel_name)
                
                # Time filtering
                start = args.get("start_time", signal.timestamps[0])
                end = args.get("end_time", signal.timestamps[-1])
                mask = (signal.timestamps >= start) & (signal.timestamps <= end)
                values = signal.samples[mask]
                
                if len(values) > 0:
                    results[channel_name] = {
                        "unit": signal.unit,
                        "samples": len(values),
                        "min": float(np.min(values)),
                        "max": float(np.max(values)),
                        "mean": float(np.mean(values)),
                        "std": float(np.std(values)),
                        "percentiles": {
                            "25": float(np.percentile(values, 25)),
                            "50": float(np.percentile(values, 50)),
                            "75": float(np.percentile(values, 75))
                        }
                    }
                else:
                    results[channel_name] = {"error": "No data in time range"}
                    
            except Exception as e:
                results[channel_name] = {"error": str(e)}
        
        return [TextContent(type="text", text=json.dumps(results, indent=2))]
    
    async def _handle_mdf_method(self, method_name: str, args: Dict[str, Any]) -> List[Any]:
        """Handle auto-mapped MDF method calls"""
        session = self._get_session(args.pop("session_id"))
        if isinstance(session, list):
            return session
        
        mdf = session.mdf
        
        if not hasattr(mdf, method_name):
            return [TextContent(type="text", text=f"Method not found: {method_name}")]
        
        # Use special handler if available
        if method_name in self.SPECIAL_HANDLERS:
            handler_name = self.SPECIAL_HANDLERS[method_name]
            handler = getattr(self, handler_name)
            return await handler(mdf, args)
        
        # Generic method call
        try:
            method = getattr(mdf, method_name)
            result = method(**args)
            
            # Handle different return types
            if result is None:
                return [TextContent(type="text", text="Method executed successfully")]
            
            elif isinstance(result, (str, int, float, bool)):
                return [TextContent(type="text", text=str(result))]
            
            elif isinstance(result, (list, dict)):
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif isinstance(result, MDF):
                # Methods like cut, filter return new MDF
                new_session_id = f"mdf_{uuid.uuid4().hex[:8]}"
                new_session = MdfSession(
                    id=new_session_id,
                    mdf=result,
                    file_path=f"<derived from {session.id}>",
                    created_at=time.time(),
                    last_accessed=time.time(),
                    metadata={
                        "parent": session.id,
                        "operation": method_name,
                        "channels_count": len(result.channels_db) if hasattr(result, 'channels_db') else 0
                    }
                )
                self.sessions[new_session_id] = new_session
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "new_session_id": new_session_id,
                        "operation": method_name,
                        "channels": new_session.metadata["channels_count"]
                    }, indent=2)
                )]
            
            else:
                return [TextContent(type="text", text=f"Method returned: {type(result).__name__}")]
                
        except Exception as e:
            return [TextContent(type="text", text=f"Error in {method_name}: {str(e)}")]
    
    # Special handlers for complex return types
    async def _handle_get_signal(self, mdf: MDF, args: Dict[str, Any]) -> List[Any]:
        """Handle get method that returns Signal"""
        signal = mdf.get(**args)
        
        result = {
            "name": signal.name,
            "unit": signal.unit,
            "samples": len(signal.samples),
            "time_range": [float(signal.timestamps[0]), float(signal.timestamps[-1])],
            "sample_rate": 1.0 / np.mean(np.diff(signal.timestamps)) if len(signal.timestamps) > 1 else 0,
            "first_values": signal.samples[:10].tolist() if len(signal.samples) > 0 else [],
            "last_values": signal.samples[-10:].tolist() if len(signal.samples) > 0 else []
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _handle_select_signals(self, mdf: MDF, args: Dict[str, Any]) -> List[Any]:
        """Handle select method that returns list of Signals"""
        signals = mdf.select(**args)
        
        results = []
        for signal in signals:
            results.append({
                "name": signal.name,
                "unit": signal.unit,
                "samples": len(signal.samples),
                "time_range": [float(signal.timestamps[0]), float(signal.timestamps[-1])]
            })
        
        return [TextContent(type="text", text=json.dumps(results, indent=2))]
    
    async def _handle_to_dataframe(self, mdf: MDF, args: Dict[str, Any]) -> List[Any]:
        """Handle to_dataframe method"""
        df = mdf.to_dataframe(**args)
        
        result = {
            "shape": list(df.shape),
            "columns": list(df.columns),
            "index_name": df.index.name,
            "memory_usage_mb": df.memory_usage(deep=True).sum() / (1024 * 1024),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "head": df.head(10).to_dict('records'),
            "describe": df.describe().to_dict() if df.select_dtypes(include=[np.number]).shape[1] > 0 else {}
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    
    async def _handle_export(self, mdf: MDF, args: Dict[str, Any]) -> List[Any]:
        """Handle export method with format specification"""
        fmt = args.pop('fmt')
        filename = args.get('filename', f"export_{int(time.time())}.{fmt}")
        args['filename'] = filename
        
        mdf.export(fmt=fmt, **args)
        
        return [TextContent(
            type="text",
            text=json.dumps({
                "status": "exported",
                "format": fmt,
                "filename": filename
            }, indent=2)
        )]
    
    async def _handle_iter_channels(self, mdf: MDF, args: Dict[str, Any]) -> List[Any]:
        """Handle iter_channels method"""
        channels = []
        for channel in mdf.iter_channels():
            channels.append({
                "name": channel.name,
                "group": channel.group_index,
                "index": channel.channel_index,
                "unit": channel.unit
            })
            if len(channels) >= 100:  # Limit output
                break
        
        result = {
            "channels": channels,
            "note": "Showing first 100 channels" if len(channels) >= 100 else None
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _handle_cut(self, mdf: MDF, args: Dict[str, Any]) -> List[Any]:
        """Handle cut method"""
        result = mdf.cut(**args)
        # Create new session for the cut result
        new_session_id = f"mdf_{uuid.uuid4().hex[:8]}"
        new_session = MdfSession(
            id=new_session_id,
            mdf=result,
            file_path=f"<cut operation>",
            created_at=time.time(),
            last_accessed=time.time(),
            metadata={"operation": "cut", "channels_count": len(result.channels_db) if hasattr(result, 'channels_db') else 0}
        )
        self.sessions[new_session_id] = new_session
        
        return [TextContent(
            type="text",
            text=json.dumps({
                "new_session_id": new_session_id,
                "operation": "cut",
                "channels": new_session.metadata["channels_count"]
            }, indent=2)
        )]
    
    async def _handle_filter(self, mdf: MDF, args: Dict[str, Any]) -> List[Any]:
        """Handle filter method"""
        result = mdf.filter(**args)
        # Create new session for the filtered result
        new_session_id = f"mdf_{uuid.uuid4().hex[:8]}"
        new_session = MdfSession(
            id=new_session_id,
            mdf=result,
            file_path=f"<filter operation>",
            created_at=time.time(),
            last_accessed=time.time(),
            metadata={"operation": "filter", "channels_count": len(result.channels_db) if hasattr(result, 'channels_db') else 0}
        )
        self.sessions[new_session_id] = new_session
        
        return [TextContent(
            type="text",
            text=json.dumps({
                "new_session_id": new_session_id,
                "operation": "filter",
                "channels": new_session.metadata["channels_count"]
            }, indent=2)
        )]
    
    async def _handle_resample(self, mdf: MDF, args: Dict[str, Any]) -> List[Any]:
        """Handle resample method"""
        result = mdf.resample(**args)
        # Create new session for the resampled result
        new_session_id = f"mdf_{uuid.uuid4().hex[:8]}"
        new_session = MdfSession(
            id=new_session_id,
            mdf=result,
            file_path=f"<resample operation>",
            created_at=time.time(),
            last_accessed=time.time(),
            metadata={"operation": "resample", "channels_count": len(result.channels_db) if hasattr(result, 'channels_db') else 0}
        )
        self.sessions[new_session_id] = new_session
        
        return [TextContent(
            type="text",
            text=json.dumps({
                "new_session_id": new_session_id,
                "operation": "resample",
                "channels": new_session.metadata["channels_count"]
            }, indent=2)
        )]
    
    def _get_session(self, session_id: str) -> Union[MdfSession, List[Any]]:
        """Get session or return error"""
        if session_id not in self.sessions:
            return [TextContent(type="text", text=f"Session not found: {session_id}")]
        
        session = self.sessions[session_id]
        session.touch()
        return session
    
    def _cleanup_old_sessions(self):
        """Remove sessions older than timeout"""
        current_time = time.time()
        to_remove = []
        
        for sid, session in self.sessions.items():
            if current_time - session.last_accessed > self.session_timeout:
                to_remove.append(sid)
        
        for sid in to_remove:
            try:
                self.sessions[sid].mdf.close()
            except:
                pass
            del self.sessions[sid]
    
    async def run(self):
        """Run the MCP server"""
        from mcp.server.models import InitializationOptions
        from mcp.server.lowlevel import NotificationOptions
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, 
                write_stream,
                InitializationOptions(
                    server_name="mdfmcp",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )

def main():
    """Main entry point for uvx distribution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MDF MCP Server")
    parser.add_argument("--max-sessions", type=int, default=10, help="Maximum concurrent sessions")
    parser.add_argument("--session-timeout", type=int, default=3600, help="Session timeout in seconds")
    
    args = parser.parse_args()
    
    server = MdfMcpServer(
        max_sessions=args.max_sessions,
        session_timeout=args.session_timeout
    )
    
    asyncio.run(server.run())

if __name__ == "__main__":
    main()