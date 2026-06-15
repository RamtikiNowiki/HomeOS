"""Creality K2 Plus integration via Moonraker API.

The K2 Plus runs Klipper with Moonraker on port **7125** by default.
Set ``CREALITY_K2_HOST`` to the printer's LAN IP (no ``http://``)::

    CREALITY_K2_HOST=192.168.1.50
    CREALITY_K2_PORT=7125          # optional, default 7125
    CREALITY_K2_API_KEY=            # optional, if Moonraker auth is enabled

Useful Moonraker endpoints wired here:
- ``GET  /printer/objects/query`` — live status (temps, progress, filename)
- ``POST /printer/print/pause``   — pause active print
- ``POST /printer/print/resume``  — resume paused print
- ``POST /printer/print/cancel``  — cancel job (with confirmation in UI)
"""
from __future__ import annotations

import math
import urllib.request
from datetime import datetime

from flask import current_app

from ..integrations.http_client import HttpError, request_json

_MOCK_STATUS = {
    "online": True,
    "state": "printing",
    "print_name": "Voron_Cube.gcode",
    "progress": 68,
    "time_elapsed": "1h 29m",
    "time_remaining": "42m",
    "nozzle_temp": 215.0,
    "nozzle_target": 215.0,
    "bed_temp": 60.1,
    "bed_target": 60.0,
    "chamber_temp": None,
    "layer_current": 142,
    "layer_total": 209,
    "filament_used_m": 12.4,
    "fan_speed_pct": 45,
    "print_speed_pct": 100,
    "status_message": "Printing layer 142/209",
    "file_path": "/gcodes/Voron_Cube.gcode",
    "can_pause": True,
    "can_resume": False,
    "can_cancel": True,
    "host": None,
    "error": None,
}

_QUERY_OBJECTS = (
    "print_stats",
    "display_status",
    "virtual_sdcard",
    "toolhead",
    "extruder",
    "heater_bed",
    "fan",
    "gcode_move",
)

PREHEAT_PRESETS = (
    {"id": "pla", "label": "PLA", "nozzle": 210, "bed": 60},
    {"id": "petg", "label": "PETG", "nozzle": 230, "bed": 80},
    {"id": "abs", "label": "ABS", "nozzle": 250, "bed": 100},
    {"id": "off", "label": "Cool down", "nozzle": 0, "bed": 0},
)


def _format_duration(seconds: float | None) -> str:
    if seconds is None or seconds < 0 or math.isnan(seconds):
        return "—"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {sec}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


