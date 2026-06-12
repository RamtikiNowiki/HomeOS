"""Creality K2 Plus integration service.

Currently returns mock data. The K2 Plus exposes a Moonraker-compatible API,
so when you're ready, set CREALITY_K2_HOST and implement get_status() against:

    GET http://{host}:7125/printer/objects/query?print_stats&display_status&heater_bed&extruder
"""
from flask import current_app


_MOCK_STATUS = {
    "online": True,
    "state": "printing",          # printing | paused | complete | standby | error
    "print_name": "Voron_Cube.gcode",
    "progress": 68,               # percent
    "time_elapsed": "1h 29m",
    "time_remaining": "42m",
    "nozzle_temp": 215.0,
    "nozzle_target": 215.0,
    "bed_temp": 60.1,
    "bed_target": 60.0,
    "layer_current": 142,
    "layer_total": 209,
    "filament_used_m": 12.4,
}


class CrealityK2Service:
    """Client for the K2 Plus print status API (mocked for now)."""

    def __init__(self):
        self.host = current_app.config.get("CREALITY_K2_HOST", "")

    @property
    def is_mock(self) -> bool:
        return not self.host

    def get_status(self) -> dict:
        if self.is_mock:
            return dict(_MOCK_STATUS)
        raise NotImplementedError("Real K2 Plus client not wired up yet")
