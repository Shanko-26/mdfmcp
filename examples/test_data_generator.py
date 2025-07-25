#!/usr/bin/env python3
"""
Generate sample MDF files for testing the MCP server
"""

import numpy as np
from pathlib import Path
try:
    from asammdf import MDF, Signal
except ImportError:
    print("Please install asammdf: pip install asammdf")
    raise

def create_sample_mdf(filename: str = "sample.mf4", duration: float = 60.0, sample_rate: float = 100.0):
    """Create a sample MDF file with various signal types"""
    
    # Time vector
    time_samples = int(duration * sample_rate)
    timestamps = np.linspace(0, duration, time_samples, dtype=np.float64)
    
    # Create various test signals
    signals = []
    
    # 1. Vehicle Speed (0-120 km/h with realistic acceleration pattern)
    vehicle_speed = 50 + 30 * np.sin(2 * np.pi * timestamps / 20) + 10 * np.random.normal(0, 1, time_samples)
    vehicle_speed = np.clip(vehicle_speed, 0, 120)
    signals.append(Signal(
        samples=vehicle_speed.astype(np.float32),
        timestamps=timestamps,
        name="Vehicle_Speed",
        unit="km/h",
        comment="Vehicle speed from CAN bus"
    ))
    
    # 2. Engine Speed (RPM)
    engine_speed = 1500 + 2000 * (vehicle_speed / 100) + 200 * np.random.normal(0, 1, time_samples)
    engine_speed = np.clip(engine_speed, 800, 6000)
    signals.append(Signal(
        samples=engine_speed.astype(np.float32),
        timestamps=timestamps,
        name="Engine_Speed",
        unit="RPM",
        comment="Engine rotational speed"
    ))
    
    # 3. Throttle Position (0-100%)
    throttle = 20 + 30 * np.sin(2 * np.pi * timestamps / 15) + 5 * np.random.normal(0, 1, time_samples)
    throttle = np.clip(throttle, 0, 100)
    signals.append(Signal(
        samples=throttle.astype(np.float32),
        timestamps=timestamps,
        name="Throttle_Position",
        unit="%",
        comment="Accelerator pedal position"
    ))
    
    # 4. Engine Temperature (80-110°C)
    temp_base = 85 + 10 * np.tanh((timestamps - 10) / 10)  # Warm-up curve
    engine_temp = temp_base + 3 * np.random.normal(0, 1, time_samples)
    engine_temp = np.clip(engine_temp, 70, 115)
    signals.append(Signal(
        samples=engine_temp.astype(np.float32),
        timestamps=timestamps,
        name="Engine_Temperature",
        unit="°C", 
        comment="Engine coolant temperature"
    ))
    
    # 5. Oil Pressure (2-6 bar)
    oil_pressure = 3.5 + 1.5 * (engine_speed / 4000) + 0.2 * np.random.normal(0, 1, time_samples)
    oil_pressure = np.clip(oil_pressure, 1.0, 6.5)
    signals.append(Signal(
        samples=oil_pressure.astype(np.float32),
        timestamps=timestamps,
        name="Oil_Pressure",
        unit="bar",
        comment="Engine oil pressure"
    ))
    
    # 6. Fuel Level (40-100%)
    fuel_consumption_rate = 0.002 * throttle / 100  # L/s based on throttle
    fuel_consumed = np.cumsum(fuel_consumption_rate) / sample_rate
    fuel_level = 80 - fuel_consumed * 5  # Start at 80%, consume fuel
    fuel_level = np.clip(fuel_level, 0, 100)
    signals.append(Signal(
        samples=fuel_level.astype(np.float32),
        timestamps=timestamps,
        name="Fuel_Level",
        unit="%",
        comment="Fuel tank level"
    ))
    
    # 7. GPS Latitude (simulated route)
    lat_base = 52.5200  # Berlin coordinates
    lat_variation = 0.01 * np.sin(2 * np.pi * timestamps / 40)
    gps_lat = lat_base + lat_variation + 0.001 * np.random.normal(0, 1, time_samples)
    signals.append(Signal(
        samples=gps_lat.astype(np.float64),
        timestamps=timestamps,
        name="GPS_Latitude",
        unit="deg",
        comment="GPS latitude coordinate"
    ))
    
    # 8. GPS Longitude (simulated route)
    lon_base = 13.4050  # Berlin coordinates
    lon_variation = 0.01 * np.cos(2 * np.pi * timestamps / 40)
    gps_lon = lon_base + lon_variation + 0.001 * np.random.normal(0, 1, time_samples)
    signals.append(Signal(
        samples=gps_lon.astype(np.float64),
        timestamps=timestamps,
        name="GPS_Longitude", 
        unit="deg",
        comment="GPS longitude coordinate"
    ))
    
    # 9. Battery Voltage (11-15V)
    battery_voltage = 12.6 + 0.8 * np.sin(2 * np.pi * timestamps / 5) + 0.1 * np.random.normal(0, 1, time_samples)
    battery_voltage = np.clip(battery_voltage, 10.5, 15.0)
    signals.append(Signal(
        samples=battery_voltage.astype(np.float32),
        timestamps=timestamps,
        name="Battery_Voltage",
        unit="V",
        comment="Vehicle battery voltage"
    ))
    
    # 10. Error flags (digital signals)
    error_probability = 0.001  # 0.1% chance of error per sample
    check_engine = np.random.random(time_samples) < error_probability
    signals.append(Signal(
        samples=check_engine.astype(np.uint8),
        timestamps=timestamps,
        name="Check_Engine_Light",
        unit="",
        comment="Engine diagnostic error flag"
    ))
    
    # Create MDF file
    with MDF(version='4.10') as mdf:
        mdf.append(signals, comment="Generated test data for MCP server")
        mdf.save(filename, overwrite=True)
    
    print(f"Created sample MDF file: {filename}")
    print(f"- Duration: {duration} seconds")
    print(f"- Sample rate: {sample_rate} Hz")
    print(f"- Signals: {len(signals)}")
    print(f"- File size: {Path(filename).stat().st_size / 1024:.1f} KB")
    
    return filename

