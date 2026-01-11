#!/usr/bin/env python3
"""
Script để reset Device ID và Client ID
Sử dụng: 
    python3 reset_device_id.py           # Interactive mode
    python3 reset_device_id.py --random  # Quick random
"""

import json
import sys
import uuid
from pathlib import Path
import os

def reset_ids(auto_random=False):
    """Reset Device ID và Client ID"""
    
    app_root = Path(os.environ.get("DIGITS_HOME") or (Path.home() / ".digits"))
    if not app_root.exists():
        legacy = Path.home() / ".xiaozhi"
        if legacy.exists():
            app_root = legacy
    config_path = app_root / "config" / "config.json"
    efuse_path = app_root / "config" / "efuse.json"
    
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║     🔄 RESET DEVICE ID VÀ CLIENT ID - Digits Smart C AI  ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()
    
    # Đọc config hiện tại
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        old_client_id = config.get('SYSTEM_OPTIONS', {}).get('CLIENT_ID')
        old_device_id = config.get('SYSTEM_OPTIONS', {}).get('DEVICE_ID')
        
        print(f"📱 CLIENT_ID cũ: {old_client_id}")
        print(f"🔧 DEVICE_ID cũ: {old_device_id}")
        print()
    else:
        print("⚠️  Không tìm thấy file config.json")
        return
    
    # Xác nhận
    print("❓ Bạn muốn:")
    print("   1. 🎲 RANDOM cả CLIENT_ID và DEVICE_ID (Khuyến nghị)")
    print("   2. Tạo chỉ CLIENT_ID mới (giữ DEVICE_ID)")
    print("   3. Tạo chỉ DEVICE_ID mới (giữ CLIENT_ID)")
    print("   4. Chỉnh sửa thủ công")
    print("   0. Hủy")
    print()
    
    choice = input("Chọn (0-4): ").strip()
    
    if choice == '0':
        print("❌ Đã hủy")
        return
    
    elif choice == '1':
        # RANDOM CẢ HAI (Option khuyến nghị)
        new_client_id = str(uuid.uuid4())
        new_device_id = str(uuid.uuid4())  # Random UUID thay vì dùng MAC
        
        if 'SYSTEM_OPTIONS' not in config:
            config['SYSTEM_OPTIONS'] = {}
        
        config['SYSTEM_OPTIONS']['CLIENT_ID'] = new_client_id
        config['SYSTEM_OPTIONS']['DEVICE_ID'] = new_device_id
        
        # Lưu config
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print()
        print("✅ Đã tạo ID RANDOM mới:")
        print(f"   CLIENT_ID:  {new_client_id}")
        print(f"   DEVICE_ID:  {new_device_id}")
        print()
        print("💡 Tip: Mỗi máy Pi sẽ có ID hoàn toàn khác nhau!")
        
    elif choice == '2':
        # Tạo CLIENT_ID mới
        new_client_id = str(uuid.uuid4())
        
        if 'SYSTEM_OPTIONS' not in config:
            config['SYSTEM_OPTIONS'] = {}
        
        config['SYSTEM_OPTIONS']['CLIENT_ID'] = new_client_id
        
        # Lưu config
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print()
        print("✅ Đã tạo CLIENT_ID mới:")
        print(f"   {new_client_id}")
        print(f"   DEVICE_ID giữ nguyên: {old_device_id}")
        
    elif choice == '3':
        # Tạo DEVICE_ID mới
        new_device_id = str(uuid.uuid4())
        
        if 'SYSTEM_OPTIONS' not in config:
            config['SYSTEM_OPTIONS'] = {}
        
        config['SYSTEM_OPTIONS']['DEVICE_ID'] = new_device_id
        
        # Lưu config
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print()
        print("✅ Đã tạo DEVICE_ID mới:")
        print(f"   {new_device_id}")
        print(f"   CLIENT_ID giữ nguyên: {old_client_id}")
        
    elif choice == '4':
        # Chỉnh sửa thủ công
        print()
        print("📝 Nhập ID mới (Enter để giữ nguyên):")
        print()
        
        new_client_id = input(f"CLIENT_ID [{old_client_id}]: ").strip()
        if not new_client_id:
            new_client_id = old_client_id
        
        new_device_id = input(f"DEVICE_ID [{old_device_id}]: ").strip()
        if not new_device_id:
            new_device_id = old_device_id
        
        if 'SYSTEM_OPTIONS' not in config:
            config['SYSTEM_OPTIONS'] = {}
        
        config['SYSTEM_OPTIONS']['CLIENT_ID'] = new_client_id
        config['SYSTEM_OPTIONS']['DEVICE_ID'] = new_device_id
        
        # Lưu config
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print()
        print("✅ Đã cập nhật ID:")
        print(f"   CLIENT_ID:  {new_client_id}")
        print(f"   DEVICE_ID:  {new_device_id}")
    
    else:
        print("❌ Lựa chọn không hợp lệ")
        return
    
    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("⚠️  Lưu ý: Khởi động lại app để áp dụng thay đổi")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

def quick_random():
    """Tạo random IDs nhanh không cần hỏi"""
    app_root = Path(os.environ.get("DIGITS_HOME") or (Path.home() / ".digits"))
    if not app_root.exists():
        legacy = Path.home() / ".xiaozhi"
        if legacy.exists():
            app_root = legacy
    config_path = app_root / "config" / "config.json"
    
    if not config_path.exists():
        print("❌ Không tìm thấy file config.json")
        return
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    new_client_id = str(uuid.uuid4())
    new_device_id = str(uuid.uuid4())
    
    if 'SYSTEM_OPTIONS' not in config:
        config['SYSTEM_OPTIONS'] = {}
    
    config['SYSTEM_OPTIONS']['CLIENT_ID'] = new_client_id
    config['SYSTEM_OPTIONS']['DEVICE_ID'] = new_device_id
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print("✅ Đã tạo RANDOM ID mới:")
    print(f"   CLIENT_ID: {new_client_id}")
    print(f"   DEVICE_ID: {new_device_id}")
    print()
    print("💡 Mỗi máy Pi có ID riêng biệt!")

if __name__ == "__main__":
    try:
        # Check for --random flag
        if len(sys.argv) > 1 and sys.argv[1] in ['--random', '-r']:
            quick_random()
        else:
            reset_ids()
    except KeyboardInterrupt:
        print("\n\n❌ Đã hủy bởi người dùng")
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
