from flask import Blueprint

home_assistant_bp = Blueprint("home_assistant", __name__)

from . import routes  # noqa: E402,F401
