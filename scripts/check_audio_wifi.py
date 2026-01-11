#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script kiểm tra và gỡ lỗi Audio/WiFi cho Raspberry Pi.

Chạy: python scripts/check_audio_wifi.py
"""

import os
import sys
import subprocess
from pathlib import Path

# Thêm thư mục gốc dự án vào path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def print_header(title: str):
    """In header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_wifi():
    """Kiểm tra kết nối WiFi"""
    print_header("KIỂM TRA WIFI")
    
    # Kiểm tra interface wifi
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"],
            capture_output=True, text=True, timeout=10
        )
        print("\n📡 Các thiết bị mạng:")
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split(':')
                if len(parts) >= 3:
                    dev, typ, state = parts[:3]
                    icon = "✅" if state == "connected" else "❌"
                    print(f"  {icon} {dev} ({typ}): {state}")
    except Exception as e:
        print(f"  ❌ Lỗi kiểm tra thiết bị: {e}")
    
    # Kiểm tra SSID đang kết nối
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"],
            capture_output=True, text=True, timeout=10
        )
        print("\n📶 WiFi hiện tại:")
        found_active = False
        for line in result.stdout.strip().split('\n'):
            if line and ':' in line:
                active, ssid = line.split(':', 1)
                if active.lower() == 'yes':
                    print(f"  ✅ Đang kết nối: {ssid}")
                    found_active = True
        if not found_active:
            print("  ❌ Chưa kết nối WiFi nào")
    except Exception as e:
        print(f"  ❌ Lỗi: {e}")
    
    # Kiểm tra IP
    try:
        result = subprocess.run(
            ["ip", "-4", "addr", "show", "wlan0"],
            capture_output=True, text=True, timeout=10
        )
        print("\n🌐 Địa chỉ IP (wlan0):")
        for line in result.stdout.strip().split('\n'):
            if 'inet ' in line:
                print(f"  ✅ {line.strip()}")
                break
        else:
            print("  ❌ Không có địa chỉ IP")
    except Exception as e:
        print(f"  ❌ Lỗi: {e}")
    
    # Kiểm tra Internet
    print("\n🌍 Kiểm tra Internet:")
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "3", "8.8.8.8"],
            capture_output=True, timeout=5
        )
        if result.returncode == 0:
            print("  ✅ Có kết nối Internet")
        else:
            print("  ❌ Không có Internet")
    except Exception:
        print("  ❌ Không thể ping")


