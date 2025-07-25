#!/usr/bin/env python3
"""
Create a test MDF file to verify MCP server functionality
"""

from pathlib import Path
import numpy as np
from asammdf import MDF, Signal

def create_test_mdf():
    """Create a simple test MDF file with automotive-like signals"""
    # Create test signals
    duration = 10.0  # seconds
    sample_rate = 100.0  # Hz
    samples = int(duration * sample_rate)
    timestamps = np.linspace(0, duration, samples, dtype=np.float64)
    
    # Vehicle speed (0-80 km/h with acceleration pattern)
    speed = 30 + 25 * np.sin(2 * np.pi * timestamps / 8) + 5 * np.random.normal(0, 1, samples)
    speed = np.clip(speed, 0, 80)
    
    # Engine RPM (correlated with speed)
    rpm = 1000 + speed * 40 + 200 * np.sin(2 * np.pi * timestamps / 5) + 50 * np.random.normal(0, 1, samples)
    rpm = np.clip(rpm, 800, 6000)
    
    # Temperature (warm-up curve)
    temp = 60 + 30 * np.tanh((timestamps - 2) / 3) + 2 * np.random.normal(0, 1, samples)
    temp = np.clip(temp, 50, 95)
    
    signals = [
        Signal(
            samples=speed.astype(np.float32),
            timestamps=timestamps,
            name="Vehicle_Speed",
            unit="km/h",
            comment="Vehicle speed from wheel sensors"
        ),
        Signal(
            samples=rpm.astype(np.float32),
            timestamps=timestamps,
            name="Engine_RPM", 
            unit="rpm",
            comment="Engine rotational speed"
        ),
        Signal(
            samples=temp.astype(np.float32),
            timestamps=timestamps,
            name="Coolant_Temperature",
            unit="°C",
            comment="Engine coolant temperature"
        )
    ]
    
    # Create MDF file
    output_path = Path("test_automotive_data.mf4")
    with MDF(version='4.10') as mdf:
        mdf.append(signals, comment="Test automotive measurement data")
        mdf.save(output_path, overwrite=True)
    
    print(f"✅ Created test MDF file: {output_path.absolute()}")
    print(f"   Duration: {duration}s")
    print(f"   Channels: {len(signals)}")
    print(f"   Samples per channel: {samples}")
    
    return output_path

if __name__ == "__main__":
    create_test_mdf()