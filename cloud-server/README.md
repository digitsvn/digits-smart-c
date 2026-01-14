# Smart C AI - Cloud Management Server

Hệ thống quản lý từ xa cho thiết bị Smart C AI.

## 🚀 Deploy lên Server

### 1. Cài đặt

```bash
cd cloud-server
npm install
```

### 2. Cấu hình

```bash
cp .env.example .env
# Sửa file .env nếu cần
```

### 3. Chạy

```bash
# Development
npm run dev

# Production
npm start
```

### 4. Reverse Proxy (Nginx)

Thêm vào nginx config:

```nginx
server {
    listen 443 ssl;
    server_name smartc.0nline.vn;
    
    # SSL certificates
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 5. PM2 (Production)

```bash
npm install -g pm2
pm2 start index.js --name smartc-cloud
pm2 save
pm2 startup
```

---

## 📱 Cấu hình trên thiết bị Pi

Thêm vào `~/.digits/config/config.json`:

```json
{
  "CLOUD": {
    "SERVER_URL": "wss://smartc.0nline.vn/ws/device",
    "DEVICE_NAME": "SmartC-Phòng Khách"
  }
}
```

Restart app để áp dụng:

```bash
sudo systemctl restart smartc
```

---

## 🔌 API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/devices` | Danh sách thiết bị |
| GET | `/api/devices/:id` | Chi tiết thiết bị |
| GET | `/api/devices/:id/screenshot` | Lấy screenshot |
| POST | `/api/devices/:id/screenshot/request` | Yêu cầu chụp screenshot |
| POST | `/api/devices/:id/command` | Gửi lệnh (restart, reboot, update) |
| POST | `/api/devices/:id/config` | Cập nhật config |
| GET | `/health` | Server health check |

---

## 🖥️ Dashboard

Truy cập `https://smartc.0nline.vn` để vào Dashboard:

- Xem danh sách thiết bị online/offline
- Xem live screenshot
- Điều khiển từ xa (restart, reboot)
- Xem thông số hệ thống (CPU, RAM, nhiệt độ)

---

## 📦 Cài đặt Screenshot trên Pi

Để tính năng screenshot hoạt động, cài đặt một trong các tools sau trên Pi:

```bash
# Option 1: scrot (recommended)
sudo apt install scrot

# Option 2: raspi2png (Raspberry Pi specific)
sudo apt install raspi2png

# Option 3: fbgrab (framebuffer)
sudo apt install fbgrab
```
