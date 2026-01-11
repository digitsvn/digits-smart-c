# 🤖 Smart C AI - Trợ lý AI cho Raspberry Pi

> Ứng dụng trợ lý AI thông minh với voice interaction, wake word detection và WiFi provisioning cho Raspberry Pi OS Lite.

## ✨ Tính Năng

- 🎤 **Voice Interaction** - Tương tác bằng giọng nói với AI
- 🔊 **Wake Word Detection** - Luôn lắng nghe từ khóa "Alexa", "Hey Lily", "Smart C"
- 📡 **WiFi Provisioning** - Tự động bật Hotspot để cấu hình WiFi khi chưa có kết nối
- 🖥️ **PyQt5 GUI** - Giao diện đồ họa hiện đại, hỗ trợ Wayland
- 🔐 **Device Activation** - Kích hoạt thiết bị với server
- 🎵 **Audio Config** - Cấu hình MIC và Speaker dễ dàng

## 🚀 Cài Đặt Trên Raspberry Pi OS Lite

### Yêu Cầu
- Raspberry Pi 4/5 với Pi OS Lite (64-bit recommended)
- USB Microphone
- Speaker (3.5mm jack hoặc HDMI)
- Kết nối Internet (Ethernet hoặc WiFi)

### Cài Đặt Nhanh

```bash
# Cài đặt Git (Ubuntu / Debian / Pi OS Lite)
sudo apt update
sudo apt install git -y

# Clone repository
git clone https://github.com/nguyenduchoai/py-xiaozhi-pi.git ~/.digits

# Chạy installer
cd ~/.digits
bash install_oslite.sh
```

### Installer Sẽ Tự Động:
1. Cài đặt Desktop Environment (labwc Wayland)
2. Cài đặt PyQt5 và các thư viện GUI
3. Cài đặt Audio (PulseAudio, ALSA)
4. Cài đặt NetworkManager cho WiFi
5. Cấu hình Desktop Autologin
6. Thiết lập Autostart cho app

---

### 🚀 Cài Đặt Tối Giản (Khuyến Nghị cho Pi OS Lite)

**Dành cho ai muốn chạy nhẹ nhất - KHÔNG cần Desktop GUI:**

```bash
# Clone repository
git clone https://github.com/nguyenduchoai/py-xiaozhi-pi.git ~/.digits

# Chạy minimal installer
cd ~/.digits
bash install_minimal.sh
```

**Ưu điểm của bản Minimal:**
- ⚡ **Nhẹ hơn 80%** - Không cài Desktop, PyQt5, PulseAudio
- 🔧 **systemd service** - Tự động chạy khi boot, tự restart nếu crash
- 💾 **RAM ~100MB** thay vì ~400MB với GUI
- 🎯 **Tập trung AI Chatbot** - Chỉ cài những gì cần thiết

**Quản lý service:**
```bash
# Khởi động
sudo systemctl start smartc

# Xem trạng thái
sudo systemctl status smartc

# Xem logs
tail -f ~/.digits/logs/smartc.log

# Dừng
sudo systemctl stop smartc
```

## 📱 Luồng Hoạt Động

```
Boot Pi → Desktop GUI → Smart C AI khởi động
                              ↓
                     Kiểm tra WiFi
                    /            \
              Không có          Có WiFi
                 ↓                 ↓
         Bật Hotspot         First Run?
        "SmartC-Setup"      /        \
              ↓           Có         Không
      Captive Portal       ↓           ↓
     192.168.4.1     Settings ──→ Activated?
              ↓                  /        \
         Cấu hình WiFi       Chưa        Rồi
                               ↓           ↓
                          Activation → Chat Bot GUI
```

### Chi tiết:
1. **Boot** → Desktop (labwc Wayland) tự động khởi động
2. **Smart C AI** tự động chạy
3. **Không có WiFi** → Bật Hotspot `SmartC-Setup` (pass: `smartc123`)
4. **Captive Portal** → User kết nối và cấu hình WiFi tại http://192.168.4.1
5. **First-run** → Mở Settings cấu hình MIC/Speaker
6. **Activation** → Xác thực với Server (QR Code + OTP)
7. **Chat Bot** → Sẵn sàng tương tác, nói "Alexa" hoặc "Hey Lily"

