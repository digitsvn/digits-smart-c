#!/usr/bin/env python3
"""Quick test script for Smart C AI on Raspberry Pi"""
import subprocess
import sys

def run(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout.strip() or result.stderr.strip()
    except:
        return "Error"

def test_audio():
    print("\n🔊 AUDIO TEST")
    print("-" * 40)
    
    # Check devices
    output = run("aplay -l 2>&1 | grep -E 'card|device' | head -6")
    print(f"Output devices:\n{output}")
    
    input_dev = run("arecord -l 2>&1 | grep -E 'card|device' | head -4")
    print(f"\nInput devices:\n{input_dev}")
    
    # Check PulseAudio
    pa_status = run("pulseaudio --check && echo 'Running' || echo 'Not running'")
    print(f"\nPulseAudio: {pa_status}")
    
    # Test record
    print("\n📢 Recording 2 seconds...")
    run("arecord -d 2 -f cd /tmp/test.wav 2>/dev/null")
    if subprocess.run("test -f /tmp/test.wav", shell=True).returncode == 0:
        size = run("ls -lh /tmp/test.wav | awk '{print $5}'")
        print(f"✓ Recording saved: {size}")
    else:
        print("✗ Recording failed")

def test_wifi():
    print("\n📶 WIFI TEST")
    print("-" * 40)
    
    # Check connection
    ssid = run("nmcli -t -f active,ssid dev wifi | grep '^yes' | cut -d: -f2")
    if ssid:
        print(f"✓ Connected to: {ssid}")
    else:
        print("✗ Not connected to any WiFi")
    
    # Check internet
    ping = run("ping -c 1 -W 2 8.8.8.8 2>&1 | grep -E 'time=|100% packet loss'")
    if "time=" in ping:
        print("✓ Internet: OK")
    else:
        print("✗ Internet: No connection")

def test_display():
    print("\n🖥️  DISPLAY TEST")
    print("-" * 40)
    
    wayland = run("echo $WAYLAND_DISPLAY")
    display = run("echo $DISPLAY")
    
    print(f"WAYLAND_DISPLAY: {wayland or 'Not set'}")
    print(f"DISPLAY: {display or 'Not set'}")
    
    # Check labwc
    labwc = run("pgrep -a labwc | head -1")
    if labwc:
        print(f"✓ Wayland compositor running: labwc")
    else:
        print("✗ No Wayland compositor found")

def test_app():
    print("\n🤖 APP TEST")
    print("-" * 40)
    
    # Check files
    import os
    files = ['main.py', 'run.sh', 'models/keywords.txt', 'config/config.json']
    app_home = os.path.expanduser("~/.digits")
    
    for f in files:
        path = os.path.join(app_home, f)
        if os.path.exists(path):
            print(f"✓ {f}")
        else:
            print(f"✗ {f} - MISSING!")
    
    # Check autostart
    autostart = os.path.expanduser("~/.config/autostart/smartc.desktop")
    if os.path.exists(autostart):
        print("✓ Autostart configured")
    else:
        print("✗ Autostart not configured")

if __name__ == "__main__":
    print("=" * 50)
    print("   SMART C AI - QUICK DIAGNOSTIC")
    print("=" * 50)
    
    test_wifi()
    test_audio()
    test_display()
    test_app()
    
    print("\n" + "=" * 50)
    print("   TEST COMPLETE")
    print("=" * 50)
    print("\nĐể chạy app, reboot Pi hoặc chạy: ~/.digits/run.sh")
