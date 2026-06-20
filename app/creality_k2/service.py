"""Creality K2 Plus integration via Moonraker API.

The K2 Plus runs Klipper with Moonraker on port **7125** by default.
Set ``CREALITY_K2_HOST`` to the printer's LAN IP (no ``http://``)::

    CREALITY_K2_HOST=192.168.1.50
    CREALITY_K2_PORT=7125          # optional, default 7125
    CREALITY_K2_API_KEY=            # optional, if Moonraker auth is enabled

Creality Print / touchscreen jobs often skip standard ``print_stats`` updates.
We infer active printing from ``motion_report`` and read Creality ``virtual_sdcard``
extensions (layer, layer_count, cur_print_data).
"""
from __future__ import annotations

import math
import urllib.error
import urllib.request
from datetime import datetime
from urllib.parse import quote

from flask import current_app

from ..integrations.http_client import HttpError, request_json

_MOCK_STATUS = {
    "online": True,
    "state": "printing",
    "print_name": "Voron_Cube.gcode",
    "progress": 68,
    "progress_unknown": False,
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

# Klipper objects polled each status refresh (Creality K2 field names included).
_QUERY_OBJECTS = (
    "print_stats",
    "display_status",
    "virtual_sdcard",
    "toolhead",
    "extruder",
    "heater_bed",
    "gcode_move",
    "motion_report",
    "output_pin fan0",
    "output_pin fan1",
    "output_pin fan2",
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


def _normalize_state(raw: str) -> str:
    raw = (raw or "standby").lower()
    if raw in ("printing", "paused", "complete", "cancelled", "error", "standby"):
        return "cancelled" if raw == "cancelled" else raw
    if raw in ("ready", "idle"):
        return "standby"
    return raw


def _infer_printing_from_motion(motion: dict, extruder: dict, klipper_state: str) -> bool:
    """Detect Creality cloud/screen prints that never flip print_stats to printing."""
    if klipper_state in ("printing", "paused"):
        return klipper_state == "printing"

    vel = float(motion.get("live_velocity") or 0)
    e_vel = float(motion.get("live_extruder_velocity") or 0)
    trapq = motion.get("trapq") or []
    nozzle_target = float(extruder.get("target") or 0)
    nozzle_temp = float(extruder.get("temperature") or 0)

    if "toolhead" not in trapq or "extruder" not in trapq:
        return False
    if nozzle_target < 120 and nozzle_temp < 120:
        return False
    if e_vel > 0.02:
        return True
    if vel > 1.0 and nozzle_target >= 120:
        return True
    return False


def _progress_from_cur_print_data(cur: dict) -> float | None:
    if not isinstance(cur, dict) or not cur:
        return None
    for key in ("progress", "percent", "pct", "print_progress"):
        val = cur.get(key)
        if val is None:
            continue
        val = float(val)
        if val > 1.0:
            val /= 100.0
        return max(0.0, min(1.0, val))
    meta = cur.get("metadata") or {}
    est = meta.get("estimated_time")
    dur = cur.get("print_duration")
    if est and dur:
        return max(0.0, min(1.0, float(dur) / float(est)))
    return None


def _state_from_cur_print_data(cur: dict) -> str | None:
    if not isinstance(cur, dict):
        return None
    raw = (cur.get("status") or "").lower()
    if raw in ("printing", "paused", "completed", "cancelled", "error"):
        return "complete" if raw == "completed" else raw
    return None


def _part_fan_speed_pct(status: dict) -> int | None:
    speeds: list[float] = []
    for key in ("output_pin fan0", "output_pin fan1", "output_pin fan2", "fan"):
        obj = status.get(key) or {}
        val = obj.get("value")
        if val is None:
            val = obj.get("speed")
        if val is not None:
            speeds.append(float(val))
    if not speeds:
        return None
    return int(round(max(speeds) * 100))


def build_status_from_moonraker(status: dict, host: str | None = None) -> dict:
    """Parse Moonraker object query into UI-friendly status (testable without Flask)."""
    print_stats = status.get("print_stats") or {}
    display = status.get("display_status") or {}
    vcard = status.get("virtual_sdcard") or {}
    cur_print = vcard.get("cur_print_data") or {}
    cur_meta = cur_print.get("metadata") or {}
    extruder = status.get("extruder") or {}
    bed = status.get("heater_bed") or {}
    gcode = status.get("gcode_move") or {}
    motion = status.get("motion_report") or {}

    klipper_state = _normalize_state(print_stats.get("state"))
    inferred_printing = _infer_printing_from_motion(motion, extruder, klipper_state)
    state = klipper_state
    cur_state = _state_from_cur_print_data(cur_print)
    if cur_state and klipper_state == "standby":
        state = cur_state
    elif state == "standby" and inferred_printing:
        state = "printing"

    progress_raw = display.get("progress")
    if progress_raw is None:
        progress_raw = vcard.get("progress")
    if progress_raw is None:
        progress_raw = _progress_from_cur_print_data(cur_print)

    if progress_raw is None and vcard.get("is_active"):
        file_size = float(vcard.get("file_size") or 0)
        file_pos = float(vcard.get("file_position") or 0)
        if file_size > 0:
            progress_raw = file_pos / file_size

    progress = int(round(float(progress_raw or 0) * 100))
    progress_unknown = (
        state == "printing"
        and progress == 0
        and not vcard.get("is_active")
        and not print_stats.get("filename")
        and not cur_print.get("filename")
        and vcard.get("layer") in (None, 0, "")
    )

    filename = print_stats.get("filename") or cur_print.get("filename") or vcard.get("file_path") or "—"
    if isinstance(filename, str) and "/" in filename:
        filename = filename.rsplit("/", 1)[-1]
    if filename in ("", "—") and state == "printing" and progress_unknown:
        filename = "Active print"
    print_duration = print_stats.get("print_duration") or cur_print.get("print_duration")
    total_duration = print_stats.get("total_duration") or cur_print.get("total_duration")

    filament_mm = print_stats.get("filament_used") or cur_print.get("filament_used") or 0
    filament_m = round(float(filament_mm) / 1000.0, 2) if filament_mm else 0.0

    eta_seconds = None
    if print_duration and progress > 0 and progress < 100:
        eta_seconds = (float(print_duration) / progress) * (100 - progress)
    elif cur_meta.get("estimated_time") and print_duration:
        eta_seconds = max(0.0, float(cur_meta["estimated_time"]) - float(print_duration))

    speed_factor = gcode.get("speed_factor")

    info = print_stats.get("info") or {}
    layer_current = (
        info.get("current_layer")
        or vcard.get("layer")
        or display.get("layer")
    )
    layer_total = info.get("total_layer") or vcard.get("layer_count") or cur_meta.get("layer_count")

    if progress_unknown:
        msg = display.get("message") or print_stats.get("message") or "Printing"
    else:
        msg = display.get("message") or print_stats.get("message") or state.capitalize()

    return {
        "online": True,
        "state": state,
        "print_name": filename,
        "progress": max(0, min(100, progress)),
        "progress_unknown": progress_unknown,
        "time_elapsed": _format_duration(print_duration or total_duration),
        "time_remaining": _format_duration(eta_seconds),
        "nozzle_temp": round(float(extruder.get("temperature") or 0), 1),
        "nozzle_target": round(float(extruder.get("target") or 0), 1),
        "bed_temp": round(float(bed.get("temperature") or 0), 1),
        "bed_target": round(float(bed.get("target") or 0), 1),
        "chamber_temp": None,
        "layer_current": layer_current if layer_current not in (None, 0, "") else "—",
        "layer_total": layer_total if layer_total not in (None, 0, "") else "—",
        "filament_used_m": filament_m,
        "fan_speed_pct": _part_fan_speed_pct(status),
        "print_speed_pct": int(round(float(speed_factor or 1) * 100)) if speed_factor else 100,
        "status_message": msg,
        "file_path": vcard.get("file_path") or print_stats.get("filename"),
        "can_pause": state == "printing",
        "can_resume": state == "paused",
        "can_cancel": state in ("printing", "paused"),
        "host": host,
        "error": None,
    }


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
        obj_list = "&".join(quote(obj, safe="") for obj in _QUERY_OBJECTS)
        data = self._get("/printer/objects/query", obj_list)
        return (data.get("result") or {}).get("status") or {}

    def _build_status(self, status: dict) -> dict:
        return build_status_from_moonraker(status, host=self.host)

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
                "progress_unknown": False,
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
    def _go2rtc_src_from_cam(cam: dict | None) -> str:
        if not cam:
            return "k2plus"
        for key in ("snapshot_url", "stream_url"):
            url = cam.get(key) or ""
            if "src=" in url:
                return url.split("src=", 1)[1].split("&", 1)[0] or "k2plus"
        return "k2plus"

    @staticmethod
    def _normalize_go2rtc_url(url: str) -> str:
        """Helper Script registers go2rtc on :4409 nginx; live go2rtc is on :1984."""
        if ":4409/go2rtc/" in url:
            return url.replace(":4409/go2rtc/", ":1984/")
        return url

    def _snapshot_candidates(self, cam: dict | None = None) -> list[str]:
        urls: list[str] = []
        seen: set[str] = set()
        src = self._go2rtc_src_from_cam(cam) if cam else "k2plus"

        def add(url: str | None) -> None:
            if not url:
                return
            url = self._normalize_go2rtc_url(url.strip())
            if url not in seen:
                seen.add(url)
                urls.append(url)

        add(self._configured_snapshot_url())
        if self.host:
            add(f"http://{self.host}:1984/api/frame.jpeg?src={src}")
        if cam:
            add(cam.get("snapshot_url"))
            add(self._snapshot_from_stream(cam.get("stream_url")))

        return urls

    def get_go2rtc_src(self) -> str:
        src = "k2plus"
        try:
            data = self._get("/server/webcams/list")
            webcams = (data.get("result") or {}).get("webcams") or []
            if webcams:
                src = self._go2rtc_src_from_cam(webcams[0])
        except HttpError:
            pass
        return src

    def get_mjpeg_stream_url(self) -> str | None:
        """Legacy MJPEG — K2 go2rtc often returns empty body; prefer MP4."""
        if self.is_mock or not self.host:
            return None
        return f"http://{self.host}:1984/api/stream.mjpeg?src={self.get_go2rtc_src()}"

    def get_video_stream_url(self) -> str | None:
        """go2rtc H264 → MP4 progressive stream (works on K2 Plus)."""
        if self.is_mock or not self.host:
            return None
        return f"http://{self.host}:1984/api/stream.mp4?src={self.get_go2rtc_src()}"

    def iter_mjpeg_stream(self):
        """Yield chunks from the printer go2rtc MJPEG stream."""
        stream_url = self.get_mjpeg_stream_url()
        if not stream_url:
            raise HttpError(0, "MJPEG stream not configured")
        yield from self._iter_go2rtc_stream(stream_url)

    def iter_video_stream(self):
        """Yield chunks from the printer go2rtc MP4 stream."""
        stream_url = self.get_video_stream_url()
        if not stream_url:
            raise HttpError(0, "Video stream not configured")
        yield from self._iter_go2rtc_stream(stream_url)

    def _iter_go2rtc_stream(self, stream_url: str):
        req = urllib.request.Request(stream_url, headers={"User-Agent": "HomeOS/1.0"})
        if self.api_key:
            req.add_header("X-Api-Key", self.api_key)
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                while True:
                    chunk = resp.read(16384)
                    if not chunk:
                        break
                    yield chunk
        except urllib.error.URLError as exc:
            raise HttpError(0, f"Camera stream failed: {exc}") from exc

    def _fetch_snapshot_bytes(self, snapshot_url: str) -> tuple[bytes, str]:
        req = urllib.request.Request(snapshot_url, headers={"User-Agent": "HomeOS/1.0"})
        if self.api_key:
            req.add_header("X-Api-Key", self.api_key)
        with urllib.request.urlopen(req, timeout=8) as resp:
            content_type = resp.headers.get("Content-Type", "image/jpeg")
            data = resp.read()
        if len(data) < 500:
            raise OSError("snapshot response too small")
        return data, content_type.split(";")[0].strip() or "image/jpeg"

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
                "stream_available": False,
                "name": None,
                "fluidd_url": fluidd_url,
                "needs_setup": False,
                "setup_hint": None,
            }

        snapshot_url = self._configured_snapshot_url()
        stream_available = False  # K2 go2rtc MJPEG/MP4 breaks in-browser; use snapshot poll
        name = "K2 Camera"
        cam: dict | None = None
        try:
            data = self._get("/server/webcams/list")
            webcams = (data.get("result") or {}).get("webcams") or []
            if webcams:
                cam = webcams[0]
                name = cam.get("name") or name
                candidates = self._snapshot_candidates(cam)
                if candidates:
                    snapshot_url = candidates[0]
        except HttpError:
            pass

        if not snapshot_url and self.host:
            snapshot_url = f"http://{self.host}:1984/api/frame.jpeg?src=k2plus"

        available = bool(self.host or cam or snapshot_url)
        go2rtc_src = self._go2rtc_src_from_cam(cam) if cam else "k2plus"
        return {
            "available": available,
            "stream_available": bool(self.host),
            "go2rtc_ws_path": f"/printer/go2rtc/api/ws?src={go2rtc_src}" if self.host else None,
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

        if self.host:
            src = "k2plus"
            try:
                return self._fetch_snapshot_bytes(
                    f"http://{self.host}:1984/api/frame.jpeg?src={src}"
                )
            except OSError:
                pass

        cam: dict | None = None
        try:
            data = self._get("/server/webcams/list")
            webcams = (data.get("result") or {}).get("webcams") or []
            if webcams:
                cam = webcams[0]
        except HttpError:
            pass

        errors: list[str] = []
        for snapshot_url in self._snapshot_candidates(cam):
            try:
                return self._fetch_snapshot_bytes(snapshot_url)
            except OSError as exc:
                errors.append(f"{snapshot_url}: {exc}")

        if errors:
            raise HttpError(0, "Camera snapshot failed — " + "; ".join(errors[-2:]))
        return None, "image/jpeg"
