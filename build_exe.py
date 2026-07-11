import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(ROOT, 'main.py')
DIST = os.path.join(ROOT, 'dist')

cmd = [
    sys.executable, '-m', 'PyInstaller',
    '--onefile',
    '--windowed',
    '--name', 'FlowConvert',
    '--distpath', DIST,
    '--clean',
    '--noconfirm',
    MAIN,
]

print('Running:', ' '.join(cmd))
subprocess.check_call(cmd)
print(f'\nBuild complete. EXE at: {os.path.join(DIST, "FlowConvert.exe")}')
