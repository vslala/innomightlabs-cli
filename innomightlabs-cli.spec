# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, collect_data_files

dep_datas, dep_binaries, dep_hiddenimports = collect_all("dependency_injector")
tiktoken_datas = collect_data_files("tiktoken")
tiktoken_ext_datas, tiktoken_ext_binaries, tiktoken_ext_hiddenimports = collect_all(
    "tiktoken_ext"
)

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[*dep_binaries, *tiktoken_ext_binaries],
    datas=[
        ("prompts", "prompts"),
        ("pyproject.toml", "."),
        *dep_datas,
        *tiktoken_datas,
        *tiktoken_ext_datas,
    ],
    hiddenimports=[*dep_hiddenimports, *tiktoken_ext_hiddenimports],
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
    name="innomightlabs-cli",
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
