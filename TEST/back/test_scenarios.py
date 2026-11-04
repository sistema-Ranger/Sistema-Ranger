# TEST/back/test_scenarios.py
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "COLLECTOR"))
from scenarios import Scenario  # noqa: E402

BASE = {
    "cpu_percent": 20.0,
    "cpu_per_core": [20.0, 20.0],
    "mem_percent": 40.0,
    "disk_percent": 50.0,
    "disk_partitions": [{"mount": "/", "percent": 50.0}],
    "latency_ms": 50.0,
    "error_rate": 0.0,
    "is_available": True,
}


def test_unknown_scenario_raises() -> None:
    with pytest.raises(ValueError):
        Scenario("inventado")


def test_normal_does_not_modify_reading() -> None:
    reading, _ = Scenario("normal", rng=random.Random(1)).tick(BASE, now=0)
    assert reading == BASE


def test_memory_leak_ramps_and_fails_then_recovers() -> None:
    sc = Scenario("memory_leak", ramp_minutes=10, down_minutes=2, rng=random.Random(1))
    start, _ = sc.tick(BASE, now=0)
    half, _ = sc.tick(BASE, now=300)
    assert start["mem_percent"] == 40 and 60 < half["mem_percent"] < 80
    end, events = sc.tick(BASE, now=600)
    failure = [e for e in events if e["source"] == "scenario" and e["level"] == "critical"]
    assert end["mem_percent"] == pytest.approx(98)
    assert failure and failure[0]["attributes"]["failure"] is True
    down, _ = sc.tick(BASE, now=650)
    assert down["is_available"] is False
    recovered, events = sc.tick(BASE, now=721)
    assert recovered["is_available"] is True and recovered["mem_percent"] == 40
    assert any("recuperado" in e["message"] for e in events)


def test_error_burst_generates_http_errors() -> None:
    sc = Scenario("error_burst", ramp_minutes=10, rng=random.Random(1))
    sc.tick(BASE, now=0)
    reading, events = sc.tick(BASE, now=540)
    assert reading["error_rate"] > 20
    assert sum(1 for e in events if e["level"] == "error") >= 7
