# WiFi Provisioning Guide - Raspberry Pi OS Lite

## Tổng quan

Tài liệu này mô tả cách triển khai tính năng WiFi Provisioning cho ứng dụng Smart C trên Raspberry Pi OS Lite.

## Luồng khởi động (Startup Flow)

```
┌─────────────────────────────────────────────────────────────┐
│                    KHỞI ĐỘNG ỨNG DỤNG                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Bước 0: KIỂM TRA WIFI                          │
│                                                             │
│  ┌──────────────┐     ┌──────────────────────────────────┐  │
│  │ Có WiFi?     │─NO──│ Bật Hotspot "SmartC-Setup"       │  │
│  └──────┬───────┘     │ Chạy Captive Portal (port 80)    │  │
│         │YES          │ Chờ user cấu hình WiFi           │  │
│         │             └──────────────────────────────────┘  │
│         ▼                                                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Bước 1: FIRST-RUN SETTINGS                     │
│                                                             │
│  ┌──────────────┐     ┌──────────────────────────────────┐  │
│  │ First run?   │─YES─│ Mở Settings Window               │  │
│  └──────┬───────┘     │ - Tab WiFi (kết nối mạng)        │  │
│         │NO           │ - Tab Âm thanh (MIC/LOA)         │  │
│         │             │ - Tab Wakeword (từ đánh thức)    │  │
│         ▼             └──────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Bước 2: ACTIVATION                             │
│                                                             │
│  ┌──────────────┐     ┌──────────────────────────────────┐  │
│  │ Đã kích hoạt?│─NO──│ Hiển thị màn hình Activation     │  │
│  └──────┬───────┘     │ User lấy code và đăng ký server  │  │
│         │YES          └──────────────────────────────────┘  │
│         ▼                                                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Bước 3: CHAT INTERFACE                         │
│                                                             │
│  - Wake Word luôn lắng nghe                                 │
│  - Từ đánh thức: "alexa", "hey lily", "smart c", "sophia"   │
│  - Phản hồi qua MIC và LOA                                  │
└─────────────────────────────────────────────────────────────┘
```

## Cài đặt

### 1. Cài đặt dependencies

```bash
# Chạy script cài đặt
sudo bash install_pi.sh
```

### 2. Cấu hình thủ công (nếu cần)

#### NetworkManager (cho WiFi Hotspot)

```bash
# Kiểm tra NetworkManager đang chạy
sudo systemctl status NetworkManager

# Bật nếu chưa chạy
sudo systemctl enable NetworkManager
sudo systemctl start NetworkManager
```

#### Audio

```bash
# Kiểm tra thiết bị audio
aplay -l  # Thiết bị phát
arecord -l  # Thiết bị thu

# Test phát âm thanh
speaker-test -t wav -c 2

# Thiết lập âm lượng
amixer set Master 80% unmute
amixer set Capture 80% cap
```

## Sử dụng

### Khi chưa có WiFi

1. Raspberry Pi sẽ tự động bật WiFi Hotspot có tên **"SmartC-Setup"**
2. Mật khẩu mặc định: **smartc123**
3. Kết nối điện thoại/laptop tới WiFi này
4. Mở trình duyệt, tự động chuyển tới trang cấu hình (hoặc vào http://192.168.4.1)
5. Chọn WiFi nhà và nhập mật khẩu
6. Nhấn "Kết nối"
7. Thiết bị sẽ kết nối WiFi và khởi động lại

### First-run Settings

Khi chạy lần đầu tiên, ứng dụng sẽ mở cửa sổ Settings với các tab:

1. **📶 WiFi** - Kiểm tra/thay đổi kết nối WiFi
2. **🔊 Âm thanh** - Chọn thiết bị MIC và LOA
3. **⚙️ Tùy chọn** - Các cài đặt hệ thống
4. **🎤 Wakeword** - Cấu hình từ đánh thức
5. **📷 Camera** - Cấu hình camera (nếu có)
6. **⌨️ Phím tắt** - Cài đặt phím tắt

### Wake Words

Các từ đánh thức mặc định:
- "alexa"
- "lily" 
- "hey lily"
- "smart c"
- "sophia"
- "xiaozhi"

## Kiểm tra và gỡ lỗi

### Script kiểm tra hệ thống

```bash
python3 scripts/check_audio_wifi.py
```

Script này kiểm tra:
- Kết nối WiFi
- Thiết bị audio (MIC/LOA)
- Cấu hình Wake Word
- Có thể test phát và thu âm thanh

### Kiểm tra logs

```bash
# Xem log ứng dụng
tail -f logs/xiaozhi.log

# Xem log systemd (nếu chạy như service)
journalctl -u smartc -f
```

### Các vấn đề thường gặp

#### 1. Không có âm thanh

```bash
# Kiểm tra thiết bị
aplay -l
pactl list sinks

# Kiểm tra âm lượng
amixer get Master
amixer set Master 80% unmute
```

#### 2. MIC không hoạt động

```bash
# Kiểm tra thiết bị thu
arecord -l
pactl list sources

# Test thu âm
arecord -d 3 -f cd test.wav
aplay test.wav
```

#### 3. WiFi Hotspot không bật

```bash
# Kiểm tra NetworkManager
sudo systemctl status NetworkManager

# Bật hotspot thủ công
sudo nmcli device wifi hotspot ifname wlan0 ssid SmartC-Setup password smartc123
```

#### 4. Wake Word không hoạt động

```bash
# Kiểm tra file model
ls -la ~/.digits/models/

# Kiểm tra keywords.txt
cat ~/.digits/models/keywords.txt

# Kiểm tra cấu hình
cat ~/.digits/config/config.json | grep -A 10 "WAKE_WORD"
```

## Cấu trúc file

```
~/.digits/
├── main.py                     # Entry point
├── install_pi.sh               # Script cài đặt
├── run.sh                      # Script khởi động
├── config/
│   └── config.json             # Cấu hình chính
├── models/
│   ├── encoder.onnx            # Model KWS
│   ├── decoder.onnx
│   ├── joiner.onnx
│   ├── tokens.txt
│   └── keywords.txt            # Danh sách từ đánh thức
├── scripts/
│   └── check_audio_wifi.py     # Script kiểm tra
└── src/
    ├── core/
    │   └── startup_flow.py     # Quản lý luồng khởi động
    ├── network/
    │   ├── wifi_manager.py     # Quản lý WiFi
    │   └── wifi_captive_portal.py  # Captive portal server
    └── views/
        └── settings/
            └── components/
                └── wifi/       # WiFi setup UI
```

## API

### WiFiManager

```python
from src.network.wifi_manager import get_wifi_manager

wifi = get_wifi_manager()

# Kiểm tra kết nối
if wifi.check_wifi_connection():
    print(f"Đã kết nối: {wifi.get_current_ssid()}")

# Quét mạng WiFi
networks = wifi.scan_wifi_networks()
for net in networks:
    print(f"{net.ssid} ({net.signal_strength}%)")

# Kết nối WiFi
success = wifi.connect_to_wifi("MyWiFi", "password123")

# Bật hotspot
wifi.start_hotspot("SmartC-Setup", "smartc123")

# Tắt hotspot
wifi.stop_hotspot()
```

### Captive Portal

```python
from src.network.wifi_captive_portal import run_wifi_setup

# Chạy WiFi setup (blocking)
success = await run_wifi_setup()
```

## License

MIT License - Smart C AI Assistant
