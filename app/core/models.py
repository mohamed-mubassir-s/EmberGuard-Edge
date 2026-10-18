"""Core domain models for EmberGuard Edge.

These are pure data models with no framework dependencies.
The risk engine, simulator, API, and database all share these types.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


# ---------------------------------------------------------------------------
# State names — DECIDED (D-03): exact spelling everywhere
# ---------------------------------------------------------------------------
class RiskState(str, Enum):
    NORMAL = "NORMAL"
    WATCH = "WATCH"
    FIRE_ALERT = "FIRE_ALERT"
    SENSOR_FAULT = "SENSOR_FAULT"


# ---------------------------------------------------------------------------
# Sensor source labels
# ---------------------------------------------------------------------------
class SensorSource(str, Enum):
    REAL = "REAL"
    INJECTED = "INJECTED"
    SIMULATED = "SIMULATED"


# ---------------------------------------------------------------------------
# Sensor reading
# ---------------------------------------------------------------------------
@dataclass
class SensorReading:
    """A single sensor's current value and validity."""
    value: float = 0.0
    triggered: bool = False          # For flame: True = flame detected
    valid: bool = True
    fault_text: str = ""
    source: SensorSource = SensorSource.SIMULATED


@dataclass
class SensorSnapshot:
    """All three sensor readings at a point in time."""
    flame: SensorReading = field(default_factory=SensorReading)
    smoke: SensorReading = field(default_factory=SensorReading)
    temperature: SensorReading = field(default_factory=SensorReading)
    timestamp: float = field(default_factory=time.monotonic)


# ---------------------------------------------------------------------------
# State transition event
# ---------------------------------------------------------------------------
@dataclass
class StateTransition:
    """Emitted whenever the risk state changes."""
    old_state: RiskState
    new_state: RiskState
    reason: str
    sensors: SensorSnapshot
    timestamp: float = field(default_factory=time.time)
    wall_clock: str = ""  # ISO-8601, filled by event_service


# ---------------------------------------------------------------------------
# Alarm output pattern
# ---------------------------------------------------------------------------
@dataclass
class AlarmOutput:
    """Current LED and buzzer state for the dashboard."""
    led_on: bool = False
    buzzer_on: bool = False
    state: RiskState = RiskState.NORMAL
    pattern_phase_ms: int = 0


# ---------------------------------------------------------------------------
# Risk explanation — the "why" behind the current state
# ---------------------------------------------------------------------------
@dataclass
class RiskExplanation:
    """Human-readable explanation of the current risk decision."""
    state: RiskState = RiskState.NORMAL
    reason: str = "boot"
    flame_critical: bool = False
    combo_critical: bool = False
    any_warning: bool = False
    warning_persisted: bool = False
    any_invalid: bool = False
    invalid_sensors: List[str] = field(default_factory=list)
    watch_timer_active: bool = False
    watch_timer_remaining_ms: int = 0
    clear_hold_active: bool = False
    clear_hold_remaining_ms: int = 0


# ---------------------------------------------------------------------------
# Full system status (sent over WebSocket)
# ---------------------------------------------------------------------------
@dataclass
class SystemStatus:
    """Complete snapshot for the dashboard."""
    state: RiskState = RiskState.NORMAL
    reason: str = "boot"
    sensors: Optional[SensorSnapshot] = None
    alarm: Optional[AlarmOutput] = None
    explanation: Optional[RiskExplanation] = None
    mode: str = "SIMULATED"             # SIMULATED | SERIAL_CONNECTED | SERIAL_DISCONNECTED
    connected: bool = True
    uptime_s: float = 0.0
    calibrated: bool = False
    last_update: str = ""
    transition_count: int = 0
