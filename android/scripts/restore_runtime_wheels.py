"""Build an offline dependency bundle from the project's verified 1.0.0 Debug APK.

This is an optional fallback when chaquo.com is unreachable. It does not reuse
application code, JNI engines, models, or signatures: those are built normally.
The original dependency metadata and licenses are retained without modification.
"""
import argparse
import base64
import csv
import hashlib
import io
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
import zipfile

APK_SHA256 = 'be4aef205a2de339576b9d4a1ad770b7f538d5cada9ae823e97e7f3672b7250b'
VERSIONS = {'numpy': '1.23.3', 'scipy': '1.8.1', 'pillow': '11.0.0', 'opencv-python': '4.5.1.48'}
ROOT = Path(__file__).resolve().parents[1]


def restore(apk_path, output):
    data = Path(apk_path).read_bytes()
    if hashlib.sha256(data).hexdigest() != APK_SHA256:
        raise ValueError('Reference APK checksum mismatch: only the pinned project artifact is accepted')
    config = (ROOT / 'app/build.gradle').read_text(encoding='utf-8')
    if any(f'{name if name != "pillow" else "Pillow"}=={version}' not in config
           for name, version in VERSIONS.items()):
        raise ValueError('Dependency pins changed: obtain fresh official wheels rather than restoring old ones')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as apk:
        common = apk.read('assets/chaquopy/requirements-common.imy')
        for abi in ['arm64-v8a', 'x86_64']:
            files = {}
            for blob in [common, apk.read(f'assets/chaquopy/requirements-{abi}.imy')]:
                with zipfile.ZipFile(io.BytesIO(blob)) as archive:
                    for item in archive.infolist():
                        if item.is_dir():
                            continue
                        path = PurePosixPath(item.filename)
                        if path.is_absolute() or '..' in path.parts or '\\' in item.filename:
                            raise ValueError('Unsafe dependency archive path')
                        files[item.filename] = archive.read(item)
            versions = {}
            for name, content in files.items():
                if name.endswith('.dist-info/METADATA'):
                    metadata = BytesParser().parsebytes(content)
                    versions[metadata['Name'].lower().replace('_', '-')] = metadata['Version']
            if any(versions.get(name) != version for name, version in VERSIONS.items()):
                raise ValueError('Reference dependency versions do not match the build pins')
            tag = f'cp310-cp310-android_24_{abi.replace("-", "_")}'
            info = 'qingying_runtime-1.0.0.dist-info'
            files[f'{info}/METADATA'] = (
                'Metadata-Version: 2.1\nName: qingying-runtime\nVersion: 1.0.0\n'
                'Summary: Verified Qingying 1.0.0 Android dependencies for offline builds\n').encode()
            files[f'{info}/WHEEL'] = (
                f'Wheel-Version: 1.0\nGenerator: qingying-offline-runtime\nRoot-Is-Purelib: false\nTag: {tag}\n').encode()
            record = io.StringIO(newline='')
            writer = csv.writer(record)
            for name, content in sorted(files.items()):
                digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).decode().rstrip('=')
                writer.writerow([name, 'sha256=' + digest, len(content)])
            writer.writerow([f'{info}/RECORD', '', ''])
            files[f'{info}/RECORD'] = record.getvalue().encode()
            destination = output / f'qingying_runtime-1.0.0-{tag}.whl'
            with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as wheel:
                for name, content in sorted(files.items()):
                    wheel.writestr(name, content)
            print(f'Restored verified offline dependencies: {destination.name}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apk')
    parser.add_argument('--output', default=str(ROOT / 'vendor/runtime-wheels'))
    args = parser.parse_args()
    restore(args.apk, args.output)
