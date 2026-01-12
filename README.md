# 🤖 Smart C AI - Trợ lý AI cho Raspberry Pi

> Ứng dụng trợ lý AI thông minh với voice interaction, wake word detection và WiFi provisioning cho Raspberry Pi OS Lite.

[![GitHub](https://img.shields.io/badge/GitHub-digits--smart--c-blue)](https://github.com/digitsvn/digits-smart-c)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## ✨ Tính Năng

| Tính Năng | Mô Tả |
|-----------|-------|
| 🎤 **Voice Interaction** | Tương tác bằng giọng nói với AI |
| 🔊 **Wake Word Detection** | Luôn lắng nghe "Alexa", "Hey Lily", "Smart C" |
| 📡 **WiFi Provisioning** | Tự động bật Hotspot khi chưa có WiFi |
| 🖥️ **Full HD GUI** | Giao diện 1920x1080, hỗ trợ Wayland |
| 🔐 **Device Activation** | Kích hoạt thiết bị với server |
| ⚡ **Auto-Update** | Tự động cập nhật khi khởi động |

---

## 🚀 Cài Đặt

### Yêu Cầu
- Raspberry Pi 4/5 với Pi OS Lite (64-bit)
- USB Microphone + Speaker
- Kết nối Internet

### Cài Đặt Đầy Đủ (Với Desktop GUI)

```bash
# Cài Git
sudo apt update && sudo apt install git -y

# Clone và cài đặt
git clone https://github.com/digitsvn/digits-smart-c.git ~/.digits
cd ~/.digits && bash install_oslite.sh
```

### Cài Đặt Tối Giản (Không GUI - Nhẹ Hơn 80%)

```bash
git clone https://github.com/digitsvn/digits-smart-c.git ~/.digits
cd ~/.digits && bash install_minimal.sh
```

| Bản | RAM | GUI | Autostart |
|-----|-----|-----|-----------|
| **Full** | ~400MB | PyQt5 Desktop | Desktop Entry |
| **Minimal** | ~100MB | CLI only | systemd service |

---

## 🔄 Cập Nhật

### Update Thủ Công
```bash
cd ~/.digits && bash update.sh
```

### Bản Cũ (Chưa Có update.sh)
```bash
cd ~/.digits && git pull && chmod +x *.sh scripts/*.sh 2>/dev/null; echo "✅ Done!"
```

### Auto-Update Mỗi Khi Boot (Khuyến Nghị)
```bash
cd ~/.digits && bash auto_update.sh --install
```

---

## 📱 Luồng Hoạt Động

```
Boot Pi → Smart C AI khởi động
              ↓
        Kiểm tra WiFi
        /           \
   Không có        Có WiFi
      ↓               ↓
 Bật Hotspot      First Run?
"SmartC-Setup"    /        \
      ↓         Có         Không
Captive Portal   ↓           ↓
192.168.4.1   Settings   Activated?
      ↓                  /        \
 Cấu hình WiFi       Chưa        Rồi
                       ↓           ↓
                   Activation → Chat Bot
```

---

## 🎤 Wake Words

| Từ khóa | Trigger |
|---------|---------|
| `alexa` | @alexa |
| `hey lily` | @hey_lily |
| `smart c` | @smartc |
| `xiaozhi` | @xiaozhi |
| `sophia` | @sophia |

---

## ⚙️ Cấu Hình

### WiFi Hotspot (Khi Không Có Mạng)
- **SSID:** `SmartC-Setup`
- **Password:** `smartc123`
- **IP:** `192.168.4.1`

### Độ Phân Giải Cửa Sổ
Chỉnh trong `config/config.json`:

```json
{
  "WINDOW_SIZE_MODE": "fullhd"
}
```

| Mode | Kích thước |
|------|------------|
| `fullhd` | 1920x1080 (khuyến nghị) |
| `hd` | 1280x720 |
| `screen_100` | Toàn màn hình |

### Audio Devices
Cấu hình trong Settings hoặc `config/config.json`:

```json
{
  "AUDIO_DEVICES": {
    "input_device_name": "USB PnP Sound Device",
    "output_device_name": "bcm2835 Headphones"
  }
}
```

> ⚠️ File `config/config.json` chứa tokens - không commit vào Git!

---

## 🔧 Scripts Tiện Ích

| Script | Mục Đích | Lệnh |
|--------|----------|------|
| `update.sh` | Cập nhật app | `bash update.sh` |
| `auto_update.sh` | Bật auto-update on boot | `bash auto_update.sh --install` |
| `scripts/fix_autostart.sh` | Sửa app không tự chạy | `bash scripts/fix_autostart.sh` |
| `scripts/fix_display.sh` | Sửa độ phân giải HDMI | `sudo bash scripts/fix_display.sh` |

---

## � Troubleshooting

```bash
# Xem logs
tail -f ~/.digits/logs/smartc.log

# Kiểm tra audio & wifi
python3 ~/.digits/scripts/check_audio_wifi.py

# Chạy thủ công
~/.digits/run.sh

# Restart service (minimal mode)
sudo systemctl restart smartc

# Fix autostart
bash ~/.digits/scripts/fix_autostart.sh && sudo reboot

# Fix display Full HD
sudo bash ~/.digits/scripts/fix_display.sh && sudo reboot
```

---

## 📁 Cấu Trúc Thư Mục

```
~/.digits/
├── main.py                 # Entry point
├── run.sh                  # GUI launcher
├── run_cli.sh              # CLI launcher
├── update.sh               # Update script
├── auto_update.sh          # Auto-update installer
├── install_oslite.sh       # Full installer
├── install_minimal.sh      # Minimal installer
├── config/
│   ├── config.json         # Cấu hình (tự động tạo)
│   └── config.example.json # Template
├── models/                 # Wake word models
├── src/                    # Source code
├── scripts/                # Utility scripts
└── logs/                   # Log files
```

---

## 🌐 Server

| Service | URL |
|---------|-----|
| Website | https://xiaozhi-ai-iot.vn |
| WebSocket | wss://xiaozhi-ai-iot.vn/api/v1/ws |
| OTA | https://xiaozhi-ai-iot.vn/api/v1/ota |

---

## 📄 License

MIT License - [Xem chi tiết](LICENSE)

---

<p align="center">
  <b>Smart C AI</b> - <i>Trợ lý AI thông minh cho mọi nhà</i> 🏠
</p>
