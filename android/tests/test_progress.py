"""Exercise progress math with a real JDK, independent of Android tooling."""
from pathlib import Path
import subprocess
import tempfile
import shutil

root = Path(__file__).resolve().parents[1]
javac = Path(shutil.which('javac') or 'javac')
java = javac.with_name('java.exe' if javac.suffix == '.exe' else 'java')
with tempfile.TemporaryDirectory() as directory:
    subprocess.run([
        str(javac), '-encoding', 'UTF-8', '-d', directory,
        str(root / 'app/src/main/java/cn/qingying/denoiser/ProcessingProgress.java'),
        str(root / 'tests/java/ProcessingProgressTest.java'),
    ], check=True)
    subprocess.run([str(java), '-cp', directory, 'cn.qingying.denoiser.ProcessingProgressTest'], check=True)
