from flask import jsonify, render_template
from flask_login import login_required

from . import home_assistant_bp
from .service import HomeAssistantService


@home_assistant_bp.route("/")
@login_required
def panel():
    service = HomeAssistantService()
    return render_template(
        "home_assistant/panel.html",
        lights=service.get_lights(),
        sensor=service.get_sensor(),
        is_mock=service.is_mock,
    )


@home_assistant_bp.route("/api/lights/<path:entity_id>/toggle", methods=["POST"])
@login_required
def toggle_light(entity_id: str):
    service = HomeAssistantService()
    light = service.toggle_light(entity_id)
    if light is None:
        return jsonify({"error": "unknown entity"}), 404
    return jsonify(light)


@home_assistant_bp.route("/api/states")
@login_required
def states():
    service = HomeAssistantService()
    return jsonify({"lights": service.get_lights(), "sensor": service.get_sensor()})
