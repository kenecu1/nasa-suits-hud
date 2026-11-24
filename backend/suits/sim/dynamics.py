"""The TSS's fault rules, as NASA's code intends them, applied to the fake TSS's state.

At the pinned TSS commit NASA's own fault and switch logic is switched off (an inverted guard in
``src/data.c``), so the fake does it here (docs/briefs/M2.md, section 6). The rules follow
``update_fan_error_state``, ``update_O2_error_state``, ``update_scrubber_state_EVA`` and
``update_power_error_state`` in ``vendor/TSS2027/src/data.c``. The rates are ours, per second
of scenario time, chosen so a failure crosses its limit within seconds.

* Only the active fan spins (``dcu.fan``: True = primary). A fan fault on the primary winds it
  down and builds helmet CO2; on the secondary fan there is no error and helmet CO2 recovers.
* An oxygen fault on the primary tank drains it and lowers suit O2 pressure; on the secondary
  tank there is no error and suit pressure recovers.
* A scrubber fault fills the active scrubber fast. The error flag is "active scrubber above 60%".
* A power fault drains the primary battery while it is in use (local power, primary battery).
  The error flag is "primary battery below 20% while in use".

``state`` is the fake's EVA.json-shaped dict. Nothing here imports from ``suits.core``.
"""

from __future__ import annotations

import copy
from typing import Any, Literal

FaultName = Literal["fan", "oxy", "scrubber", "power"]
FAULTS: tuple[FaultName, ...] = ("fan", "oxy", "scrubber", "power")

FAN_RPM = 30000.0
FAN_DECAY_RPM_S = 1500.0
HELMET_CO2_GROWTH_S = 0.006  # psi/s
SUIT_O2_DROP_S = 0.03  # psi/s
O2_TANK_DRAIN_S = 0.5  # %/s
SCRUBBER_FILL_S = 3.0  # %/s
SCRUBBER_EMPTY_S = 1.0  # %/s, the inactive scrubber vents
SUIT_CO2_GROWTH_S = 0.004  # psi/s while the active scrubber is above 30%
BATTERY_DRAIN_S = 2.0  # %/s
RECOVERY_HALF_LIFE_S = 1.0  # a disturbed value closes half its gap to normal per second


class Dynamics:
    def __init__(self, state: dict[str, Any]) -> None:
        self.state = state
        self.faults: set[FaultName] = set()
        self._normal = copy.deepcopy(state["telemetry"])  # what disturbed values recover to
        self._disturbed: set[str] = set()

    def set_fault(self, name: FaultName, on: bool = True) -> None:
        if name not in FAULTS:
            raise ValueError(f"unknown fault {name!r}; known: {', '.join(FAULTS)}")
        if on:
            self.faults.add(name)
        else:
            self.faults.discard(name)

    def tick(self, dt: float) -> None:
        """Advance the rules by ``dt`` seconds of scenario time."""
        if dt <= 0:
            return
        tel = self.state["telemetry"]
        err = self.state["error"]
        dcu = self.state["dcu"]
        self._fan(tel, err, bool(dcu["fan"]), dt)
        self._oxygen(err, bool(dcu["oxy"]), dt)
        self._scrubber(tel, err, bool(dcu["co2"]), dt)
        self._power(tel, err, dcu["batt"], dt)

    # ---- rules ----

    def _fan(self, tel: dict, err: dict, on_primary: bool, dt: float) -> None:
        failed = "fan" in self.faults and on_primary
        err["fan_error"] = failed
        if failed:
            tel["fan_pri_rpm"] = max(0.0, tel["fan_pri_rpm"] - FAN_DECAY_RPM_S * dt)
            tel["fan_sec_rpm"] = 0.0
            self._push("helmet_pressure_co2", HELMET_CO2_GROWTH_S * dt)
        else:
            tel["fan_pri_rpm"] = FAN_RPM if on_primary else 0.0
            tel["fan_sec_rpm"] = 0.0 if on_primary else FAN_RPM
            self._recover("helmet_pressure_co2", dt)

    def _oxygen(self, err: dict, on_primary: bool, dt: float) -> None:
        failed = "oxy" in self.faults and on_primary
        err["oxy_error"] = failed
        if failed:
            self._push("suit_pressure_oxy", -SUIT_O2_DROP_S * dt, low=0.0)
            self._push("oxy_pri_storage", -O2_TANK_DRAIN_S * dt, low=0.0)
        else:
            self._recover("suit_pressure_oxy", dt)

    def _scrubber(self, tel: dict, err: dict, on_a: bool, dt: float) -> None:
        active, idle = (
            ("scrubber_a_co2_storage", "scrubber_b_co2_storage")
            if on_a
            else ("scrubber_b_co2_storage", "scrubber_a_co2_storage")
        )
        if "scrubber" in self.faults:
            self._push(active, SCRUBBER_FILL_S * dt, high=100.0)
        if idle in self._disturbed:
            self._push(idle, -SCRUBBER_EMPTY_S * dt, low=0.0)
        if tel[active] > 30.0:
            self._push("suit_pressure_co2", SUIT_CO2_GROWTH_S * dt)
        else:
            self._recover("suit_pressure_co2", dt)
        err["scrubber_error"] = tel[active] > 60.0

    def _power(self, tel: dict, err: dict, batt: dict, dt: float) -> None:
        primary_in_use = not batt["lu"] and bool(batt["ps"])  # local power, primary battery
        if "power" in self.faults and primary_in_use:
            self._push("primary_battery_level", -BATTERY_DRAIN_S * dt, low=0.0)
        err["power_error"] = primary_in_use and tel["primary_battery_level"] < 20.0

    # ---- helpers ----

    def _push(self, name: str, delta: float, low: float | None = None,
              high: float | None = None) -> None:
        tel = self.state["telemetry"]
        value = tel[name] + delta
        if low is not None:
            value = max(low, value)
        if high is not None:
            value = min(high, value)
        tel[name] = value
        self._disturbed.add(name)

    def _recover(self, name: str, dt: float) -> None:
        """Move a value this module disturbed back toward normal; leave others alone (tests
        set values by hand)."""
        if name not in self._disturbed:
            return
        tel = self.state["telemetry"]
        gap = self._normal[name] - tel[name]
        if abs(gap) < 1e-3:
            tel[name] = self._normal[name]
            self._disturbed.discard(name)
            return
        tel[name] += gap * (1.0 - 0.5 ** (dt / RECOVERY_HALF_LIFE_S))
