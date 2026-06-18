"""Read Raspberry Pi host metrics from mounted /host paths (Docker volumes)."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

HOST_ROOT = Path(os.environ.get("HOST_ROOTFS", "/host/rootfs"))
HOST_PROC = Path(os.environ.get("HOST_PROC", "/host/proc"))
HOST_CPU_TEMP = Path(os.environ.get("HOST_CPU_TEMP", "/host/cpu_temp"))
HOST_THERMAL = Path(os.environ.get("HOST_THERMAL", "/host/sys/class/thermal"))
DOCKER_SOCK = Path(os.environ.get("DOCKER_HOST_SOCKET", "/var/run/docker.sock"))


def _cpu_temp_c() -> float | None:
    if HOST_CPU_TEMP.is_file():
        try:
            millideg = int(HOST_CPU_TEMP.read_text().strip())
            if millideg > 0:
                return round(millideg / 1000, 1)
        except (OSError, ValueError):
            pass
    if not HOST_THERMAL.is_dir():
        return None
    for zone in sorted(HOST_THERMAL.glob("thermal_zone*/temp")):
        try:
            millideg = int(zone.read_text().strip())
            if millideg > 0:
                return round(millideg / 1000, 1)
        except (OSError, ValueError):
            continue
    return None


def _memory() -> dict:
    meminfo = HOST_PROC / "meminfo"
    if not meminfo.is_file():
        return {"used_pct": None, "total_mb": None, "avail_mb": None}
    info: dict[str, int] = {}
    try:
        for line in meminfo.read_text().splitlines():
            if ":" not in line:
                continue
            key, rest = line.split(":", 1)
            info[key.strip()] = int(rest.strip().split()[0])
    except OSError:
        return {"used_pct": None, "total_mb": None, "avail_mb": None}

    total = info.get("MemTotal")
    avail = info.get("MemAvailable", info.get("MemFree"))
    if not total or avail is None:
        return {"used_pct": None, "total_mb": None, "avail_mb": None}
    used_pct = round((1 - avail / total) * 100)
    return {
        "used_pct": used_pct,
        "total_mb": total // 1024,
        "avail_mb": avail // 1024,
    }


def _disk() -> dict:
    root = HOST_ROOT if HOST_ROOT.is_dir() else Path("/")
    try:
        st = os.statvfs(root)
    except OSError:
        return {"used_pct": None, "total_gb": None, "free_gb": None}
    total = st.f_blocks * st.f_frsize
    free = st.f_bavail * st.f_frsize
    if total <= 0:
        return {"used_pct": None, "total_gb": None, "free_gb": None}
    used_pct = round((1 - free / total) * 100)
    return {
        "used_pct": used_pct,
        "total_gb": round(total / (1024**3), 1),
        "free_gb": round(free / (1024**3), 1),
    }


def _docker_services() -> list[dict]:
    if not DOCKER_SOCK.is_socket():
        return []
    try:
        proc = subprocess.run(
            [
                "curl",
                "-s",
                "--max-time",
                "3",
                "--unix-socket",
                str(DOCKER_SOCK),
                "http://localhost/containers/json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if proc.returncode != 0 or not proc.stdout.strip():
        return []
    try:
        raw = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []

    services = []
    for c in raw:
        names = c.get("Names") or []
        name = names[0].lstrip("/") if names else c.get("Id", "")[:12]
        if "home-os" not in name and "homeassistant" not in name:
            continue
        services.append({"name": name, "state": c.get("State", "unknown")})
    services.sort(key=lambda s: s["name"])
    return services


def get_host_health() -> dict:
    mem = _memory()
    disk = _disk()
    temp = _cpu_temp_c()
    services = _docker_services()
    online = sum(1 for s in services if s["state"] == "running")

    return {
        "available": temp is not None or mem["used_pct"] is not None or disk["used_pct"] is not None,
        "cpu_temp_c": temp,
        "cpu_temp_warn": temp is not None and temp >= 70,
        "memory": mem,
        "disk": disk,
        "docker": {
            "services": services,
            "running": online,
            "total": len(services),
        },
    }