class CrealityK2Service:
    """Client for the K2 Plus Moonraker API."""

    def __init__(self):
        self.host = (current_app.config.get("CREALITY_K2_HOST") or "").strip()
        self.port = int(current_app.config.get("CREALITY_K2_PORT") or 7125)
        self.api_key = (current_app.config.get("CREALITY_K2_API_KEY") or "").strip()

    @property
    def is_mock(self) -> bool:
        return not self.host

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        return headers

    def _get(self, path: str, params: str = "") -> dict:
        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{params}"
        data = request_json("GET", url, headers=self._headers())
        if not isinstance(data, dict):
            raise HttpError(0, "Invalid Moonraker response")
        if data.get("error"):
            raise HttpError(0, str(data["error"]))
        return data

    def _post(self, path: str, body: dict | None = None) -> dict:
        data = request_json("POST", f"{self.base_url}{path}", headers=self._headers(), body=body or {})
        if not isinstance(data, dict):
            raise HttpError(0, "Invalid Moonraker response")
        if data.get("error"):
            raise HttpError(0, str(data["error"]))
        return data

    def _query_objects(self) -> dict:
        obj_list = "&".join(_QUERY_OBJECTS)
        data = self._get("/printer/objects/query", obj_list)
        return (data.get("result") or {}).get("status") or {}

    @staticmethod
    def _normalize_state(raw: str) -> str:
        raw = (raw or "standby").lower()
        if raw in ("printing", "paused", "complete", "cancelled", "error", "standby"):
            return "cancelled" if raw == "cancelled" else raw
        if raw in ("ready", "idle"):
            return "standby"
        return raw

    def _build_status(self, status: dict) -> dict:
        print_stats = status.get("print_stats") or {}
        display = status.get("display_status") or {}
        vcard = status.get("virtual_sdcard") or {}
        extruder = status.get("extruder") or {}
        bed = status.get("heater_bed") or {}
        fan = status.get("fan") or {}
        gcode = status.get("gcode_move") or {}

        state = self._normalize_state(print_stats.get("state"))
        progress_raw = display.get("progress")
        if progress_raw is None:
            progress_raw = vcard.get("progress")
        progress = int(round(float(progress_raw or 0) * 100))

        filename = print_stats.get("filename") or vcard.get("file_path") or "—"
        if isinstance(filename, str) and "/" in filename:
            filename = filename.rsplit("/", 1)[-1]

        total_duration = print_stats.get("total_duration")
        print_duration = print_stats.get("print_duration")
        filament_mm = print_stats.get("filament_used") or 0
        filament_m = round(float(filament_mm) / 1000.0, 2) if filament_mm else 0.0

        eta_seconds = None
        if print_duration and progress > 0 and progress < 100:
            eta_seconds = (float(print_duration) / progress) * (100 - progress)

        fan_speed = fan.get("speed")
        speed_factor = gcode.get("speed_factor")

        info = status.get("info") or {}
        layer_current = info.get("current_layer") or display.get("layer")
        layer_total = info.get("total_layer")

        return {
            "online": True,
            "state": state,
            "print_name": filename,
            "progress": max(0, min(100, progress)),
            "time_elapsed": _format_duration(print_duration or total_duration),
            "time_remaining": _format_duration(eta_seconds),
            "nozzle_temp": round(float(extruder.get("temperature") or 0), 1),
            "nozzle_target": round(float(extruder.get("target") or 0), 1),
            "bed_temp": round(float(bed.get("temperature") or 0), 1),
            "bed_target": round(float(bed.get("target") or 0), 1),
            "chamber_temp": None,
            "layer_current": layer_current or "—",
            "layer_total": layer_total or "—",
            "filament_used_m": filament_m,
            "fan_speed_pct": int(round(float(fan_speed or 0) * 100)) if fan_speed is not None else None,
            "print_speed_pct": int(round(float(speed_factor or 1) * 100)) if speed_factor else 100,
            "status_message": display.get("message") or print_stats.get("message") or state.capitalize(),
            "file_path": vcard.get("file_path") or print_stats.get("filename"),
            "can_pause": state == "printing",
            "can_resume": state == "paused",
            "can_cancel": state in ("printing", "paused"),
            "host": self.host,
            "error": None,
        }

    def get_status(self) -> dict:
        if self.is_mock:
            return dict(_MOCK_STATUS)
        try:
            status = self._query_objects()
            return self._build_status(status)
        except HttpError as exc:
            offline = dict(_MOCK_STATUS)
            offline.update({
                "online": False,
                "state": "offline",
                "print_name": "—",
                "progress": 0,
                "time_elapsed": "—",
                "time_remaining": "—",
                "can_pause": False,
                "can_resume": False,
                "can_cancel": False,
                "error": str(exc),
                "host": self.host,
            })
            return offline

    def pause_print(self) -> dict:
        if self.is_mock:
            _MOCK_STATUS["state"] = "paused"
            _MOCK_STATUS["can_pause"] = False
            _MOCK_STATUS["can_resume"] = True
            return self.get_status()
        self._post("/printer/print/pause")
        return self.get_status()

    def resume_print(self) -> dict:
        if self.is_mock:
            _MOCK_STATUS["state"] = "printing"
            _MOCK_STATUS["can_pause"] = True
            _MOCK_STATUS["can_resume"] = False
            return self.get_status()
        self._post("/printer/print/resume")
        return self.get_status()

    def cancel_print(self) -> dict:
        if self.is_mock:
            _MOCK_STATUS["state"] = "standby"
            _MOCK_STATUS["progress"] = 0
            _MOCK_STATUS["can_pause"] = False
            _MOCK_STATUS["can_resume"] = False
            _MOCK_STATUS["can_cancel"] = False
            return self.get_status()
        self._post("/printer/print/cancel")
        return self.get_status()

    def preheat(self, nozzle: float, bed: float, wait: bool = False) -> dict:
        if self.is_mock:
            _MOCK_STATUS["nozzle_target"] = float(nozzle)
            _MOCK_STATUS["bed_target"] = float(bed)
            return self.get_status()

        lines = [
            f"SET_HEATER_TEMPERATURE HEATER=extruder TARGET={nozzle}",
            f"SET_HEATER_TEMPERATURE HEATER=heater_bed TARGET={bed}",
        ]
        if wait and nozzle > 0:
            lines.append(f"TEMPERATURE_WAIT SENSOR=extruder MINIMUM={max(0, nozzle - 3)}")
        if wait and bed > 0:
            lines.append(f"TEMPERATURE_WAIT SENSOR=heater_bed MINIMUM={max(0, bed - 3)}")
        self._post("/printer/gcode/script", {"script": "\n".join(lines)})
        return self.get_status()

    def get_print_history(self, limit: int = 8) -> list[dict]:
        if self.is_mock:
            return [
                {
                    "filename": "Demo_Part.gcode",
                    "status": "completed",
                    "finished": "Jun 10",
                    "duration": "2h 14m",
                    "filament_m": 12.4,
                }
            ]

        try:
            data = self._get("/server/history/list", f"limit={limit}&order=desc")
        except HttpError:
            return []

        jobs = (data.get("result") or {}).get("jobs") or []
        history: list[dict] = []
        for job in jobs:
            if not isinstance(job, dict):
                continue
            filename = job.get("filename") or "—"
            if isinstance(filename, str) and "/" in filename:
                filename = filename.rsplit("/", 1)[-1]
            end_time = job.get("end_time")
            finished = "—"
            if end_time:
                finished = datetime.fromtimestamp(float(end_time)).strftime("%b %d")
            history.append({
                "filename": filename,
                "status": job.get("status") or "unknown",
                "finished": finished,
                "duration": _format_duration(job.get("print_duration")),
                "filament_m": round(float(job.get("filament_used") or 0) / 1000.0, 1),
            })
        return history

    def connection_info(self) -> dict:
        return {
            "configured": not self.is_mock,
            "host": self.host or None,
            "port": self.port,
            "base_url": self.base_url if self.host else None,
        }

    def _fluidd_url(self) -> str | None:
        override = (current_app.config.get("CREALITY_K2_FLUIDD_URL") or "").strip()
        if override:
            return override
        if self.host:
            return f"http://{self.host}:4408"
        return None

    def _configured_snapshot_url(self) -> str | None:
        override = (current_app.config.get("CREALITY_K2_CAMERA_SNAPSHOT_URL") or "").strip()
        if override:
            return override
        return None

    @staticmethod
    def _snapshot_from_stream(stream_url: str | None) -> str | None:
        if not stream_url:
            return None
        if "action=stream" in stream_url:
            return stream_url.replace("action=stream", "action=snapshot")
        if stream_url.endswith("/stream"):
            return stream_url.rsplit("/", 1)[0] + "/snapshot"
        return None

    def get_camera_info(self) -> dict:
        fluidd_url = self._fluidd_url()
        if self.is_mock:
            return {
                "available": False,
                "name": None,
                "fluidd_url": fluidd_url,
                "needs_setup": False,
                "setup_hint": None,
            }

        snapshot_url = self._configured_snapshot_url()
        name = "K2 Camera"
        try:
            data = self._get("/server/webcams/list")
            webcams = (data.get("result") or {}).get("webcams") or []
            if webcams:
                cam = webcams[0]
                name = cam.get("name") or name
                snapshot_url = (
                    cam.get("snapshot_url")
                    or self._snapshot_from_stream(cam.get("stream_url"))
                    or snapshot_url
                )
        except HttpError:
            pass

        available = bool(snapshot_url)
        return {
            "available": available,
            "name": name if available else None,
            "fluidd_url": fluidd_url,
            "needs_setup": not available,
            "setup_hint": (
                "The K2 Plus camera uses Creality WebRTC. Install "
                "Helper Script → option 11 (Camera Support) on the printer, "
                "then reboot — Moonraker will expose a snapshot stream we can embed here."
            ),
        }

    def fetch_webcam_snapshot(self) -> tuple[bytes | None, str]:
        if self.is_mock:
            return None, "image/jpeg"

        snapshot_url = self._configured_snapshot_url()
        try:
            data = self._get("/server/webcams/list")
            webcams = (data.get("result") or {}).get("webcams") or []
            if webcams:
                cam = webcams[0]
                snapshot_url = (
                    cam.get("snapshot_url")
                    or self._snapshot_from_stream(cam.get("stream_url"))
                    or snapshot_url
                )
        except HttpError:
            pass

        if not snapshot_url:
            return None, "image/jpeg"

        req = urllib.request.Request(snapshot_url, headers={"User-Agent": "HomeOS/1.0"})
        if self.api_key:
            req.add_header("X-Api-Key", self.api_key)
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                content_type = resp.headers.get("Content-Type", "image/jpeg")
                return resp.read(), content_type.split(";")[0].strip()
        except OSError as exc:
            raise HttpError(0, f"Camera snapshot failed: {exc}") from exc
