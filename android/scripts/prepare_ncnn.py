"""Fetch the pinned Android ncnn archive and verify it before extraction."""
import hashlib
import io
from pathlib import Path
import urllib.request
import zipfile

VERSION = '20250503'
SHA256 = '4b54cd11094dae1371c59fb202dfd92d22962ffaef04317bdf99b12c09f44ed3'
ROOT = Path(__file__).resolve().parents[1]
URL = f'https://github.com/Tencent/ncnn/releases/download/{VERSION}/ncnn-{VERSION}-android-vulkan.zip'

def main():
    print('Downloading pinned ncnn Android libraries...')
    data = urllib.request.urlopen(URL, timeout=180).read()
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise RuntimeError('ncnn archive checksum mismatch')
    prefix = f'ncnn-{VERSION}-android-vulkan/'
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for info in archive.infolist():
            if not info.filename.startswith(prefix):
                continue
            relative = Path(info.filename[len(prefix):])
            if not relative.parts or relative.parts[0] not in ('arm64-v8a', 'x86_64'):
                continue
            if '..' in relative.parts or relative.is_absolute():
                raise RuntimeError('Invalid archive path')
            target = ROOT / 'vendor' / 'ncnn' / relative
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(info))
    print('Ready: vendor/ncnn')

if __name__ == '__main__':
    main()
