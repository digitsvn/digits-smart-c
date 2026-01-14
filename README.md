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
| 📡 **Auto WiFi Provisioning** | Tự động bật Hotspot + hiển thị QR code khi chưa có WiFi |
| 🖥️ **Full HD GUI** | Giao diện 1920x1080, hỗ trợ Wayland |
| 🔐 **Device Activation** | Kích hoạt thiết bị với server |
| ⚡ **Auto-Update** | Tự động cập nhật khi khởi động |
| 🎙️ **I2S INMP441 Mic** | Hỗ trợ microphone I2S MEMS (stereo dual mic) |
| 🎯 **Beamforming** | Delay-and-Sum beamforming khử nhiễu loa |
| 📺 **HDMI Audio** | Output audio qua HDMI hoặc 3.5mm jack |
| 🌐 **Web Dashboard** | Cấu hình từ xa qua `http://IP:8080` |
| 📱 **Network Overlay** | Hiển thị IP + QR code trên GUI để dễ dàng cấu hình |

---

## 🚀 Cài Đặt

### Yêu Cầu
- Raspberry Pi 4/5 với Pi OS Lite (64-bit)
- USB Microphone hoặc I2S INMP441 + Speaker
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
   KHÔNG CÓ        CÓ MẠNG SẴN
      ↓               ↓
 Bật Hotspot      Start App NGAY LẬP TỨC
"SmartC-Setup"    + Hiển thị IP Overlay
IP: 192.168.4.1   (Song song, không chặn app)
      ↓               ↓
Chờ User Config   Sau 10 giây
(App tạm dừng)        ↓
      ↓           Tự động ẩn Overlay
Kết nối Web UI        ↓
192.168.4.1:8080  Giao diện sạch
      ↓
Kết nối thành công
      ↓
Start App NGAY LẬP TỨC
+ Hiển thị IP Mới
(Song song)
      ↓
Sau 15 giây
      ↓
Tự động ẩn Overlay
```

### 📶 Network Overlay trên GUI

Khi app khởi động, góc trên phải màn hình sẽ hiển thị:

**Chế độ Hotspot (chưa có WiFi):**
```
╭─────────────────────────╮
│ 📶 WiFi: SmartC-Setup   │
│ 🔐 Pass: smartc123      │
│ 🌐 http://192.168.4.1:8080 │
│                         │
│    ┌─────────┐          │
│    │ QR Code │          │
│    └─────────┘          │
│ 📷 Quét để cấu hình     │
╰─────────────────────────╯
```

**Chế độ Connected (đã có WiFi):**
```
╭─────────────────────────╮
│ 📱 Settings:            │
│ http://192.168.1.50:8080│
│                         │
│    ┌─────────┐          │
│    │ QR Code │          │
│    └─────────┘          │
│ 📷 Quét để cấu hình     │
╰─────────────────────────╯
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
- **Web Config:** `http://192.168.4.1:8080`

### Web Dashboard
Khi đã kết nối WiFi, truy cập `http://IP:8080` để:
- Cấu hình WiFi
- Chọn Audio Input/Output
- Cấu hình Wake Word
- Xem trạng thái thiết bị
- Điều chỉnh Video Background

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

### 🎙️ I2S INMP441 Microphone

Hỗ trợ microphone I2S MEMS INMP441 với Delay-and-Sum Beamforming.

**Sơ đồ kết nối:**
```
┌─────────────────────────────────────┐
│  INMP441     →    Raspberry Pi     │
├─────────────────────────────────────┤
│  VDD         →    3.3V (Pin 1)     │
│  GND         →    GND  (Pin 6)     │
│  SD (Data)   →    GPIO 20 (Pin 38) │
│  WS (LRCLK)  →    GPIO 19 (Pin 35) │
│  SCK (BCLK)  →    GPIO 18 (Pin 12) │
│  L/R         →    GND (Left only)  │
└─────────────────────────────────────┘
```

**Dual mic (Stereo):** Mic 1: L/R→GND, Mic 2: L/R→3.3V

**Cấu hình trong Dashboard:**
1. Mở `http://IP:8080`
2. ✅ Sử dụng I2S Microphone
3. ✅ Stereo (nếu 2 mic)
4. ✅ Beamforming (khử nhiễu loa)

---

## 🔧 Scripts Tiện Ích

| Script | Mục Đích | Lệnh |
|--------|----------|------|
| `update.sh` | Cập nhật app | `bash update.sh` |
| `auto_update.sh` | Bật auto-update on boot | `bash auto_update.sh --install` |
| `scripts/fix_autostart.sh` | Sửa app không tự chạy | `bash scripts/fix_autostart.sh` |
| `scripts/fix_display.sh` | Sửa độ phân giải HDMI | `sudo bash scripts/fix_display.sh` |

---

## 🐛 Troubleshooting

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

### Lỗi Thường Gặp

| Lỗi | Nguyên nhân | Giải pháp |
|-----|-------------|-----------|
| Không thấy IP overlay | GUI chưa load xong | Đợi 5-10 giây sau khi boot |
| QR code không hiện | Thiếu thư viện qrcode | `pip install qrcode[pil]` |
| WebSocket không kết nối | Chưa có Internet | Kiểm tra WiFi đã kết nối |

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
├── assets/
│   ├── emojis/             # Emotion GIFs
│   ├── qr_settings.png     # QR code cho web dashboard
│   └── qr_hotspot.png      # QR code cho hotspot
├── models/                 # Wake word models
├── src/                    # Source code
│   ├── application.py      # Main app logic
│   ├── display/            # GUI components (QML)
│   ├── network/            # WiFi, Hotspot, Web Settings
│   └── plugins/            # Audio, UI, Wake Word plugins
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
