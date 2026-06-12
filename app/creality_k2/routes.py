from flask import jsonify, render_template
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
    )


@creality_k2_bp.route("/api/status")
@login_required
def status():
    return jsonify(CrealityK2Service().get_status())
