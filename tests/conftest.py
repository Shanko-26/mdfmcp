"""Test configuration for MDF MCP Server tests"""

import pytest
import tempfile
import numpy as np
from pathlib import Path

try:
    from asammdf import MDF, Signal
except ImportError:
    pytest.skip("asammdf not available", allow_module_level=True)

@pytest.fixture(scope="session")
def sample_data():
    """Generate sample signal data for tests"""
    duration = 10.0
    sample_rate = 100.0
    samples = int(duration * sample_rate)
    timestamps = np.linspace(0, duration, samples, dtype=np.float64)
    
    return {
        "timestamps": timestamps,
        "samples": samples,
        "duration": duration,
        "sample_rate": sample_rate
    }

@pytest.fixture(scope="session") 
def automotive_signals(sample_data):
    """Create realistic automotive test signals"""
    t = sample_data["timestamps"]
    
    # Vehicle speed with acceleration/deceleration pattern
    speed_base = 50 + 20 * np.sin(2 * np.pi * t / 8)
    speed_noise = 2 * np.random.normal(0, 1, len(t))
    vehicle_speed = np.clip(speed_base + speed_noise, 0, 120)
    
    # Engine RPM correlated with speed
    rpm_base = 1000 + 30 * vehicle_speed + 500 * np.sin(2 * np.pi * t / 5)
    rpm_noise = 100 * np.random.normal(0, 1, len(t))
    engine_rpm = np.clip(rpm_base + rpm_noise, 800, 6000)
    
    # Temperature with warm-up curve
    temp_base = 70 + 25 * np.tanh((t - 2) / 3)
    temp_noise = 2 * np.random.normal(0, 1, len(t))
    temperature = np.clip(temp_base + temp_noise, 60, 110)
    
    return [
        Signal(
            samples=vehicle_speed.astype(np.float32),
            timestamps=t,
            name="Vehicle_Speed",
            unit="km/h",
            comment="Vehicle speed from wheel sensors"
        ),
        Signal(
            samples=engine_rpm.astype(np.float32), 
            timestamps=t,
            name="Engine_RPM",
            unit="rpm",
            comment="Engine rotational speed"
        ),
        Signal(
            samples=temperature.astype(np.float32),
            timestamps=t, 
            name="Coolant_Temperature",
            unit="°C",
            comment="Engine coolant temperature"
        )
    ]

@pytest.fixture
def temp_mdf_file(automotive_signals):
    """Create temporary MDF file with automotive signals"""
    with tempfile.NamedTemporaryFile(suffix='.mf4', delete=False) as tmp:
        with MDF(version='4.10') as mdf:
            mdf.append(automotive_signals, comment="Test automotive data")
            mdf.save(tmp.name, overwrite=True)
        
        yield tmp.name
        
        # Cleanup
        Path(tmp.name).unlink(missing_ok=True)

@pytest.fixture
def server_config():
    """Default server configuration for tests"""
    return {
        "max_sessions": 3,
        "session_timeout": 60  # Short timeout for tests
    }