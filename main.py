import threading

import uvicorn

from backend.database import init_db
from backend.main import app, attack_queue
from config import API_HOST, API_PORT, HONEYPOT_HOST, HONEYPOT_PORT
from honeypot.ssh_server import start_honeypot


def main():
    init_db()

    honeypot_thread = threading.Thread(
        target=start_honeypot,
        args=(HONEYPOT_HOST, HONEYPOT_PORT, attack_queue),
        daemon=True,
    )
    honeypot_thread.start()

    print(f"[*] API server at http://{API_HOST}:{API_PORT}")
    print(f"[*] Dashboard:  http://{API_HOST}:{API_PORT}")

    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="warning")


if __name__ == "__main__":
    main()
