#!/bin/sh
# GitHub main is the trust boundary; this is not a pinned release/runtime installer.
set -eu
project=$PWD
source=
while [ "$#" -gt 0 ]; do
  case "$1" in
    --project|--source)
      [ "$#" -ge 2 ] || { printf '%s\n' "Missing value for $1" >&2; exit 2; }
      case "$1" in --project) project=$2 ;; --source) source=$2 ;; esac
      shift 2 ;;
    --help) printf '%s\n' 'Usage: sh install.sh [--source CHECKOUT] [--project EXISTING_PROJECT]'; exit 0 ;;
    *) printf '%s\n' "Unknown argument: $1" >&2; exit 2 ;;
  esac
done
command -v python3 >/dev/null 2>&1 || { printf '%s\n' 'Python 3.10+ must already be installed.' >&2; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || { printf '%s\n' 'Python 3.10+ is required.' >&2; exit 1; }
[ -d "$project" ] || { printf '%s\n' 'Project must be an existing directory.' >&2; exit 1; }
if [ -n "$source" ]; then
  [ -f "$source/install.py" ] || { printf '%s\n' 'Local checkout is missing install.py.' >&2; exit 1; }
  exec python3 "$source/install.py" --project "$project"
fi
command -v curl >/dev/null 2>&1 || { printf '%s\n' 'curl must already be installed for remote use.' >&2; exit 1; }
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
trap 'exit 1' HUP INT TERM
curl -fsSL --connect-timeout 10 --max-time 60 --max-filesize 10485760 \
  https://codeload.github.com/darwinlatorre/ssd-workflow/tar.gz/refs/heads/main \
  -o "$stage/source.tar.gz" || { printf '%s\n' 'GitHub source download failed; project unchanged.' >&2; exit 1; }
python3 - "$stage/source.tar.gz" "$stage/source" <<'PY'
import gzip, pathlib, sys, tarfile
try:
    root = pathlib.Path(sys.argv[2])
    unpacked = root.parent / 'bounded-source.tar'
    total = 0
    with gzip.open(sys.argv[1], 'rb') as compressed, unpacked.open('xb') as dst:
        while True:
            block = compressed.read(65536)
            if not block:
                break
            total += len(block)
            if total > 33554432:
                raise ValueError('source archive exceeds limits')
            dst.write(block)
    with tarfile.open(unpacked, 'r:') as archive:
        members = archive.getmembers()
        if len(members) > 2000 or sum(m.size for m in members) > 33554432:
            raise ValueError('source archive exceeds limits')
        names = {}
        for member in members:
            name = member.name.rstrip('/') if member.isdir() else member.name
            path = pathlib.PurePosixPath(name)
            if (not name or '\\' in name or any(ord(c) < 32 for c in name) or path.is_absolute()
                or '..' in path.parts or path.as_posix() != name or path.parts[0] != 'ssd-workflow-main'
                or len(path.parts) == 1 and not member.isdir()
                or name in names or not (member.isfile() or member.isdir())):
                raise ValueError('unsafe/unsupported source archive member')
            names[name] = member
        for name, member in names.items():
            if any(str(parent) in names and not names[str(parent)].isdir() for parent in pathlib.PurePosixPath(name).parents):
                raise ValueError('archive parent/file collision')
        root.mkdir()
        for name, member in names.items():
            destination = root / name
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as src, destination.open('xb') as dst:
                    import shutil
                    shutil.copyfileobj(src, dst)
except (OSError, EOFError, ValueError, tarfile.TarError):
    print('Source archive refused; project unchanged.', file=sys.stderr)
    sys.exit(1)
PY
python3 "$stage/source/ssd-workflow-main/install.py" --project "$project"
