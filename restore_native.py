"""Restore bundled engines/models from the official Windows release ZIP."""
import argparse
from pathlib import Path, PurePosixPath
import shutil
import zipfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('release_zip', type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parent
count = 0
with zipfile.ZipFile(args.release_zip) as archive:
    for member in archive.infolist():
        parts = PurePosixPath(member.filename).parts
        if len(parts) < 4 or parts[:3] != ('Qingying-2.5', '_internal', 'native') or member.is_dir():
            continue
        destination = (root / 'native' / Path(*parts[3:])).resolve()
        if not destination.is_relative_to(root / 'native'):
            raise ValueError('Invalid archive path')
        destination.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(member) as source, destination.open('wb') as target:
            shutil.copyfileobj(source, target)
        count += 1
if not count:
    raise SystemExit('No bundled native files found; select the official Qingying 2.5 Windows ZIP.')
print(f'Restored {count} native engine/model files.')
