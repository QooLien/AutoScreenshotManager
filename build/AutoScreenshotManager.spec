from pathlib import Path
root = Path(SPECPATH).parent
analysis = Analysis([str(root / "main.py")], pathex=[str(root)], binaries=[], datas=[], hiddenimports=["win32timezone"], hookspath=[], runtime_hooks=[], excludes=[])
pyz = PYZ(analysis.pure)
exe = EXE(pyz, analysis.scripts, analysis.binaries, analysis.datas, [], name="AutoScreenshotManager", debug=False, strip=False, upx=False, console=False)
