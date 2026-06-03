import threading
import uvicorn
from fastapi.staticfiles import StaticFiles # [MỚI] Thư viện để load file HTML/CSS

from backend.database import init_db
from backend.main import app, attack_queue
from honeypot.ssh_server import start_honeypot
from config import HONEYPOT_HOST, HONEYPOT_PORT, API_HOST, API_PORT

# ==========================================
# GẮN GIAO DIỆN FRONTEND VÀO MẶT TIỀN API
# ==========================================
# Lệnh này sẽ lấy toàn bộ file trong thư mục 'frontend' (index.html, style.css...) 
# và đẩy thẳng ra cổng 8000
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

def main():
    init_db()

    honeypot_thread = threading.Thread(
        target=start_honeypot,
        args=(HONEYPOT_HOST, HONEYPOT_PORT, attack_queue),
        daemon=True,
    )
    honeypot_thread.start()

    print(f'[*] API server at http://{API_HOST}:{API_PORT}')
    # Đã sửa lại dòng in ra màn hình cho đúng IP thay vì localhost
    print(f'[*] Dashboard:  http://{API_HOST}:{API_PORT}') 
    
    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level='warning')

if __name__ == '__main__':
    main()
