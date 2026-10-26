"""Build two linux/amd64 Tiramisu images and export a server-ready bundle."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-build', action='store_true', help='Package already-built images')
    parser.add_argument('--output', type=Path, default=REPO / '.runtime/releases/sidequest-tiramisu-amd64')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    compose = REPO / 'deploy/compose.yaml'
    if not args.skip_build:
        subprocess.run(['docker', 'compose', '-f', str(compose), 'build'], cwd=REPO, check=True)
    images = ['sidequest-review:tiramisu', 'sidequest-portfolio:tiramisu']
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
        shutil.copyfile(ledger, output / 'state/renewal.sqlite3')
    metadata = {'network':'tiramisu','chain_id':7738577,'platform':'linux/amd64',
                'review_url':'https://sidequest.appcalipse.com/','portfolio_url':'https://portfolios.appcalipse.com/','images':images}
    (output / 'build.json').write_text(json.dumps(metadata, indent=2)+'\n')
    bundle = output.parent / (output.name+'.tar.gz')
    with tarfile.open(bundle, 'w:gz') as archive:
        for name in ['images.tar.gz','compose.yaml','.env.example','README.md','build.json']:
            archive.add(output / name, arcname=output.name+'/'+name)
        if ledger.is_file():
            archive.add(output / 'state/renewal.sqlite3', arcname=output.name+'/state/renewal.sqlite3')
        # Never include runtime secrets, even if this output directory was reused.
        info=tarfile.TarInfo(output.name+'/secrets');info.type=tarfile.DIRTYPE;info.mode=0o700
        archive.addfile(info)
    print(f'Package: {bundle}\nImages and public configuration only; private keys are excluded.')


if __name__ == '__main__':
    main()
