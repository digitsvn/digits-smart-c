# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('config', 'config'), ('libs', 'libs'), ('models', 'models'), ('src/display/gui_display.qml', '.'), ('src/views/settings/settings_window.ui', '.'), ('src/views/settings/components/audio/audio_widget.ui', '.'), ('src/views/settings/components/camera/camera_widget.ui', '.'), ('src/views/settings/components/system_options/system_options_widget.ui', '.'), ('src/views/settings/components/wake_word/wake_word_widget.ui', '.'), ('src/views/activation/activation_window.qml', '.')],
    hiddenimports=['pypinyin'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='xiaozhi',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='xiaozhi',
)
app = BUNDLE(
    coll,
    name='xiaozhi.app',
    icon=None,
    bundle_identifier='com.xiaozhi.desktop',
    info_plist={
        'NSCameraUsageDescription': 'This app requires camera access to capture images for vision analysis.',
        'NSMicrophoneUsageDescription': 'This app requires microphone access for voice interaction.',
        'NSHighResolutionCapable': 'True'
    },
)
