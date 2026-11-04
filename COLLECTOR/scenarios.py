# COLLECTOR/scenarios.py
"""Inyección de fallos simulados (07 · escenarios).

Cada escenario degrada la lectura real de psutil de forma progresiva durante `ramp_minutes`.
Al llegar al 100 % emite un evento `critical` con `source="scenario"` y
`attributes.failure=true` (etiqueta del modelo), simula una caída de `down_minutes` y reinicia.
"""

import random
from datetime import UTC, datetime
from typing import Any

Reading = dict[str, Any]
EventDict = dict[str, Any]

SCENARIOS = ("normal", "cpu_spike", "memory_leak", "disk_fill", "error_burst", "degradation")

_INFO_MESSAGES = [
    ("api", "GET /health 200"),
    ("api", "GET /orders 200"),
    ("nginx", "upstream response ok"),
    ("system", "cron job completed"),
]
_WARN_MESSAGES = [
    ("api", "slow request GET /orders took 900 ms"),
    ("system", "high load average"),
]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _event(level: str, source: str, message: str, **attributes: Any) -> EventDict:
    return {
        "ts": _now_iso(),
        "level": level,
        "source": source,
        "message": message,
        "attributes": attributes or None,
    }


def _ramp(current: float, target: float, progress: float) -> float:
    return current + (target - current) * progress


class Scenario:
    def __init__(
        self,
        name: str = "normal",
        ramp_minutes: float = 30,
        down_minutes: float = 3,
        rng: random.Random | None = None,
    ) -> None:
        if name not in SCENARIOS:
            raise ValueError(f"Escenario desconocido: {name}. Opciones: {', '.join(SCENARIOS)}")
        self.name = name
        self.ramp_s = ramp_minutes * 60
        self.down_s = down_minutes * 60
        self.rng = rng or random.Random()
        self.cycle_start: float | None = None
        self.down_until: float | None = None

    def progress(self, now: float) -> float:
        if self.cycle_start is None:
            self.cycle_start = now
        return min(1.0, (now - self.cycle_start) / self.ramp_s) if self.ramp_s else 1.0

    def tick(self, reading: Reading, now: float) -> tuple[Reading, list[EventDict]]:
        """Aplica el escenario a una lectura y devuelve (lectura, eventos generados)."""
        reading = dict(reading)
        events = self._background_events()
        if self.name == "normal":
            return reading, events

        if self.down_until is not None:
            if now < self.down_until:
                reading.update(is_available=False, error_rate=100.0)
                return reading, events
            self.down_until, self.cycle_start = None, now
            events.append(_event("info", "scenario", f"Servicio recuperado ({self.name})"))

        p = self.progress(now)
        events += getattr(self, f"_apply_{self.name}")(reading, p)

        if p >= 1.0:
            events.append(
                _event(
                    "critical",
                    "scenario",
                    f"Fallo simulado: {self.name}",
                    failure=True,
                    scenario=self.name,
                )
            )
            self.down_until = now + self.down_s
        return reading, events

    # ---- eventos de fondo ----
    def _background_events(self) -> list[EventDict]:
        events = []
        if self.rng.random() < 0.3:
            source, msg = self.rng.choice(_INFO_MESSAGES)
            events.append(_event("info", source, msg))
        if self.rng.random() < 0.03:
            source, msg = self.rng.choice(_WARN_MESSAGES)
            events.append(_event("warning", source, msg))
        return events

    def _http_errors(self, count: int, path: str = "/orders") -> list[EventDict]:
        return [
            _event(
                "error",
                "api",
                f"HTTP 503 GET {path} upstream timeout",
                status_code=503,
                path=path,
            )
            for _ in range(count)
        ]

    # ---- escenarios ----
    def _apply_cpu_spike(self, r: Reading, p: float) -> list[EventDict]:
        r["cpu_percent"] = min(100.0, _ramp(r["cpu_percent"], 97, p) + self.rng.uniform(-1, 1))
        if r.get("cpu_per_core"):
            r["cpu_per_core"] = [min(100.0, _ramp(c, 97, p)) for c in r["cpu_per_core"]]
        r["latency_ms"] = (r.get("latency_ms") or 50) + 600 * p
        return [_event("warning", "system", "CPU throttling detected")] if p > 0.8 else []

    def _apply_memory_leak(self, r: Reading, p: float) -> list[EventDict]:
        r["mem_percent"] = min(100.0, _ramp(r["mem_percent"], 98, p))
        if p > 0.85 and self.rng.random() < 0.5:
            return [_event("error", "api", "java.lang.OutOfMemoryError: Java heap space")]
        return []

    def _apply_disk_fill(self, r: Reading, p: float) -> list[EventDict]:
        r["disk_percent"] = min(100.0, _ramp(r["disk_percent"], 99.5, p))
        for part in r.get("disk_partitions") or []:
            if part.get("mount") == "/":
                part["percent"] = r["disk_percent"]
        if p > 0.9:
            return [_event("error", "postgres", "could not extend file: No space left on device")]
        return []

    def _apply_error_burst(self, r: Reading, p: float) -> list[EventDict]:
        r["error_rate"] = 25 * p
        return self._http_errors(int(8 * p))

    def _apply_degradation(self, r: Reading, p: float) -> list[EventDict]:
        r["cpu_percent"] = min(100.0, _ramp(r["cpu_percent"], 93, p))
        r["mem_percent"] = min(100.0, _ramp(r["mem_percent"], 92, p))
        r["latency_ms"] = 180 + 500 * p
        r["error_rate"] = 6 * p
        return self._http_errors(int(5 * p))
