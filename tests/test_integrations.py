"""Integration service smoke tests."""
from app import create_app
from app.home_assistant.service import HomeAssistantService
from app.creality_k2.service import CrealityK2Service, build_status_from_moonraker


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


def test_k2_mock_preheat_and_history():
    app = create_app()
    with app.app_context():
        svc = CrealityK2Service()
        heated = svc.preheat(210, 60)
        assert heated["nozzle_target"] == 210
        history = svc.get_print_history()
        assert len(history) >= 1
        assert "filename" in history[0]


def test_k2_creality_motion_inference():
    """Creality Print jobs often leave print_stats on standby while motion is active."""
    payload = {
        "print_stats": {"state": "standby", "filename": "", "print_duration": 0, "info": {}},
        "display_status": {"progress": 0.0},
        "virtual_sdcard": {"is_active": False, "progress": 0.0, "layer": 0, "layer_count": 0},
        "extruder": {"temperature": 220.0, "target": 220.0},
        "heater_bed": {"temperature": 50.0, "target": 50.0},
        "gcode_move": {"speed_factor": 1.0},
        "motion_report": {
            "live_velocity": 26.0,
            "live_extruder_velocity": 1.2,
            "trapq": ["extruder", "toolhead"],
        },
        "output_pin fan1": {"value": 0.8},
    }
    status = build_status_from_moonraker(payload, host="192.168.1.239")
    assert status["state"] == "printing"
    assert status["progress_unknown"] is True
    assert status["nozzle_temp"] == 220.0
    assert status["fan_speed_pct"] == 80


def test_k2_cur_print_data_progress():
    """Creality Print stores live job stats in virtual_sdcard.cur_print_data."""
    payload = {
        "print_stats": {"state": "standby", "filename": "", "print_duration": 0, "info": {}},
        "display_status": {},
        "virtual_sdcard": {
            "is_active": False,
            "layer": 42,
            "layer_count": 0,
            "cur_print_data": {
                "status": "printing",
                "filename": "part.stl_PLA_10m.gcode",
                "print_duration": 300,
                "metadata": {"layer_count": 120, "estimated_time": 600},
            },
        },
        "extruder": {"temperature": 215.0, "target": 215.0},
        "heater_bed": {"temperature": 60.0, "target": 60.0},
        "gcode_move": {},
        "motion_report": {},
    }
    status = build_status_from_moonraker(payload)
    assert status["state"] == "printing"
    assert status["progress"] == 50
    assert status["layer_current"] == 42
    assert status["layer_total"] == 120
    assert "part.stl" in status["print_name"]


def test_k2_moonraker_progress_from_sdcard():
    payload = {
        "print_stats": {"state": "printing", "filename": "part.gcode", "print_duration": 120},
        "display_status": {},
        "virtual_sdcard": {
            "is_active": True,
            "file_position": 50000,
            "file_size": 100000,
            "layer": 12,
            "layer_count": 240,
        },
        "extruder": {"temperature": 215.0, "target": 215.0},
        "heater_bed": {"temperature": 60.0, "target": 60.0},
        "gcode_move": {},
        "motion_report": {},
    }
    status = build_status_from_moonraker(payload)
    assert status["progress"] == 50
    assert status["layer_current"] == 12
    assert status["layer_total"] == 240
