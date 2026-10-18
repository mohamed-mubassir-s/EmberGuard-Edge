"""Deterministic risk engine for EmberGuard Edge.

This module is a PURE function with an injectable clock.
It has NO dependency on FastAPI, the database, serial, or the frontend.

The evaluation rules and priority follow the authoritative specification
in EMBERGUARD_AI_IMPLEMENTATION_BRIEF_v2.md §6.3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from app.core.models import RiskState, SensorSnapshot, RiskExplanation


# ---------------------------------------------------------------------------
# Thresholds container — passed in, never hard-coded
# ---------------------------------------------------------------------------
@dataclass
class RiskThresholds:
    smoke_watch_level: float = 300.0
    smoke_critical_level: float = 600.0
    temp_watch_c: float = 45.0
    temp_critical_c: float = 65.0
    watch_persist_ms: int = 5000
    clear_hold_ms: int = 5000


# ---------------------------------------------------------------------------
# Internal timing context (mutable, carried between evaluations)
# ---------------------------------------------------------------------------
@dataclass
class RiskContext:
    """Mutable context that tracks timers between evaluations."""
    current_state: RiskState = RiskState.NORMAL
    current_reason: str = "boot"

    # Timestamp (monotonic ms) when warning was first continuously detected
    warn_start_ms: Optional[int] = None
    # Whether the warning has persisted for >= WATCH_PERSIST_MS
    warn_persisted: bool = False

    # Timestamp when the critical/warn condition first cleared
    clear_start_ms: Optional[int] = None

    # Track which sensors are currently invalid
    invalid_sensors: List[str] = field(default_factory=list)

    # Transition counter
    transition_count: int = 0


# ---------------------------------------------------------------------------
# Evaluation result
# ---------------------------------------------------------------------------
@dataclass
class EvalResult:
    state: RiskState
    reason: str
    changed: bool
    explanation: RiskExplanation
    old_state: RiskState = RiskState.NORMAL


# ---------------------------------------------------------------------------
# The engine
# ---------------------------------------------------------------------------
class RiskEngine:
    """Stateful, deterministic risk evaluator.

    Call `evaluate(snapshot, now_ms)` once per sample period.
    The engine uses an injectable monotonic clock so unit tests can control time.
    """

    def __init__(
        self,
        thresholds: Optional[RiskThresholds] = None,
        clock_ms: Optional[Callable[[], int]] = None,
    ):
        self.thresholds = thresholds or RiskThresholds()
        self._clock_ms = clock_ms or self._default_clock
        self.ctx = RiskContext()

    @staticmethod
    def _default_clock() -> int:
        import time
        return int(time.monotonic() * 1000)

    def reset(self) -> None:
        """Reset to boot state."""
        self.ctx = RiskContext()

    def evaluate(self, snap: SensorSnapshot, now_ms: Optional[int] = None) -> EvalResult:
        """Evaluate the risk state from a sensor snapshot.

        Args:
            snap: Current sensor readings.
            now_ms: Monotonic timestamp in milliseconds (injectable for tests).

        Returns:
            EvalResult with the new state, reason, and explanation.
        """
        if now_ms is None:
            now_ms = self._clock_ms()

        t = self.thresholds
        ctx = self.ctx

        # --- Compute conditions ---
        flame_crit = snap.flame.valid and snap.flame.triggered
        combo_crit = (
            snap.smoke.valid
            and snap.temperature.valid
            and snap.smoke.value >= t.smoke_critical_level
            and snap.temperature.value >= t.temp_critical_c
        )
        critical = flame_crit or combo_crit

        any_invalid = not snap.flame.valid or not snap.smoke.valid or not snap.temperature.valid

        invalid_sensors: List[str] = []
        if not snap.flame.valid:
            invalid_sensors.append("flame")
        if not snap.smoke.valid:
            invalid_sensors.append("smoke")
        if not snap.temperature.valid:
            invalid_sensors.append("temperature")

        warn_smoke = snap.smoke.valid and snap.smoke.value >= t.smoke_watch_level
        warn_temp = snap.temperature.valid and snap.temperature.value >= t.temp_watch_c
        warn_raw = warn_smoke or warn_temp

        # --- Warning persistence timer ---
        if warn_raw:
            if ctx.warn_start_ms is None:
                ctx.warn_start_ms = now_ms
            elapsed = now_ms - ctx.warn_start_ms
            warn_persisted = elapsed >= t.watch_persist_ms
        else:
            ctx.warn_start_ms = None
            warn_persisted = False
        ctx.warn_persisted = warn_persisted

        # --- Determine reason text for warnings ---
        warn_reason = ""
        if warn_persisted:
            if warn_smoke:
                warn_reason = "persistent smoke warning"
            elif warn_temp:
                warn_reason = "persistent temperature warning"

        # --- Decision rules (strict priority) ---
        new_state: RiskState
        reason: str

        # Rule 1: Critical → FIRE_ALERT (immediate)
        if critical:
            new_state = RiskState.FIRE_ALERT
            if flame_crit:
                reason = "valid flame trigger"
            else:
                reason = "smoke and temperature both critical"
            # Reset clear-hold since we're (re-)entering critical
            ctx.clear_start_ms = None

        # Rule 2: Holding FIRE_ALERT during clear-hold
        elif ctx.current_state == RiskState.FIRE_ALERT:
            if ctx.clear_start_ms is None:
                ctx.clear_start_ms = now_ms
            hold_elapsed = now_ms - ctx.clear_start_ms
            if hold_elapsed < t.clear_hold_ms:
                new_state = RiskState.FIRE_ALERT
                reason = ctx.current_reason  # keep existing reason while holding
            else:
                # Clear-hold expired — fall through to lower rules
                ctx.clear_start_ms = None
                if any_invalid:
                    new_state = RiskState.SENSOR_FAULT
                    reason = " and ".join(f"{s} sensor read failed" for s in invalid_sensors) if len(invalid_sensors) > 1 else f"{invalid_sensors[0]} sensor read failed"
                elif warn_persisted:
                    new_state = RiskState.WATCH
                    reason = warn_reason
                elif warn_raw:
                    # Warn present but not yet persisted — go NORMAL
                    new_state = RiskState.NORMAL
                    reason = f"conditions cleared for CLEAR_HOLD_MS"
                else:
                    new_state = RiskState.NORMAL
                    reason = f"conditions cleared for CLEAR_HOLD_MS"

        # Rule 3: Sensor fault (no critical override)
        elif any_invalid:
            new_state = RiskState.SENSOR_FAULT
            if len(invalid_sensors) == 1:
                reason = f"{invalid_sensors[0]} sensor read failed"
            else:
                reason = " and ".join(f"{s} sensor read failed" for s in invalid_sensors)
            ctx.clear_start_ms = None

        # Rule 4: Warning persisted → WATCH
        elif warn_persisted:
            new_state = RiskState.WATCH
            reason = warn_reason
            ctx.clear_start_ms = None

        # Rule 5: Holding WATCH during clear-hold
        elif ctx.current_state == RiskState.WATCH:
            if warn_raw:
                new_state = RiskState.WATCH
                reason = ctx.current_reason
                ctx.clear_start_ms = None
            else:
                # Warning cleared — start/continue clear-hold
                if ctx.clear_start_ms is None:
                    ctx.clear_start_ms = now_ms
                hold_elapsed = now_ms - ctx.clear_start_ms
                if hold_elapsed < t.clear_hold_ms:
                    new_state = RiskState.WATCH
                    reason = ctx.current_reason
                else:
                    new_state = RiskState.NORMAL
                    reason = "conditions cleared for CLEAR_HOLD_MS"
                    ctx.clear_start_ms = None

        # Rule 6: Default NORMAL
        else:
            new_state = RiskState.NORMAL
            reason = ctx.current_reason if ctx.current_state == RiskState.NORMAL else "conditions cleared for CLEAR_HOLD_MS"
            ctx.clear_start_ms = None

        # --- Build explanation ---
        watch_timer_remaining = 0
        if warn_raw and ctx.warn_start_ms is not None and not warn_persisted:
            watch_timer_remaining = max(0, t.watch_persist_ms - (now_ms - ctx.warn_start_ms))

        clear_hold_remaining = 0
        clear_hold_active = False
        if ctx.clear_start_ms is not None and new_state in (RiskState.FIRE_ALERT, RiskState.WATCH):
            clear_hold_active = True
            clear_hold_remaining = max(0, t.clear_hold_ms - (now_ms - ctx.clear_start_ms))

        explanation = RiskExplanation(
            state=new_state,
            reason=reason,
            flame_critical=flame_crit,
            combo_critical=combo_crit,
            any_warning=warn_raw,
            warning_persisted=warn_persisted,
            any_invalid=any_invalid,
            invalid_sensors=invalid_sensors,
            watch_timer_active=warn_raw and not warn_persisted,
            watch_timer_remaining_ms=watch_timer_remaining,
            clear_hold_active=clear_hold_active,
            clear_hold_remaining_ms=clear_hold_remaining,
        )

        # --- Detect change ---
        changed = new_state != ctx.current_state
        old_state = ctx.current_state

        if changed:
            ctx.transition_count += 1

        ctx.current_state = new_state
        ctx.current_reason = reason
        ctx.invalid_sensors = invalid_sensors

        return EvalResult(
            state=new_state,
            reason=reason,
            changed=changed,
            explanation=explanation,
            old_state=old_state,
        )
