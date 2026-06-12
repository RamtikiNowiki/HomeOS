"""Home Assistant integration service.

Uses the Home Assistant REST API when ``HOME_ASSISTANT_URL`` and
``HOME_ASSISTANT_TOKEN`` are set. Falls back to in-memory mock state otherwise.

Configure entity IDs in ``.env`` (comma-separated for lights)::

    HOME_ASSISTANT_URL=http://192.168.1.10:8123
    HOME_ASSISTANT_TOKEN=your-long-lived-token
    HOME_ASSISTANT_LIGHTS=light.living_room,light.desk_lamp
    HOME_ASSISTANT_SENSOR=sensor.living_room_temperature

Create a long-lived token in HA: Profile → Security → Long-Lived Access Tokens.
"""
from __future__ import annotations

from flask import current_app

from ..integrations.http_client import HttpError, request_json

_MOCK_LIGHTS = [
    {
        "entity_id": "light.living_room_leds",
        "name": "Living Room LEDs",
        "state": "on",
        "brightness": 80,
        "icon": "led-strip",
    },
    {
        "entity_id": "light.desk_lamp",
        "name": "Desk Lamp",
        "state": "off",
        "brightness": 0,
        "icon": "lamp",
    },
]

_MOCK_SENSOR = {
    "entity_id": "sensor.desk_temperature",
    "name": "Desk Sensor",
    "temperature": 22.4,
    "humidity": 41,
}


def _parse_csv(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


class HomeAssistantService:
    """Thin client around the Home Assistant REST API."""

    def __init__(self):
        self.base_url = (current_app.config.get("HOME_ASSISTANT_URL") or "").rstrip("/")
        self.token = current_app.config.get("HOME_ASSISTANT_TOKEN", "")
        self.light_entities = _parse_csv(current_app.config.get("HOME_ASSISTANT_LIGHTS", ""))
        self.sensor_entity = (current_app.config.get("HOME_ASSISTANT_SENSOR") or "").strip()

    @property
    def is_mock(self) -> bool:
        return not (self.base_url and self.token)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _get_state(self, entity_id: str) -> dict | None:
        try:
            return request_json(
                "GET",
                f"{self.base_url}/api/states/{entity_id}",
                headers=self._headers(),
            )
        except HttpError:
            return None

    def _call_service(self, domain: str, service: str, entity_id: str, **data) -> bool:
        payload = {"entity_id": entity_id, **data}
        try:
            request_json(
                "POST",
                f"{self.base_url}/api/services/{domain}/{service}",
                headers=self._headers(),
                body=payload,
            )
            return True
        except HttpError:
            return False

    @staticmethod
    def _light_from_state(state: dict) -> dict:
        attrs = state.get("attributes") or {}
        brightness = attrs.get("brightness")
        if brightness is None and state.get("state") == "on":
            brightness = 255
        return {
            "entity_id": state.get("entity_id", ""),
            "name": attrs.get("friendly_name") or state.get("entity_id", "Light"),
            "state": state.get("state", "unknown"),
            "brightness": int(round((brightness or 0) / 255 * 100)) if brightness else 0,
            "icon": "lamp",
        }

    @staticmethod
    def _sensor_from_state(state: dict) -> dict:
        attrs = state.get("attributes") or {}
        temp = attrs.get("temperature")
        if temp is None:
            try:
                temp = float(state.get("state"))
            except (TypeError, ValueError):
                temp = None
        humidity = attrs.get("humidity")
        return {
            "entity_id": state.get("entity_id", ""),
            "name": attrs.get("friendly_name") or state.get("entity_id", "Sensor"),
            "temperature": round(float(temp), 1) if temp is not None else None,
            "humidity": int(humidity) if humidity is not None else None,
        }

    def get_lights(self) -> list[dict]:
        if self.is_mock:
            return [dict(light) for light in _MOCK_LIGHTS]

        entities = self.light_entities or [
            eid for eid in self._discover_light_entities()
        ]
        lights = []
        for entity_id in entities:
            state = self._get_state(entity_id)
            if state:
                lights.append(self._light_from_state(state))
        return lights or [dict(_MOCK_LIGHTS[0])]

    def _discover_light_entities(self) -> list[str]:
        """Fallback when HOME_ASSISTANT_LIGHTS is unset — first few light.* entities."""
        try:
            states = request_json("GET", f"{self.base_url}/api/states", headers=self._headers())
        except HttpError:
            return []
        if not isinstance(states, list):
            return []
        return [
            s["entity_id"]
            for s in states
            if isinstance(s, dict)
            and str(s.get("entity_id", "")).startswith("light.")
        ][:6]

    def get_sensor(self) -> dict:
        if self.is_mock:
            return dict(_MOCK_SENSOR)

        entity_id = self.sensor_entity or "sensor.temperature"
        state = self._get_state(entity_id)
        if not state:
            return dict(_MOCK_SENSOR)
        return self._sensor_from_state(state)

    def toggle_light(self, entity_id: str) -> dict | None:
        if self.is_mock:
            for light in _MOCK_LIGHTS:
                if light["entity_id"] == entity_id:
                    light["state"] = "off" if light["state"] == "on" else "on"
                    light["brightness"] = 80 if light["state"] == "on" else 0
                    return dict(light)
            return None

        if not self._call_service("light", "toggle", entity_id):
            return None
        state = self._get_state(entity_id)
        return self._light_from_state(state) if state else None

    def set_light(self, entity_id: str, on: bool, brightness_pct: int | None = None) -> dict | None:
        if self.is_mock:
            for light in _MOCK_LIGHTS:
                if light["entity_id"] == entity_id:
                    light["state"] = "on" if on else "off"
                    light["brightness"] = brightness_pct or (80 if on else 0)
                    return dict(light)
            return None

        service = "turn_on" if on else "turn_off"
        extra = {}
        if on and brightness_pct is not None:
            extra["brightness_pct"] = max(1, min(100, brightness_pct))
        if not self._call_service("light", service, entity_id, **extra):
            return None
        state = self._get_state(entity_id)
        return self._light_from_state(state) if state else None

    def connection_info(self) -> dict:
        """Diagnostics for settings / troubleshooting."""
        return {
            "configured": not self.is_mock,
            "url": self.base_url or None,
            "lights": self.light_entities,
            "sensor": self.sensor_entity or None,
        }