def create_large_sample_mdf(filename: str = "large_sample.mf4", duration: float = 600.0, channels: int = 100):
    """Create a larger sample file for performance testing"""
    
    sample_rate = 1000.0  # 1 kHz
    time_samples = int(duration * sample_rate)
    timestamps = np.linspace(0, duration, time_samples, dtype=np.float64)
    
    signals = []
    
    for i in range(channels):
        # Generate varied signal patterns
        if i % 4 == 0:  # Sine waves
            freq = 0.1 + i * 0.05
            data = 10 * np.sin(2 * np.pi * freq * timestamps) + np.random.normal(0, 0.5, time_samples)
        elif i % 4 == 1:  # Ramp signals
            data = (timestamps / duration) * 100 + np.random.normal(0, 1, time_samples)
        elif i % 4 == 2:  # Step signals
            data = 50 * np.sign(np.sin(2 * np.pi * timestamps / (10 + i))) + np.random.normal(0, 2, time_samples)
        else:  # Random walk
            data = np.cumsum(np.random.normal(0, 0.1, time_samples))
        
        signals.append(Signal(
            samples=data.astype(np.float32),
            timestamps=timestamps,
            name=f"Channel_{i:03d}",
            unit="V" if i % 3 == 0 else ("A" if i % 3 == 1 else "°C"),
            comment=f"Test channel {i} - {'Sine' if i%4==0 else 'Ramp' if i%4==1 else 'Step' if i%4==2 else 'Random'}"
        ))
    
    with MDF(version='4.10') as mdf:
        mdf.append(signals, comment=f"Large test file with {channels} channels")
        mdf.save(filename, overwrite=True)
    
    print(f"Created large sample MDF file: {filename}")
    print(f"- Duration: {duration} seconds")
    print(f"- Channels: {channels}")
    print(f"- Total samples: {time_samples * channels:,}")
    print(f"- File size: {Path(filename).stat().st_size / (1024*1024):.1f} MB")
    
    return filename

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate sample MDF files")
    parser.add_argument("--small", action="store_true", help="Create small sample file")
    parser.add_argument("--large", action="store_true", help="Create large sample file") 
    parser.add_argument("--duration", type=float, default=60.0, help="Duration in seconds")
    parser.add_argument("--channels", type=int, default=100, help="Number of channels (large file only)")
    parser.add_argument("--output", type=str, help="Output filename")
    
    args = parser.parse_args()
    
    if args.large:
        filename = args.output or "large_sample.mf4"
        create_large_sample_mdf(filename, args.duration, args.channels)
    else:
        filename = args.output or "sample.mf4"
        create_sample_mdf(filename, args.duration)
    
    print(f"\nTo test with MCP server:")
    print(f'1. Start the server: python -m mdfmcp.server')
    print(f'2. Open the file: {{"tool": "open_mdf", "arguments": {{"file_path": "{filename}"}}}}')
    print(f'3. List channels: {{"tool": "list_channels", "arguments": {{"session_id": "SESSION_ID"}}}}')
    print(f'4. Plot signals: {{"tool": "plot_signals", "arguments": {{"session_id": "SESSION_ID", "channels": ["Vehicle_Speed", "Engine_Speed"]}}}}')