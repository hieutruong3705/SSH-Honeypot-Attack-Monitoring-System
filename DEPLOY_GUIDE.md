# HÆ°á»›ng Dáº«n Triá»ƒn Khai Honeypot LÃªn VPS (Production)

TÃ i liá»‡u nÃ y hÆ°á»›ng dáº«n chi tiáº¿t cÃ¡ch Ä‘Æ°a dá»± Ã¡n Honeypot cá»§a báº¡n lÃªn má»™t mÃ¡y chá»§ áº£o (VPS) cháº¡y há»‡ Ä‘iá»u hÃ nh Linux (Ubuntu/Debian) vÃ  treo 24/7 báº±ng Docker.

> [!NOTE]
> Báº¡n hoÃ n toÃ n cÃ³ thá»ƒ sao chÃ©p nguyÃªn vÄƒn pháº§n nÃ y vÃ o BÃ¡o cÃ¡o Äá»“ Ã¡n pháº§n "Triá»ƒn khai thá»±c táº¿" Ä‘á»ƒ gÃ¢y áº¥n tÆ°á»£ng vá»›i giáº£ng viÃªn!

## 1. Chuáº©n bá»‹ VPS
- Cáº§n má»™t mÃ¡y chá»§ áº£o (VPS) cÃ i sáºµn **Ubuntu 20.04** hoáº·c **Ubuntu 22.04**.
- Cáº¥u hÃ¬nh tá»‘i thiá»ƒu: 1 CPU, 1GB RAM (KhuyÃªn dÃ¹ng: 2GB RAM Ä‘á»ƒ Docker Build mÆ°á»£t mÃ ).
- Há»‡ thá»‘ng Ä‘Ã£ Ä‘Æ°á»£c cáº¥p phÃ¡t má»™t Ä‘á»‹a chá»‰ IP Public.

## 2. CÃ i Ä‘áº·t Docker vÃ  Docker Compose trÃªn VPS
Truy cáº­p vÃ o VPS thÃ´ng qua SSH (VD: `ssh root@dia_chi_ip_vps`). Cháº¡y cÃ¡c lá»‡nh sau Ä‘á»ƒ cÃ i Ä‘áº·t Docker:

```bash
# Cáº­p nháº­t há»‡ thá»‘ng
sudo apt update && sudo apt upgrade -y

# CÃ i Ä‘áº·t Docker
sudo apt install docker.io docker-compose -y

# Báº­t Docker khá»Ÿi Ä‘á»™ng cÃ¹ng há»‡ thá»‘ng
sudo systemctl enable docker
sudo systemctl start docker
```

## 3. Táº£i mÃ£ nguá»“n lÃªn VPS
Báº¡n cÃ³ thá»ƒ Ä‘áº©y code tá»« mÃ¡y tÃ­nh lÃªn Github, sau Ä‘Ã³ `git clone` vá» VPS. Hoáº·c dÃ¹ng pháº§n má»m WinSCP/FileZilla Ä‘á»ƒ copy toÃ n bá»™ thÆ° má»¥c `bmudht` lÃªn VPS.

> [!IMPORTANT]
> Cáº¥u trÃºc thÆ° má»¥c trÃªn VPS báº¯t buá»™c pháº£i giá»‘ng nhÆ° trÃªn mÃ¡y tÃ­nh cá»§a báº¡n, bao gá»“m cÃ¡c file `Dockerfile` vÃ  `docker-compose.yml` náº±m á»Ÿ ngoÃ i cÃ¹ng.

VÃ­ dá»¥ Ä‘Æ°á»ng dáº«n thÆ° má»¥c trÃªn VPS: `/root/bmudht/`

## 4. Khá»Ÿi cháº¡y há»‡ thá»‘ng Honeypot (Chá»‰ vá»›i 1 lá»‡nh)
Di chuyá»ƒn vÃ o thÆ° má»¥c dá»± Ã¡n vÃ  gÃµ lá»‡nh cháº¡y ná»n:

```bash
cd /root/bmudht
sudo docker-compose up -d --build
```

Lá»‡nh nÃ y sáº½ tá»± Ä‘á»™ng:
1. Äá»c file `Dockerfile` Ä‘á»ƒ cÃ i Ä‘áº·t NodeJS vÃ  gÃ³i giao diá»‡n Frontend.
2. CÃ i Ä‘áº·t Python 3.10 vÃ  cÃ¡c thÆ° viá»‡n cáº§n thiáº¿t.
3. Cháº¡y `python main.py` á»Ÿ cháº¿ Ä‘á»™ ngáº§m (background).
4. TÃ­nh nÄƒng `restart: always` sáº½ tá»± Ä‘á»™ng khá»Ÿi Ä‘á»™ng láº¡i Honeypot náº¿u mÃ¡y chá»§ VPS bá»‹ táº¯t Ä‘á»™t ngá»™t vÃ  má»Ÿ láº¡i.

## 5. Truy cáº­p há»‡ thá»‘ng

Sau khi Docker cháº¡y xong, há»‡ thá»‘ng cá»§a báº¡n Ä‘Ã£ chÃ­nh thá»©c Ä‘Æ°á»£c "Public" ra ngoÃ i Internet:

- **Báº£ng Ä‘iá»u khiá»ƒn (Dashboard):** Truy cáº­p `http://<IP_Cá»¦A_VPS>:8000` trÃªn trÃ¬nh duyá»‡t Ä‘á»ƒ xem.
- **Má»“i nhá»­ Hacker (Honeypot):** Báº¥t cá»© ai trÃªn máº¡ng Internet giá» Ä‘Ã¢y Ä‘á»u cÃ³ thá»ƒ sáº­p báº«y náº¿u gÃµ:
  ```bash
  ssh root@<IP_Cá»¦A_VPS> -p 2222
  ```

> [!CAUTION]
> **Khuyáº¿n nghá»‹ Báº£o máº­t:** Máº·c Ä‘á»‹nh cá»•ng 8000 (Dashboard) Ä‘ang má»Ÿ cÃ´ng khai. Báº¥t ká»³ ai biáº¿t IP VPS cá»§a báº¡n Ä‘á»u cÃ³ thá»ƒ truy cáº­p vÃ o xem thá»‘ng kÃª. Trong mÃ´i trÆ°á»ng thá»±c táº¿, quáº£n trá»‹ viÃªn thÆ°á»ng sá»­ dá»¥ng VPN (nhÆ° Tailscale/WireGuard) Ä‘á»ƒ chá»‰ cho phÃ©p truy cáº­p cá»•ng 8000 tá»« máº¡ng ná»™i bá»™ áº£o, cÃ²n cá»•ng 2222 thÃ¬ váº«n má»Ÿ cÃ´ng khai ra toÃ n cáº§u.
