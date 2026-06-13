"""PWA routes — service worker and manifest served from site root (required scope)."""
from flask import send_from_directory


def register_pwa_routes(app):
    @app.route("/sw.js")
    def service_worker():
        resp = send_from_directory(app.static_folder, "sw.js", mimetype="application/javascript")
        resp.headers["Cache-Control"] = "no-cache"
        resp.headers["Service-Worker-Allowed"] = "/"
        return resp

    @app.route("/manifest.webmanifest")
    def web_manifest():
        resp = send_from_directory(app.static_folder, "manifest.webmanifest", mimetype="application/manifest+json")
        resp.headers["Cache-Control"] = "public, max-age=3600"
        return resp
