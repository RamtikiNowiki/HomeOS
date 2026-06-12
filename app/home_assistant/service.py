"""Home Assistant integration service.

Currently returns mock state. When you're ready to wire up a real Home
Assistant instance, set HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN in the
environment and replace the mock branches with REST calls, e.g.:

    GET  {url}/api/states/<entity_id>
    POST {url}/api/services/light/toggle   {"entity_id": "..."}

with header  Authorization: Bearer {token}.
"""
from flask import current_app

# In-memory mock state (shared across requests within one worker — good
# enough for the mock phase, real state will live in Home Assistant).
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
    "temperature": 22.4,   # °C
    "humidity": 41,        # %
}


class HomeAssistantService:
    """Thin client around the Home Assistant REST API (mocked for now)."""

    def __init__(self):
        self.base_url = current_app.config.get("HOME_ASSISTANT_URL", "")
        self.token = current_app.config.get("HOME_ASSISTANT_TOKEN", "")

    @property
    def is_mock(self) -> bool:
        return not (self.base_url and self.token)

    def get_lights(self) -> list[dict]:
        if self.is_mock:
            return [dict(light) for light in _MOCK_LIGHTS]
        raise NotImplementedError("Real HA client not wired up yet")

    def get_sensor(self) -> dict:
        if self.is_mock:
            return dict(_MOCK_SENSOR)
        raise NotImplementedError("Real HA client not wired up yet")

    def toggle_light(self, entity_id: str) -> dict | None:
        if self.is_mock:
            for light in _MOCK_LIGHTS:
                if light["entity_id"] == entity_id:
                    light["state"] = "off" if light["state"] == "on" else "on"
                    light["brightness"] = 80 if light["state"] == "on" else 0
                    return dict(light)
            return None
        raise NotImplementedError("Real HA client not wired up yet")
