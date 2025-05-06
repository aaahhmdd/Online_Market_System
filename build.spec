# build.spec (updated)
block_cipher = None
a = Analysis(
    ['desktop_app.py'],
    # ... keep other parameters ...
    datas=[
        ('templates/*', 'templates'),
        ('market.db', '.')  # Critical: Include DB in root of bundle
    ],
    hiddenimports=[
        'flask',
        'flask_sqlalchemy',
        'flask_restful',
        'werkzeug.security',
        'webview'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MarketplaceApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to True if you want to see console output
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)