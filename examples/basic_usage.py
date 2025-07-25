#!/usr/bin/env python3
"""
Basic usage examples for MDF MCP Server
This demonstrates how the server processes various requests
"""

# Example 1: Opening an MDF file
open_request = {
    "tool": "open_mdf",
    "arguments": {
        "file_path": "/path/to/measurement.mf4",
        "memory": "full"  # or "low" for large files
    }
}
# Response: {"session_id": "mdf_12345678", "version": "4.10", "channels_count": 523}

# Example 2: Listing channels with pattern matching
list_channels_request = {
    "tool": "list_channels", 
    "arguments": {
        "session_id": "mdf_12345678",
        "pattern": "speed|velocity",  # Regex pattern
        "group": None  # Optional: specific group index
    }
}
# Response: List of matching channels with metadata

# Example 3: Getting signal data
get_signal_request = {
    "tool": "mdf_get",
    "arguments": {
        "session_id": "mdf_12345678",
        "name": "Vehicle_Speed",
        "samples_only": False  # Get full Signal object info
    }
}
# Response: Signal data with timestamps, values, unit, statistics

# Example 4: Plotting multiple signals
plot_request = {
    "tool": "plot_signals",
    "arguments": {
        "session_id": "mdf_12345678",
        "channels": ["Engine_Speed", "Vehicle_Speed", "Throttle_Position"],
        "start_time": 100.0,  # Optional: time range
        "end_time": 200.0,
        "subplot": True  # Create separate subplots
    }
}
# Response: Base64 encoded PNG image

# Example 5: Calculating statistics
stats_request = {
    "tool": "calculate_statistics",
    "arguments": {
        "session_id": "mdf_12345678",
        "channels": ["Oil_Temperature", "Coolant_Temperature"],
        "start_time": 0,
        "end_time": None  # Use full time range
    }
}
# Response: Statistics for each channel (min, max, mean, std, percentiles)

# Example 6: Filtering and creating new session
filter_request = {
    "tool": "mdf_filter",
    "arguments": {
        "session_id": "mdf_12345678",
        "channels": ["Speed", "RPM", "Temperature"]  # Keep only these
    }
}
# Response: {"new_session_id": "mdf_87654321", "operation": "filter", "channels": 3}

# Example 7: Exporting to different formats
export_csv_request = {
    "tool": "mdf_export",
    "arguments": {
        "session_id": "mdf_12345678",
        "fmt": "csv",
        "filename": "output.csv",
        "channels": ["Vehicle_Speed", "Engine_Speed"]  # Optional: specific channels
    }
}
# Response: {"status": "exported", "format": "csv", "filename": "output.csv"}

# Example 8: Converting to pandas DataFrame
dataframe_request = {
    "tool": "mdf_to_dataframe",
    "arguments": {
        "session_id": "mdf_12345678",
        "channels": None,  # All channels
        "time_from_zero": True
    }
}
# Response: DataFrame info with shape, columns, memory usage, sample data

# Example 9: Time-based data extraction
cut_request = {
    "tool": "mdf_cut",
    "arguments": {
        "session_id": "mdf_12345678",
        "start": 100.0,  # Start time in seconds
        "stop": 500.0,   # End time in seconds
        "include_ends": True
    }
}
# Response: New session with time-sliced data

# Example 10: Resampling signals
resample_request = {
    "tool": "mdf_resample",
    "arguments": {
        "session_id": "mdf_12345678",
        "raster": 0.1,  # 10 Hz sampling rate
        "time_from_zero": True
    }
}
# Response: New session with resampled data

# Example 11: Getting file metadata
file_info_request = {
    "tool": "get_file_info",
    "arguments": {
        "session_id": "mdf_12345678"
    }
}
# Response: Detailed file information including version, program, timestamps

# Example 12: Closing session
close_request = {
    "tool": "close_mdf",
    "arguments": {
        "session_id": "mdf_12345678"
    }
}
# Response: "Closed session: mdf_12345678"