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


def write_wheel(output, name, version, tag, info, files, pure=False):
    files = dict(files)
    files[f'{info}/WHEEL'] = (
        f'Wheel-Version: 1.0\nGenerator: qingying-offline-runtime\n'
        f'Root-Is-Purelib: {str(pure).lower()}\nTag: {tag}\n').encode()
    record = io.StringIO(newline='')
    writer = csv.writer(record)
    for path, content in sorted(files.items()):
        digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).decode().rstrip('=')
        writer.writerow([path, 'sha256=' + digest, len(content)])
    writer.writerow([f'{info}/RECORD', '', ''])
    files[f'{info}/RECORD'] = record.getvalue().encode()
    destination = output / f'{name.replace("-", "_")}-{version}-{tag}.whl'
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as wheel:
        for path, content in sorted(files.items()):
            wheel.writestr(path, content)
    print(f'Restored verified offline dependency: {destination.name}')


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
    for abi in ['arm64_v8a', 'x86_64']:
        (output / f'qingying_runtime-1.0.0-cp310-cp310-android_24_{abi}.whl').unlink(missing_ok=True)
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
            versions, infos = {}, {}
            for name, content in files.items():
                if name.endswith('.dist-info/METADATA'):
                    metadata = BytesParser().parsebytes(content)
                    package = metadata['Name'].lower().replace('_', '-')
                    versions[package] = metadata['Version']
                    infos[package] = name.split('/')[0]
            if any(versions.get(name) != version for name, version in VERSIONS.items()):
                raise ValueError('Reference dependency versions do not match the build pins')
            # Reconstruct each distribution separately so Chaquopy can track ABI
            # ownership with standard WHEEL and RECORD metadata for every package.
            modules = {'numpy': 'numpy', 'scipy': 'scipy', 'PIL': 'pillow', 'cv2': 'opencv-python'}
            libraries = {
                'libc++_shared.so': 'chaquopy-libcxx', 'libfreetype.so': 'chaquopy-freetype',
                'libgfortran.so.3': 'chaquopy-libgfortran', 'libjpeg_chaquopy.so': 'chaquopy-libjpeg',
                'libopenblas.so': 'chaquopy-openblas', 'libpng16.so': 'chaquopy-libpng',
            }
            metadata_owners = {info: package for package, info in infos.items()}
            packages = {package: {} for package in infos}
            for path, content in files.items():
                top = path.split('/')[0]
                package = metadata_owners.get(top) or modules.get(top)
                if package is None and path.startswith('chaquopy/lib/'):
                    package = libraries.get(path.rsplit('/', 1)[-1])
                if package not in packages:
                    raise ValueError(f'Unrecognized dependency file ownership: {path}')
                packages[package][path] = content
            tag = f'cp310-cp310-android_24_{abi.replace("-", "_")}'
            for package, package_files in packages.items():
                write_wheel(output, package, versions[package], tag, infos[package], package_files)
    info = 'qingying_runtime-1.0.0.dist-info'
    metadata = ('Metadata-Version: 2.1\nName: qingying-runtime\nVersion: 1.0.0\n'
                'Summary: Verified Qingying Android dependencies for offline builds\n'
                + ''.join(f'Requires-Dist: {name}=={version}\n' for name, version in VERSIONS.items()))
    write_wheel(output, 'qingying-runtime', '1.0.0', 'py3-none-any', info,
                {f'{info}/METADATA': metadata.encode()}, pure=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apk')
    parser.add_argument('--output', default=str(ROOT / 'vendor/runtime-wheels'))
    args = parser.parse_args()
    restore(args.apk, args.output)
