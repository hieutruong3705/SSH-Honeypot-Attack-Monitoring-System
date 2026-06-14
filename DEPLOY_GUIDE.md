# Hướng Dẫn Triển Khai Honeypot Lên VPS (Production)

Tài liệu này hướng dẫn chi tiết cách đưa dự án Honeypot của bạn lên một máy chủ ảo (VPS) chạy hệ điều hành Linux (Ubuntu/Debian) và treo 24/7 bằng Docker. 

> [!NOTE]
> Bạn hoàn toàn có thể sao chép nguyên văn phần này vào Báo cáo Đồ án phần "Triển khai thực tế" để gây ấn tượng với giảng viên!

## 1. Chuẩn bị VPS
- Cần một máy chủ ảo (VPS) cài sẵn **Ubuntu 20.04** hoặc **Ubuntu 22.04**.
- Cấu hình tối thiểu: 1 CPU, 1GB RAM (Khuyên dùng: 2GB RAM để Docker Build mượt mà).
- Hệ thống đã được cấp phát một địa chỉ IP Public.

## 2. Cài đặt Docker và Docker Compose trên VPS
Truy cập vào VPS thông qua SSH (VD: `ssh root@dia_chi_ip_vps`). Chạy các lệnh sau để cài đặt Docker:

```bash
# Cập nhật hệ thống
sudo apt update && sudo apt upgrade -y

# Cài đặt Docker
sudo apt install docker.io docker-compose -y

# Bật Docker khởi động cùng hệ thống
sudo systemctl enable docker
sudo systemctl start docker
```

## 3. Tải mã nguồn lên VPS
Bạn có thể đẩy code từ máy tính lên Github, sau đó `git clone` về VPS. Hoặc dùng phần mềm WinSCP/FileZilla để copy toàn bộ thư mục `bmudht` lên VPS.

> [!IMPORTANT]
> Cấu trúc thư mục trên VPS bắt buộc phải giống như trên máy tính của bạn, bao gồm các file `Dockerfile` và `docker-compose.yml` nằm ở ngoài cùng.

Ví dụ đường dẫn thư mục trên VPS: `/root/bmudht/`

## 4. Khởi chạy hệ thống Honeypot (Chỉ với 1 lệnh)
Di chuyển vào thư mục dự án và gõ lệnh chạy nền:

```bash
cd /root/bmudht
sudo docker-compose up -d --build
```

Lệnh này sẽ tự động:
1. Đọc file `Dockerfile` để cài đặt NodeJS và gói giao diện Frontend.
2. Cài đặt Python 3.10 và các thư viện cần thiết.
3. Chạy `python main.py` ở chế độ ngầm (background).
4. Tính năng `restart: always` sẽ tự động khởi động lại Honeypot nếu máy chủ VPS bị tắt đột ngột và mở lại.

## 5. Truy cập hệ thống

Sau khi Docker chạy xong, hệ thống của bạn đã chính thức được "Public" ra ngoài Internet:

- **Bảng điều khiển (Dashboard):** Truy cập `http://<IP_CỦA_VPS>:8000` trên trình duyệt để xem.
- **Mồi nhử Hacker (Honeypot):** Bất cứ ai trên mạng Internet giờ đây đều có thể sập bẫy nếu gõ:
  ```bash
  ssh root@<IP_CỦA_VPS> -p 2222
  ```

> [!CAUTION]
> **Khuyến nghị Bảo mật:** Mặc định cổng 8000 (Dashboard) đang mở công khai. Bất kỳ ai biết IP VPS của bạn đều có thể truy cập vào xem thống kê. Trong môi trường thực tế, quản trị viên thường sử dụng VPN (như Tailscale/WireGuard) để chỉ cho phép truy cập cổng 8000 từ mạng nội bộ ảo, còn cổng 2222 thì vẫn mở công khai ra toàn cầu.
