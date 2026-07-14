# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [("assets", "assets"), ("data", "data")]
binaries = []
hiddenimports = []
for package in ["dash", "dash_ag_grid", "plotly", "sklearn", "pandas", "numpy", "openpyxl"]:
    d, b, h = collect_all(package)
    datas += d; binaries += b; hiddenimports += h

a = Analysis(["demeter_launcher.py"], pathex=["."], binaries=binaries, datas=datas,
    hiddenimports=hiddenimports, hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="DemeterDashboard", debug=False,
    bootloader_ignore_signals=False, strip=False, upx=True, console=False, disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, name="DemeterDashboard")
