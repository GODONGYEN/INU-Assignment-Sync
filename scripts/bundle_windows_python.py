"""Run on Windows after setup-python + pip install -r requirements.txt."""
import shutil
import sys
from pathlib import Path

if sys.platform != 'win32':
    raise SystemExit('Windows에서 실행하세요.')
destination = Path('electron-app/python-runtime')
if destination.exists():
    raise SystemExit('python-runtime 폴더가 이미 있습니다. 새 빌드 작업 폴더를 사용하세요.')
shutil.copytree(Path(sys.base_prefix), destination,
                ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'Doc', 'tcl', 'Tools'))
print('Bundled Python:', destination)