def check_audio():
    """Kiểm tra thiết bị âm thanh"""
    print_header("KIỂM TRA AUDIO")
    
    # Kiểm tra ALSA devices
    print("\n🔊 Thiết bị ALSA (aplay -l):")
    try:
        result = subprocess.run(
            ["aplay", "-l"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                if 'card' in line.lower():
                    print(f"  🔈 {line}")
        else:
            print("  ❌ Không tìm thấy thiết bị phát âm thanh")
    except Exception as e:
        print(f"  ❌ Lỗi: {e}")
    
    # Kiểm tra thiết bị thu âm
    print("\n🎤 Thiết bị thu âm (arecord -l):")
    try:
        result = subprocess.run(
            ["arecord", "-l"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                if 'card' in line.lower():
                    print(f"  🎤 {line}")
        else:
            print("  ❌ Không tìm thấy thiết bị thu âm")
    except Exception as e:
        print(f"  ❌ Lỗi: {e}")
    
    # Kiểm tra PulseAudio/PipeWire
    print("\n🎵 Audio Server:")
    try:
        result = subprocess.run(
            ["pactl", "info"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if 'Server Name' in line or 'Default Sink' in line or 'Default Source' in line:
                    print(f"  ℹ️ {line}")
        else:
            print("  ⚠️ PulseAudio không chạy")
    except FileNotFoundError:
        print("  ⚠️ pactl không có sẵn (PulseAudio không được cài đặt)")
    except Exception as e:
        print(f"  ❌ Lỗi: {e}")
    
    # Kiểm tra volume
    print("\n🔉 Âm lượng:")
    try:
        result = subprocess.run(
            ["amixer", "get", "Master"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if '%' in line:
                    print(f"  📊 {line.strip()}")
        else:
            # Thử với Headphone
            result = subprocess.run(
                ["amixer", "get", "Headphone"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if '%' in line:
                        print(f"  📊 {line.strip()}")
    except Exception as e:
        print(f"  ⚠️ Không thể đọc âm lượng: {e}")


def check_sounddevice():
    """Kiểm tra sounddevice (Python audio)"""
    print_header("KIỂM TRA SOUNDDEVICE (Python)")
    
    try:
        import sounddevice as sd
        
        print("\n🎤 Thiết bị đầu vào (MIC):")
        devices = sd.query_devices()
        input_count = 0
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                input_count += 1
                default = " (MẶC ĐỊNH)" if i == sd.default.device[0] else ""
                print(f"  [{i}] {dev['name']}{default}")
                print(f"      Kênh: {dev['max_input_channels']}, Sample Rate: {int(dev['default_samplerate'])}Hz")
        
        if input_count == 0:
            print("  ❌ Không tìm thấy thiết bị đầu vào!")
        
        print("\n🔊 Thiết bị đầu ra (LOA):")
        output_count = 0
        for i, dev in enumerate(devices):
            if dev['max_output_channels'] > 0:
                output_count += 1
                default = " (MẶC ĐỊNH)" if i == sd.default.device[1] else ""
                print(f"  [{i}] {dev['name']}{default}")
                print(f"      Kênh: {dev['max_output_channels']}, Sample Rate: {int(dev['default_samplerate'])}Hz")
        
        if output_count == 0:
            print("  ❌ Không tìm thấy thiết bị đầu ra!")
            
    except ImportError:
        print("  ❌ sounddevice chưa được cài đặt")
        print("     Chạy: pip install sounddevice")
    except Exception as e:
        print(f"  ❌ Lỗi: {e}")


def check_wake_word():
    """Kiểm tra cấu hình Wake Word"""
    print_header("KIỂM TRA WAKE WORD")
    
    models_dir = project_root / "models"
    
    # Kiểm tra file models
    required_files = [
        "encoder.onnx",
        "decoder.onnx", 
        "joiner.onnx",
        "tokens.txt",
        "keywords.txt"
    ]
    
    print("\n📁 Kiểm tra file model:")
    all_exist = True
    for f in required_files:
        path = models_dir / f
        if path.exists():
            size = path.stat().st_size / 1024 / 1024  # MB
            print(f"  ✅ {f} ({size:.2f} MB)")
        else:
            print(f"  ❌ {f} - KHÔNG TÌM THẤY!")
            all_exist = False
    
    # Kiểm tra keywords
    keywords_file = models_dir / "keywords.txt"
    if keywords_file.exists():
        print("\n🎤 Keywords đã cấu hình:")
        with open(keywords_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.rsplit('@', 1)
                    if len(parts) == 2:
                        chars, name = parts
                        print(f"  • {name}: '{chars.replace(' ', '')}'")
    
    # Kiểm tra config
    config_file = project_root / "config" / "config.json"
    if config_file.exists():
        import json
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        wake_word_opts = config.get("WAKE_WORD_OPTIONS", {})
        print("\n⚙️ Cấu hình Wake Word:")
        print(f"  USE_WAKE_WORD: {wake_word_opts.get('USE_WAKE_WORD', 'N/A')}")
        print(f"  KEYWORDS_THRESHOLD: {wake_word_opts.get('KEYWORDS_THRESHOLD', 'N/A')}")
        print(f"  KEYWORDS_SCORE: {wake_word_opts.get('KEYWORDS_SCORE', 'N/A')}")
        print(f"  NUM_THREADS: {wake_word_opts.get('NUM_THREADS', 'N/A')}")


def test_audio_playback():
    """Test phát âm thanh"""
    print_header("TEST PHÁT ÂM THANH")
    
    print("\n🔊 Đang phát âm thanh test (sine wave 1 giây)...")
    
    try:
        import sounddevice as sd
        import numpy as np
        
        duration = 1  # seconds
        frequency = 440  # Hz (A4 note)
        sample_rate = 44100
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio = np.sin(2 * np.pi * frequency * t) * 0.3
        
        sd.play(audio, sample_rate)
        sd.wait()
        
        print("  ✅ Phát âm thanh thành công!")
        print("     Nếu bạn nghe thấy tiếng beep, loa hoạt động bình thường.")
        
    except Exception as e:
        print(f"  ❌ Lỗi phát âm thanh: {e}")


def test_audio_recording():
    """Test thu âm"""
    print_header("TEST THU ÂM")
    
    print("\n🎤 Đang thu âm 2 giây... Hãy nói gì đó!")
    
    try:
        import sounddevice as sd
        import numpy as np
        
        duration = 2  # seconds
        sample_rate = 16000
        
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype=np.float32
        )
        sd.wait()
        
        max_amplitude = np.max(np.abs(recording))
        rms = np.sqrt(np.mean(recording**2))
        
        print(f"\n  📊 Kết quả thu âm:")
        print(f"     Biên độ max: {max_amplitude:.4f}")
        print(f"     RMS: {rms:.4f}")
        
        if max_amplitude > 0.01:
            print(f"  ✅ MIC hoạt động bình thường!")
        else:
            print(f"  ⚠️ Biên độ thấp - kiểm tra MIC và gain")
        
    except Exception as e:
        print(f"  ❌ Lỗi thu âm: {e}")


def main():
    """Main function"""
    print("\n" + "🤖 SMART C - CÔNG CỤ KIỂM TRA HỆ THỐNG 🤖".center(60))
    print("=" * 60)
    
    check_wifi()
    check_audio()
    check_sounddevice()
    check_wake_word()
    
    print("\n" + "-" * 60)
    response = input("\n🎵 Bạn có muốn test phát âm thanh không? (y/n): ")
    if response.lower() == 'y':
        test_audio_playback()
    
    response = input("\n🎤 Bạn có muốn test thu âm không? (y/n): ")
    if response.lower() == 'y':
        test_audio_recording()
    
    print("\n" + "=" * 60)
    print("  KIỂM TRA HOÀN TẤT")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
