"""Integration service smoke tests."""
from app import create_app
from app.home_assistant.service import HomeAssistantService
from app.creality_k2.service import CrealityK2Service


def test_ha_mock_lights():
    app = create_app()
    with app.app_context():
        svc = HomeAssistantService()
        assert svc.is_mock
        lights = svc.get_lights()
        assert len(lights) >= 1
        assert "entity_id" in lights[0]


def test_ha_mock_toggle():
    app = create_app()
    with app.app_context():
        svc = HomeAssistantService()
        light = svc.toggle_light("light.living_room_leds")
        assert light is not None
        assert light["state"] in ("on", "off")


def test_k2_mock_status():
    app = create_app()
    with app.app_context():
        svc = CrealityK2Service()
        assert svc.is_mock
        status = svc.get_status()
        assert "progress" in status
        assert status["state"] in ("printing", "paused", "standby", "complete", "offline")


def test_k2_mock_pause_resume():
    app = create_app()
    with app.app_context():
        svc = CrealityK2Service()
        paused = svc.pause_print()
        assert paused["state"] == "paused"
        resumed = svc.resume_print()
        assert resumed["state"] == "printing"