## 🎤 Wake Words

Ứng dụng sử dụng [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) để phát hiện từ khóa:

| Từ khóa | Trigger |
|---------|---------|
| `xiaozhi` | @xiaozhi |
| `lily` | @lily |
| `alexa` | @alexa |
| `hey lily` | @hey_lily |
| `smart c` | @smartc |
| `sophia` | @sophia |

## 📁 Cấu Trúc Thư Mục

```
~/.digits/
├── main.py                 # Entry point
├── run.sh                  # Launcher script
├── install_oslite.sh       # OS Lite installer
├── config/
│   ├── config.json         # Cấu hình app (tự động tạo)
│   └── config.example.json # Template cấu hình
├── models/
│   ├── encoder.onnx        # Wake word model
│   ├── decoder.onnx
│   ├── joiner.onnx
│   └── keywords.txt        # Danh sách wake words
├── src/
│   ├── core/
│   │   └── startup_flow.py # Quản lý luồng khởi động
│   ├── network/
│   │   ├── wifi_manager.py # Quản lý WiFi/Hotspot
│   │   └── wifi_captive_portal.py
│   ├── views/
│   │   ├── settings/       # Settings UI
│   │   └── activation/     # Activation UI
│   └── ...
└── logs/
    └── smartc.log          # Log files
```

## ⚙️ Cấu Hình

### WiFi Hotspot
- **SSID:** `SmartC-Setup`
- **Password:** `smartc123`
- **IP:** `192.168.4.1`

### Audio Devices
Lần đầu chạy, hệ thống tự động tạo `config/config.json` từ template.

Cấu hình trong Settings hoặc chỉnh `config/config.json`:
```json
{
  "AUDIO_DEVICES": {
    "input_device_id": 2,
    "input_device_name": "USB PnP Sound Device",
    "output_device_id": 1,
    "output_device_name": "bcm2835 Headphones",
    "input_sample_rate": 44100,
    "output_sample_rate": 44100
  }
}
```

> ⚠️ **Lưu ý:** File `config/config.json` chứa tokens xác thực và không được commit vào Git.  
> Sử dụng `config/config.example.json` làm template.

### Window Size (Độ phân giải)
Cấu hình trong `config/config.json`:
```json
{
  "WINDOW_SIZE_MODE": "fullhd"
}
```

**Các chế độ hỗ trợ:**

| Mode | Kích thước | Mô tả |
|------|------------|-------|
| `fullhd` | 1920x1080 | Full HD (khuyến nghị) |
| `hd` | 1280x720 | HD |
| `screen_75` | 75% màn hình | 75% kích thước màn hình |
| `screen_100` | 100% | Toàn màn hình |
| `vertical_916` | 9:16 | Tỷ lệ dọc (cho video dọc) |
| `default` | Auto | Tự động: Full HD nếu màn hình đủ lớn |

## 🔧 Troubleshooting

### Kiểm tra Audio & WiFi
```bash
python3 ~/.digits/scripts/check_audio_wifi.py
```

### Kiểm tra nhanh
```bash
python3 ~/.digits/scripts/quick_test.py
```

### Xem Logs
```bash
tail -f ~/.digits/logs/smartc.log
```

### Chạy thủ công
```bash
~/.digits/run.sh
```

### Fix Autostart (nếu app không tự chạy khi boot)
```bash
bash ~/.digits/scripts/fix_autostart.sh
sudo reboot
```

## 🌐 Server

- **Website:** https://xiaozhi-ai-iot.vn
- **WebSocket:** wss://xiaozhi-ai-iot.vn/api/v1/ws
- **OTA:** https://xiaozhi-ai-iot.vn/api/v1/ota

## 📄 License

MIT License

---

**Smart C AI** - *Trợ lý AI thông minh cho mọi nhà* 🏠
