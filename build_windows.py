"""Build a self-contained Windows executable, excluding models and local data."""
from pathlib import Path
import importlib.metadata as metadata
import argparse,subprocess,sys

BASE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,default=BASE/'releases')
options=parser.parse_args()
if sys.platform!='win32':raise SystemExit('Build this Windows app on Windows.')
packages=['requests','httpx','beautifulsoup4','psutil','PyAutoGUI','Pillow','pywinauto','pywin32','ddgs','pywebview','pythonnet','clr_loader','comtypes','primp','lxml','urllib3','certifi','charset_normalizer','idna','anyio','httpcore','h11','six','cffi','pycparser','proxy_tools','bottle','pyperclip','pyscreeze','pygetwindow','mouseinfo','pytweening','pymsgbox','pyrect','soupsieve','click','typing_extensions']
lines=['JARVIS THIRD-PARTY NOTICES','\nThe following runtime packages retain their own licenses. Model weights are not bundled.\n']
for package in packages:
    try:
        dist=metadata.distribution(package)
        lines.append(f'\n{package} {dist.version}\nLicense metadata: {dist.metadata.get("License-Expression",dist.metadata.get("License","See package license"))}\n')
        for file in dist.files or []:
            if any(term in file.name.lower() for term in ['license','copyright','notice']) and '.dist-info' in str(file):
                path=dist.locate_file(file)
                if path.is_file():
                    try:lines.append(path.read_text(encoding='utf-8',errors='replace'))
                    except OSError:pass
    except metadata.PackageNotFoundError:pass
notice=BASE/'THIRD-PARTY-NOTICES.txt';notice.write_text('\n'.join(lines),encoding='utf-8')
args=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onefile','--windowed','--name','Jarvis',
      '--add-data',f'{BASE / "static"};static','--add-data',f'{notice};.',
      '--collect-all','webview','--collect-all','ddgs','--collect-submodules','pywinauto','--collect-submodules','comtypes',
      '--hidden-import','pyautogui','--hidden-import','pythoncom','--hidden-import','win32clipboard','--hidden-import','win32gui','--hidden-import','win32api',
      '--distpath',str(options.output.resolve()),'--workpath',str(BASE.parent.parent/'work'/'pyinstaller'),
      '--specpath',str(BASE.parent.parent/'work')]
for package in packages:
    try:metadata.distribution(package);args+=['--copy-metadata',package]
    except metadata.PackageNotFoundError:pass
subprocess.run(args+[str(BASE/'app.py')],check=True,cwd=BASE)
print('Built:',options.output.resolve()/'Jarvis.exe')
