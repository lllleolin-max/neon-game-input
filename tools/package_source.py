"""Create a shareable source ZIP from explicit public directories, never the venv."""
import hashlib
from pathlib import Path
import tomllib
import zipfile


def main():
    root = Path(__file__).resolve().parents[1]
    version = tomllib.loads((root/'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    output = root/'dist'
    output.mkdir(exist_ok=True)
    paths = []
    for directory in ('src/neon_game_input', 'tests', 'docs', 'examples', 'tools', 'LICENSES', '.github'):
        paths.extend(p for p in (root/directory).rglob('*') if p.is_file()
                     and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo'))
    names = ('pyproject.toml', 'MANIFEST.in', 'README.md', 'README.en.md', 'LICENSE', 'THIRD_PARTY.md',
             'CHANGELOG.md', 'CONTRIBUTING.md', 'AGENTS.md', '.gitignore',
             'requirements-windows-py312.lock.txt')
    paths.extend(root/name for name in names)
    paths.extend(root.glob('*.cmd'))
    prefix = f'neon-game-input-{version}'
    target = output/f'{prefix}-source.zip'
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(paths)):
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError(f'Unexpected external file: {path.name}')
            archive.write(path, f'{prefix}/{path.relative_to(root).as_posix()}')
    sums = []
    for artifact in sorted(output.iterdir()):
        if artifact.is_file() and artifact.suffix in ('.zip', '.whl', '.gz'):
            sums.append(f'{hashlib.sha256(artifact.read_bytes()).hexdigest()}  {artifact.name}')
    (output/'SHA256SUMS.txt').write_text('\n'.join(sums)+'\n', encoding='utf-8')
    print(f'{target.name}: {target.stat().st_size:,} bytes, {len(set(paths))} source files')


if __name__ == '__main__':
    main()
