# COLLECTOR/collector.py
"""Agente de Ranger: lee métricas con psutil y las envía a la API (POST /ingest/*).

Variables de entorno: API_URL, COLLECTOR_API_KEY, COLLECT_INTERVAL, HOSTNAME_OVERRIDE,
SCENARIO, SCENARIO_RAMP_MINUTES, HOST_KIND, HOST_ENVIRONMENT, HOST_AREA, LOG_LEVEL.
Si la API no responde, las lecturas y eventos se guardan en un buffer en memoria y se
reenvían en el siguiente ciclo (B2).
"""

import logging
import os
import platform
import socket
import sys
import time
from collections import deque
from datetime import UTC, datetime
from typing import Any

import psutil
import requests

from scenarios import Scenario

API_URL = os.environ.get("API_URL", "http://localhost:8000/api/v1").rstrip("/")
API_KEY = os.environ.get("COLLECTOR_API_KEY", "")
INTERVAL = float(os.environ.get("COLLECT_INTERVAL", "10"))
HOSTNAME = os.environ.get("HOSTNAME_OVERRIDE") or socket.gethostname()
SCENARIO = os.environ.get("SCENARIO", "normal").strip()
RAMP_MINUTES = float(os.environ.get("SCENARIO_RAMP_MINUTES", "30"))
BATCH_SIZE = 500
BUFFER_MAX = 10_000
TIMEOUT = 5

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s collector: %(message)s",
)
log = logging.getLogger("collector")


class ApiError(Exception):
    pass


class Collector:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers["X-Collector-Key"] = API_KEY
        self.scenario = Scenario(SCENARIO, ramp_minutes=RAMP_MINUTES)
        self.metrics_buffer: deque[dict[str, Any]] = deque(maxlen=BUFFER_MAX)
        self.events_buffer: deque[dict[str, Any]] = deque(maxlen=BUFFER_MAX)
        self.registered = False
        self._last_net = psutil.net_io_counters()
        self._last_net_time = time.monotonic()
        self._health_url = API_URL.split("/api/")[0] + "/health"
        psutil.cpu_percent(percpu=True)  # primera llamada inicializa el contador

    # ---------- API ----------
    def _post(self, path: str, payload: dict[str, Any]) -> requests.Response:
        try:
            res = self.session.post(f"{API_URL}{path}", json=payload, timeout=TIMEOUT)
        except requests.RequestException as exc:
            raise ApiError(f"API no disponible: {exc}") from exc
        if res.status_code == 404 and path != "/ingest/register":
            self.registered = False
        if res.status_code >= 400:
            raise ApiError(f"{path} → {res.status_code}: {res.text[:200]}")
        return res

    def register(self) -> None:
        mem = psutil.virtual_memory()
        payload = {
            "hostname": HOSTNAME,
            "kind": os.environ.get("HOST_KIND", "server"),
            "environment": os.environ.get("HOST_ENVIRONMENT", "dev"),
            "os": f"{platform.system()} {platform.release()}"[:80],
            "cpu_cores": psutil.cpu_count() or 1,
            "mem_total_mb": int(mem.total / 1024 / 1024),
            "ip_address": self._local_ip(),
        }
        if os.environ.get("HOST_AREA"):
            payload["area"] = os.environ["HOST_AREA"]
        host_id = self._post("/ingest/register", payload).json()["host_id"]
        self.registered = True
        log.info("Registrado como %s (host_id=%s, escenario=%s)", HOSTNAME, host_id, SCENARIO)

    def flush(self) -> None:
        for path, key, buffer in (
            ("/ingest/metrics", "readings", self.metrics_buffer),
            ("/ingest/events", "events", self.events_buffer),
        ):
            while buffer:
                chunk = [buffer[i] for i in range(min(BATCH_SIZE, len(buffer)))]
                self._post(path, {"hostname": HOSTNAME, key: chunk})
                for _ in chunk:
                    buffer.popleft()

    # ---------- lecturas ----------
    @staticmethod
    def _local_ip() -> str | None:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return None

    def _latency_ms(self) -> float | None:
        start = time.perf_counter()
        try:
            self.session.get(self._health_url, timeout=TIMEOUT)
        except requests.RequestException:
            return None
        return round((time.perf_counter() - start) * 1000, 1)

    def _disk_partitions(self) -> list[dict[str, Any]]:
        partitions = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except (PermissionError, OSError):
                continue
            partitions.append(
                {
                    "mount": part.mountpoint,
                    "percent": usage.percent,
                    "used_gb": round(usage.used / 1024**3, 2),
                    "total_gb": round(usage.total / 1024**3, 2),
                }
            )
        return partitions[:64]

    def read(self) -> dict[str, Any]:
        mem = psutil.virtual_memory()
        root = "C:\\" if sys.platform == "win32" else "/"
        net = psutil.net_io_counters()
        now = time.monotonic()
        elapsed = max(now - self._last_net_time, 1e-6)
        sent_bps = max(0.0, (net.bytes_sent - self._last_net.bytes_sent) / elapsed)
        recv_bps = max(0.0, (net.bytes_recv - self._last_net.bytes_recv) / elapsed)
        self._last_net, self._last_net_time = net, now
        per_core = psutil.cpu_percent(percpu=True)
        return {
            "ts": datetime.now(UTC).isoformat(),
            "cpu_percent": round(sum(per_core) / max(len(per_core), 1), 2),
            "cpu_per_core": per_core,
            "mem_percent": mem.percent,
            "mem_used_mb": int(mem.used / 1024 / 1024),
            "disk_percent": psutil.disk_usage(root).percent,
            "disk_partitions": self._disk_partitions(),
            "net_sent_bps": round(sent_bps, 2),
            "net_recv_bps": round(recv_bps, 2),
            "latency_ms": self._latency_ms(),
            "error_rate": 0.0,
            "is_available": True,
        }

    # ---------- ciclo ----------
    def run_once(self) -> None:
        reading, events = self.scenario.tick(self.read(), time.monotonic())
        self.metrics_buffer.append(reading)
        self.events_buffer.extend(events)
        try:
            if not self.registered:
                self.register()
            self.flush()
            log.debug("Enviado: cpu=%.1f mem=%.1f", reading["cpu_percent"], reading["mem_percent"])
        except ApiError as exc:
            log.warning(
                "%s (buffer: %d lecturas, %d eventos)",
                exc,
                len(self.metrics_buffer),
                len(self.events_buffer),
            )

    def run(self) -> None:
        if not API_KEY:
            log.error("COLLECTOR_API_KEY no definido")
            sys.exit(1)
        log.info("Recolector iniciado → %s cada %ss", API_URL, INTERVAL)
        while True:
            started = time.monotonic()
            self.run_once()
            time.sleep(max(0.0, INTERVAL - (time.monotonic() - started)))


if __name__ == "__main__":
    Collector().run()
