from flask import Blueprint

creality_k2_bp = Blueprint("creality_k2", __name__)

from . import routes  # noqa: E402,F401
