#!/usr/bin/env python3
import json
import uuid
import hashlib
import os
import sys

CONFIG_PATH = os.path.expanduser("~/.digits/config/config.json")
if not os.path.exists(CONFIG_PATH):
    CONFIG_PATH = os.path.expanduser("~/.xiaozhi/config/config.json")

def get_mac_address():
    """Get the MAC address of the device."""
    # uuid.getnode() returns the MAC address as an integer
    mac = uuid.getnode()
    return ':'.join(("%012X" % mac)[i:i+2] for i in range(0, 12, 2))

def generate_hardware_uuid(salt=""):
    """Generate a deterministic UUID based on MAC address and optional salt."""
    mac = get_mac_address()
    # Create a unique string based on MAC and salt
    unique_str = f"{mac}-{salt}"
    # Use MD5 to hash it (uuid3 uses MD5)
    return str(uuid.uuid3(uuid.NAMESPACE_DNS, unique_str))

def ensure_ids():
    if not os.path.exists(CONFIG_PATH):
        print(f"Error: Config file not found at {CONFIG_PATH}")
        return

    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError:
        config = {}

    if 'SYSTEM_OPTIONS' not in config:
        config['SYSTEM_OPTIONS'] = {}

    # Generate persistent hardware-based IDs
    # DEVICE_ID: Unique to the machine hardware
    hardware_device_id = generate_hardware_uuid(salt="device")
    
    # CLIENT_ID: Also unique to machine, but distinct from device_id
    hardware_client_id = generate_hardware_uuid(salt="client")
    
    current_device_id = config['SYSTEM_OPTIONS'].get('DEVICE_ID')
    current_client_id = config['SYSTEM_OPTIONS'].get('CLIENT_ID')

    updated = False
    
    # Check if we need to update to hardware IDs
    # User requested: "nếu trên máy đó thì vẫn là id dó" (same ID if on that machine)
    # This implies we should enforce the hardware ID.
    
    if current_device_id != hardware_device_id:
        print(f"🔄 Updating DEVICE_ID to hardware-based ID: {hardware_device_id}")
        config['SYSTEM_OPTIONS']['DEVICE_ID'] = hardware_device_id
        updated = True
    else:
        print(f"✅ DEVICE_ID is consistent with hardware: {hardware_device_id}")

    if current_client_id != hardware_client_id:
        print(f"🔄 Updating CLIENT_ID to hardware-based ID: {hardware_client_id}")
        config['SYSTEM_OPTIONS']['CLIENT_ID'] = hardware_client_id
        updated = True
    else:
        print(f"✅ CLIENT_ID is consistent with hardware: {hardware_client_id}")

    if updated:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print("💾 Configuration saved with persistent hardware IDs.")

if __name__ == "__main__":
    try:
        ensure_ids()
    except Exception as e:
        print(f"Error ensuring IDs: {e}")
