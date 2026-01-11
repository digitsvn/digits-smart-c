#!/usr/bin/env python3

import json
import os
from pathlib import Path


def main() -> int:
    app_root = Path(os.environ.get("DIGITS_HOME") or (Path.home() / ".digits"))
    if not app_root.exists():
        legacy = Path.home() / ".xiaozhi"
        if legacy.exists():
            app_root = legacy
    config_path = app_root / "config" / "config.json"
    efuse_path = app_root / "config" / "efuse.json"

    if not efuse_path.exists():
        print(f"❌ Missing efuse.json: {efuse_path}")
        return 2

    efuse = json.loads(efuse_path.read_text(encoding="utf-8"))
    mac = (efuse.get("mac_address") or "").strip().lower()
    if not mac:
        print("❌ efuse.json has no mac_address")
        return 3

    if not config_path.exists():
        print(f"❌ Missing config.json: {config_path}")
        return 4

    config = json.loads(config_path.read_text(encoding="utf-8"))
    config.setdefault("SYSTEM_OPTIONS", {})

    current = (config["SYSTEM_OPTIONS"].get("DEVICE_ID") or "").strip()
    if current != mac:
        print(f"🔄 DEVICE_ID: {current!r} -> {mac!r}")
        config["SYSTEM_OPTIONS"]["DEVICE_ID"] = mac
        config_path.write_text(
            json.dumps(config, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    else:
        print(f"✅ DEVICE_ID already matches efuse MAC: {mac}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
