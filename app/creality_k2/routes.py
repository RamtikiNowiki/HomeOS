from flask import jsonify, render_template, request
from flask_login import login_required

from . import creality_k2_bp
from .service import CrealityK2Service


@creality_k2_bp.route("/")
@login_required
def panel():
    service = CrealityK2Service()
    return render_template(
        "creality_k2/panel.html",
        status=service.get_status(),
        is_mock=service.is_mock,
        connection=service.connection_info(),
    )


@creality_k2_bp.route("/api/status")
@login_required
def status():
    return jsonify(CrealityK2Service().get_status())


@creality_k2_bp.route("/api/pause", methods=["POST"])
@login_required
def pause():
    return jsonify(CrealityK2Service().pause_print())


@creality_k2_bp.route("/api/resume", methods=["POST"])
@login_required
def resume():
    return jsonify(CrealityK2Service().resume_print())


@creality_k2_bp.route("/api/cancel", methods=["POST"])
@login_required
def cancel():
    if request.args.get("confirm") != "1":
        return jsonify({"error": "confirmation required"}), 400
    return jsonify(CrealityK2Service().cancel_print())
