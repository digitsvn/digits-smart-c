# Copilot Instructions (Xiaozhi Pi)

## Project Identity
Voice AI assistant for Raspberry Pi with TV display integration. Python 3.9+ asyncio-based architecture supporting GUI (PyQt5/QML) and CLI modes, real-time audio streaming, wake word detection, and MCP server integration.

## Quick Start
**Run**: `python main.py --mode gui` (default) or `--mode cli` for headless  
**Protocols**: `--protocol websocket` (default) or `--protocol mqtt`  
**Skip Activation** (debug only): `--skip-activation`  
**Disable Audio** (testing): `XIAOZHI_DISABLE_AUDIO=1 python main.py`

**First Run**: SystemInitializer ([src/core/system_initializer.py](../src/core/system_initializer.py)) handles:
- Device fingerprint creation (`config/efuse.json`)
- Config initialization (`config/config.json`)
- OTA config fetch
- v1 (skip activation) vs v2 (activation UI) protocol detection

## Architecture (Data Flow)
**Singleton Orchestrator**: `Application` ([src/application.py](../src/application.py))
- Owns `Protocol` (WebsocketProtocol/MqttProtocol), device state (`DeviceState`, `ListeningMode`)
- Task registry via `Application.spawn(coro, name)` — use this, NOT `asyncio.create_task()` directly
- Asyncio objects initialized in `run()`: `_shutdown_event`, `_state_lock`, `_connect_lock`

**Plugin System** ([src/plugins/](../src/plugins/)):
- Lifecycle: `setup(app)` → `start()` → (running) → `stop()` → `shutdown()`
- Managed by `PluginManager` ([manager.py](../src/plugins/manager.py)); errors isolated (swallowed)
- Event broadcast: `notify_incoming_audio(data)`, `notify_incoming_json(msg)`, `notify_device_state_changed(state)`
- Key plugins: `AudioPlugin`, `UIPlugin`, `WakeWordPlugin`, `McpPlugin`, `CalendarPlugin`, `IoTPlugin`, `ShortcutsPlugin`

**Protocol Events** (callbacks set in `Application._setup_protocol_callbacks()`):
- Binary audio → `plugins.notify_incoming_audio(...)`
- JSON messages → `plugins.notify_incoming_json(...)` → UI state derived from `tts start/stop` events

**State Transitions**: MUST use `Application.set_device_state(...)` to update state and trigger plugin notifications

## Config & Runtime Paths
- **Config**: `config/config.json` (auto-merged) via `ConfigManager.get_instance()` ([src/utils/config_manager.py](../src/utils/config_manager.py))
- **Device ID**: `config/efuse.json` via `DeviceFingerprint` ([src/utils/device_fingerprint.py](../src/utils/device_fingerprint.py))
- **Resource Paths**: Use `resource_finder` ([src/utils/resource_finder.py](../src/utils/resource_finder.py)) for dev vs PyInstaller compatibility
- **Listening Mode**: Forced to `ListeningMode.REALTIME` for continuous TV use (auto-listen after TTS)

## Audio Pipeline (Critical Points)
- **Stack**: `AudioPlugin` ([src/plugins/audio.py](../src/plugins/audio.py)) + `AudioCodec` ([src/audio_codecs/audio_codec.py](../src/audio_codecs/audio_codec.py))
- **Opus Native Lib**: Loaded early via `setup_opus()` ([src/utils/opus_loader.py](../src/utils/opus_loader.py)) from `libs/libopus/`
- **Frame Duration**: ARM-optimized (Raspberry Pi) in `AudioConfig.FRAME_DURATION` ([src/constants/constants.py](../src/constants/constants.py))
- **AEC**: Configurable via `AEC_OPTIONS.ENABLED` in config (WebRTC AEC in `libs/webrtc_apm/`)
- **Wake Word**: Sherpa ONNX models in `models/` (encoder.onnx, decoder.onnx, joiner.onnx, keywords.txt)

## GUI (PyQt5 + QML)
- **Architecture**: `UIPlugin(mode="gui")` → `GuiDisplay` ([src/display/gui_display.py](../src/display/gui_display.py)) → loads [src/display/gui_display.qml](../src/display/gui_display.qml)
- **Data Binding**: `GuiDisplayModel` ([src/display/gui_display_model.py](../src/display/gui_display_model.py)) properties/signals — update model, not QML directly
- **Event Loop**: Uses qasync (`QEventLoop`) in GUI mode, plain asyncio in CLI mode (see [main.py](../main.py) L126-148)
- **Wayland Support**: Auto-detects Wayland, sets `QT_QPA_PLATFORM=wayland;xcb` (L95-103)
- **Camera**: OpenCV snapshot-based ([src/mcp/tools/camera](../src/mcp/tools/camera)) for single-frame capture, not streaming

## MCP Server Integration
- **Implementation**: [src/mcp/mcp_server.py](../src/mcp/mcp_server.py) registers tools from `src/mcp/tools/*`
- **Tool Pattern**: `McpTool(name, description, PropertyList, callback)` — return simple types (bool/int/str)
- **Activation**: MCP server starts as part of `McpPlugin` lifecycle

## Code Conventions
- **Async Scheduling**: Use `Application.spawn(coro, name)` or `schedule_command_nowait(fn)` — avoid `create_task()` in plugins
- **State Updates**: Call `Application.set_device_state(state)` — broadcasts to `notify_device_state_changed()`
- **Error Handling**: Plugins isolate errors (logged but swallowed); validate inside plugin if critical
- **Logging**: Vietnamese comments in code; use `get_logger(__name__)` ([src/utils/logging_config.py](../src/utils/logging_config.py))
- **Code Style**: Black (line-length=88), isort profile=black (see [pyproject.toml](../pyproject.toml))

## Deployment (Raspberry Pi)
- **Scripts**: [install.sh](../install.sh), [RASPBERRY_PI_INSTALL.sh](../RASPBERRY_PI_INSTALL.sh), [build_for_pi.sh](../build_for_pi.sh)
- **Autostart**: [install_autostart.sh](../install_autostart.sh) → systemd service
- **PyInstaller**: [xiaozhi.spec](../xiaozhi.spec) bundles into single executable
- **Docs**: [PI_DEPLOYMENT.md](../PI_DEPLOYMENT.md), [TV_SETUP_GUIDE.md](../TV_SETUP_GUIDE.md)

## Key Files
- Entry: [main.py](../main.py)
- Core: [src/application.py](../src/application.py), [src/core/system_initializer.py](../src/core/system_initializer.py)
- Plugins: [src/plugins/](../src/plugins/) (base.py, audio.py, ui.py, mcp.py, wake_word.py)
- Config: [src/utils/config_manager.py](../src/utils/config_manager.py), [src/utils/device_fingerprint.py](../src/utils/device_fingerprint.py)
- Display: [src/display/gui_display.py](../src/display/gui_display.py), [src/display/gui_display.qml](../src/display/gui_display.qml)
