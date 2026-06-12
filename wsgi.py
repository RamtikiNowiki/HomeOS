"""WSGI entrypoint — used by gunicorn in production and `flask run` locally."""
import socket
from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402

app = create_app()


def _lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


if __name__ == "__main__":
    port = 5000
    lan = _lan_ip()
    print(f"\n  Local:   http://127.0.0.1:{port}")
    print(f"  Phone:   http://{lan}:{port}  (same Wi‑Fi network)\n")
    app.run(host="0.0.0.0", port=port, debug=True)
