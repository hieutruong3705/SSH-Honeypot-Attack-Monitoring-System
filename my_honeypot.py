import socket
import paramiko
import json
import requests
import threading
from datetime import datetime

# ==========================================
# 1. CAU HINH TELEGRAM BOT
# ==========================================
TELEGRAM_TOKEN = '8229175529:AAHXfG-L88oTDMeWTkwNTWCumt9jXQ4MfjM'
TELEGRAM_CHAT_ID = '7180170830'

# Mo san "duong ong" giup gui tin nhan Telegram sieu toc do
telegram_session = requests.Session() 

# ==========================================
# 2. CAC HAM XU LY (GUI TIN & LUU LOG)
# ==========================================
def send_telegram_alert(ip, username, password, date_str, time_str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    message = (
        f"🚨 [BAO DONG] HONEYPOT DA SAP!\n\n"
        f"📅 Ngay: {date_str}\n"
        f"⏰ Gio: {time_str}\n"
        f"🌐 IP: {ip}\n"
        f"👤 Tai khoan: {username}\n"
        f"🔑 Mat khau: {password}"
    )
    try:
        telegram_session.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': message}, timeout=5)
    except Exception:
        pass

def save_log_to_file(ip, username, password, date_str, time_str):
    with open("hacker_logs.json", "a") as f:
        log_entry = {
            "Ngay": date_str,
            "ThoiGian": time_str,
            "IP": ip,
            "TaiKhoan": username,
            "MatKhau": password
        }
        f.write(json.dumps(log_entry) + "\n")

# ==========================================
# 3. KICH BAN GIA MAO SSH (HONEYPOT)
# ==========================================
class FakeSSHServer(paramiko.ServerInterface):
    def __init__(self, client_ip):
        self.client_ip = client_ip

    # Ham nay chay khi Hacker nhap mat khau
    def check_auth_password(self, username, password):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        timestamp = f"{date_str} {time_str}"
        
        # In canh bao do ruc ra man hinh Ubuntu
        print(f"\n[{timestamp}] [!] BAO DONG: Ke la mat dang pha khoa!")
        print(f"   => IP        : {self.client_ip}")
        print(f"   => Tai khoan : {username}")
        print(f"   => Mat khau  : {password}")
        
        # Ghi log ra file
        save_log_to_file(self.client_ip, username, password, date_str, time_str)
        
        # Thue mot "nhan vien" chay ngam gui tin nhan Tele ngay lap tuc
        threading.Thread(
            target=send_telegram_alert,
            args=(self.client_ip, username, password, date_str, time_str),
            daemon=True
        ).start()
        
        # Da hacker ra ngoai khong cho vao
        return paramiko.AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

# ==========================================
# 4. KHOI DONG HE THONG CHUNG
# ==========================================
def start_honeypot(host='0.0.0.0', port=2222):
    print(f"[*] Dang rai bay tai cong {port}... Cho con moi lot luoi!")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(100)

    # Tao chia khoa (Chung minh thu gia) truc tiep tren RAM
    host_key = paramiko.RSAKey.generate(2048)

    while True:
        client_socket, client_addr = server_socket.accept()
        client_ip = client_addr[0]
        
        transport = paramiko.Transport(client_socket)
        transport.add_server_key(host_key)
        
        server = FakeSSHServer(client_ip)
        try:
            transport.start_server(server=server)
        except paramiko.SSHException:
            pass

if __name__ == '__main__':
    start_honeypot()