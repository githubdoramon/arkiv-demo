"""Build two linux/amd64 Tiramisu images and export a server-ready bundle."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sqlite3
import stat
import tarfile
import zipfile

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-build', action='store_true', help='Package already-built images')
    parser.add_argument('--output', type=Path, default=REPO / '.runtime/releases/sidequest-tiramisu-amd64')
    parser.add_argument('--format', choices=['zip', 'tar.gz'], default='zip', help='Release archive format (default: zip)')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    compose = REPO / 'deploy/compose.yaml'
    if not args.skip_build:
        build_env = dict(os.environ)
        for variable, name in [('ARKIV_JS_CONTEXT', 'arkiv-sdk-js'), ('ARKIV_PYTHON_CONTEXT', 'arkiv-python-sdk')]:
            if variable not in build_env:
                candidates = [REPO.parent / name, REPO.parent.parent / name]
                checkout = next((path for path in candidates if (path / ('package.json' if name.endswith('-js') else 'pyproject.toml')).is_file()), None)
                if checkout is None:
                    raise SystemExit(f'Missing sibling {name}; set {variable} to its checkout path.')
                build_env[variable] = str(checkout.resolve())
        subprocess.run(['docker', 'compose', '-f', str(compose), 'build'], cwd=REPO, env=build_env, check=True)
    images = ['sidequest-review:tiramisu', 'sidequest-portfolio:tiramisu']
    inspected = json.loads(subprocess.check_output(['docker', 'image', 'inspect', *images], text=True))
    if any(image['Os'] != 'linux' or image['Architecture'] != 'amd64' for image in inspected):
        raise SystemExit('Release images must both be Linux/amd64.')
    print('Exporting both verified Linux/amd64 images…', flush=True)
    # Write atomically so a failed export cannot look like a complete package.
    temporary = output / 'images.tar.gz.partial'
    with temporary.open('wb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', compresslevel=3) as archive:
            process = subprocess.Popen(['docker', 'image', 'save', *images], stdout=subprocess.PIPE)
            try:
                shutil.copyfileobj(process.stdout, archive)
            finally:
                process.stdout.close()
            if process.wait() != 0:
                raise SystemExit('Docker image export failed.')
    temporary.replace(output / 'images.tar.gz')
    # Strip build configuration: the server needs only Docker and these two images.
    import_text = compose.read_text()
    lines = import_text.splitlines()
    clean = []; skip = False
    for line in lines:
        if line.startswith('    build:'):
            skip = True; continue
        if skip and line and not line.startswith('      '):
            skip = False
        if not skip:
            clean.append(line)
    (output / 'compose.yaml').write_text('\n'.join(clean)+'\n')
    shutil.copyfile(REPO / 'deploy/.env.example', output / '.env.example')
    shutil.copyfile(REPO / 'deploy/README.md', output / 'README.md')
    (output / 'secrets').mkdir(exist_ok=True)
    ledger = REPO / '.runtime/tiramisu/renewal.sqlite3'
    if ledger.is_file():
        (output / 'state').mkdir(exist_ok=True)
        # Snapshot a live SQLite ledger consistently, without changing its source.
        with sqlite3.connect(ledger.as_uri()+'?mode=ro', uri=True) as source:
            with sqlite3.connect(output / 'state/renewal.sqlite3') as target:
                source.backup(target)
    metadata = {'network':'tiramisu','chain_id':7738577,'platform':'linux/amd64',
                'review_url':'https://sidequest.appcalipse.com/','portfolio_url':'https://afterword.appcalipse.com/','images':images,
                'built_at':datetime.now(timezone.utc).isoformat(),
                'image_ids':{name:image['Id'] for name,image in zip(images,inspected)}}
    (output / 'build.json').write_text(json.dumps(metadata, indent=2)+'\n')
    bundle = output.parent / (output.name+'.'+args.format)
    temporary_bundle = Path(str(bundle)+'.partial')
    # Explicit allowlist: a reused output folder may contain private runtime files.
    members = ['images.tar.gz','compose.yaml','.env.example','README.md','build.json']
    if ledger.is_file():
        members.append('state/renewal.sqlite3')
    if args.format == 'zip':
        with zipfile.ZipFile(temporary_bundle, 'w', allowZip64=True) as archive:
            for name in members:
                archive.write(output/name, arcname=output.name+'/'+name,
                              compress_type=zipfile.ZIP_STORED if name=='images.tar.gz' else zipfile.ZIP_DEFLATED)
            info=zipfile.ZipInfo(output.name+'/secrets/')
            info.create_system=3
            info.external_attr=(stat.S_IFDIR | 0o700) << 16
            archive.writestr(info,b'')
    else:
        with tarfile.open(temporary_bundle, 'w:gz') as archive:
            for name in members:
                archive.add(output/name, arcname=output.name+'/'+name)
            info=tarfile.TarInfo(output.name+'/secrets');info.type=tarfile.DIRTYPE;info.mode=0o700
            archive.addfile(info)
    temporary_bundle.replace(bundle)
    with bundle.open('rb') as packaged:
        digest=hashlib.file_digest(packaged,'sha256').hexdigest()
    Path(str(bundle)+'.sha256').write_text(digest+'  '+bundle.name+'\n')
    print(f'Package: {bundle}\nSHA-256: {digest}\nImages and public configuration only; private keys are excluded.')


if __name__ == '__main__':
    main()
