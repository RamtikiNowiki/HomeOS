from flask import Response, jsonify, render_template, request
from flask_login import login_required

from ..integrations.http_client import HttpError
from . import creality_k2_bp
from .service import PREHEAT_PRESETS, CrealityK2Service


@creality_k2_bp.route("/")
@login_required
def panel():
    service = CrealityK2Service()
    return render_template(
        "creality_k2/panel.html",
        status=service.get_status(),
        is_mock=service.is_mock,
        connection=service.connection_info(),
        camera=service.get_camera_info(),
        preheat_presets=PREHEAT_PRESETS,
        print_history=service.get_print_history(),
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


@creality_k2_bp.route("/api/preheat", methods=["POST"])
@login_required
def preheat():
    body = request.get_json(silent=True) or {}
    preset_id = (body.get("preset") or "").strip().lower()
    wait = bool(body.get("wait"))

    preset = next((p for p in PREHEAT_PRESETS if p["id"] == preset_id), None)
    if preset:
        nozzle, bed = preset["nozzle"], preset["bed"]
    else:
        try:
            nozzle = float(body.get("nozzle", 0))
            bed = float(body.get("bed", 0))
        except (TypeError, ValueError):
            return jsonify({"error": "invalid temperature"}), 400

    return jsonify(CrealityK2Service().preheat(nozzle, bed, wait=wait))


@creality_k2_bp.route("/api/history")
@login_required
def history():
    limit = request.args.get("limit", 8, type=int)
    return jsonify({"jobs": CrealityK2Service().get_print_history(limit=limit)})


@creality_k2_bp.route("/api/webcam/snapshot")
@login_required
def webcam_snapshot():
    service = CrealityK2Service()
    try:
        data, content_type = service.fetch_webcam_snapshot()
    except HttpError as exc:
        return jsonify({"error": str(exc)}), 502
    if not data:
        return jsonify({"error": "camera not configured"}), 404
    return Response(data, mimetype=content_type)
