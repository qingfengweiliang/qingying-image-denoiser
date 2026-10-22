# Rebuild from this folder: python -m PyInstaller --noconfirm build.spec
# Install requirements.txt and PyInstaller first.
from pathlib import Path

root = Path(SPECPATH)
a = Analysis([str(root / 'app.py')], pathex=[str(root)], binaries=[],
    datas=[(str(root / 'native'), 'native'), (str(root / 'assets'), 'assets')],
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['tkinter', 'torch', 'onnxruntime', 'matplotlib', 'pytest', 'IPython', 'pandas',
              'scipy.tests', 'scipy.ndimage.tests', 'PySide6.QtQml', 'PySide6.QtQuick',
              'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets'],
    noarchive=False, optimize=0)
# Qt uses Windows' ICU API. Do not bundle unrelated same-named ICU DLLs from PATH.
a.binaries = [entry for entry in a.binaries
              if not (Path(entry[0]).name.lower().startswith('icu') and entry[0].lower().endswith('.dll'))]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='清影图片降噪',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False, icon=str(root / 'assets' / 'app_icon.ico'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='清影图片降噪')
