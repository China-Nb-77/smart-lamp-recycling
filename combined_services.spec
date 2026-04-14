# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['packager\\launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('wechat_payment_fix\\pay-demo\\target\\pay-demo-patch-0.0.1-SNAPSHOT.jar', '.'), ('fulfillment - 副本\\target\\fulfillment-1.0.0.jar', '.')],
    hiddenimports=[],
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
    name='combined_services',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
