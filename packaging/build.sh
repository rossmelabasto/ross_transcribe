#!/usr/bin/env bash
# Build the tree the deb, rpm and pacman packages install, then the packages themselves.
#
#   /opt/ross-transcribe/python   a portable CPython (python-build-standalone) with transcribe and
#                                 its dependencies, so it doesn't depend on the distro's Python
#   /usr/bin/transcribe           the CLI
#   /usr/bin/transcribir          the same with the interface and audio in Spanish by default
#   /usr/bin/record               record from the microphone, then offer to transcribe
#
#   packaging/build.sh <version> <out-dir>      (runs on Linux x86_64; needs curl and nfpm)
set -euo pipefail

version=${1:?version}
out=$(realpath -m "${2:?out-dir}")
root=$(cd "$(dirname "$0")/.." && pwd)

# Pinned and checked: the release of python-build-standalone and its published SHA-256.
PBS_TAG=20261026
PBS_FILE="cpython-3.12.16+${PBS_TAG}-x86_64-unknown-linux-gnu-install_only.tar.gz"
PBS_SHA256=6a79e922e50006b601f29e688407659da1c2b86ebcd4e9c7254cf234be8b89de

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
stage="$work/stage"
prefix="$stage/opt/ross-transcribe"
mkdir -p "$prefix" "$stage/usr/bin" "$out"

echo "==> portable Python ($PBS_FILE)"
curl -fsSL -o "$work/python.tar.gz" \
  "https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/${PBS_FILE//+/%2B}"
echo "$PBS_SHA256  $work/python.tar.gz" | sha256sum -c -
tar xzf "$work/python.tar.gz" -C "$prefix"   # -> $prefix/python
py="$prefix/python/bin/python3"

echo "==> transcribe $version and its dependencies"
"$py" -m pip install --quiet --no-cache-dir --disable-pip-version-check "$root"
installed=$("$py" -c 'import ross_transcribe; print(ross_transcribe.__version__)')
[ "$installed" = "$version" ] || { echo "version mismatch: package says $installed, building $version" >&2; exit 1; }

echo "==> trimming"
site=$("$py" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
# faster-whisper depends on PyAV (decoding, ~130 MB with its own FFmpeg) and onnxruntime (the
# optional voice filter, ~65 MB). transcribe decodes with the system ffmpeg and doesn't use the
# filter, and both are only touched inside functions it never calls, so they stay out. faster-
# whisper still imports av when it loads: a stand-in module answers that import.
"$py" -m pip uninstall --quiet -y av onnxruntime coloredlogs humanfriendly flatbuffers protobuf sympy mpmath 2>/dev/null || true
mkdir -p "$site/av"
cat > "$site/av/__init__.py" <<'PY'
"""Stand-in for PyAV in the ross-transcribe packages: transcribe decodes audio with ffmpeg."""


def __getattr__(name):
    raise ImportError("PyAV isn't included in this build of transcribe (it decodes with ffmpeg)")
PY
"$py" -I -c 'import faster_whisper, ross_transcribe.engine' || { echo "imports broke after trimming" >&2; exit 1; }
# Nothing at runtime needs pip, the test suites or the build headers.
"$py" -m pip uninstall --quiet -y pip
rm -rf "$prefix/python/include" "$prefix/python/share" \
  "$prefix"/python/lib/python3.12/{test,idlelib,tkinter,turtledemo,ensurepip} \
  "$prefix"/python/lib/{tcl,tk,itcl,thread}* 2>/dev/null || true
find "$prefix" -depth -type d \( -name tests -o -name test \) -path '*site-packages*' -exec rm -rf {} +
find "$prefix" -name '__pycache__' -type d -prune -exec rm -rf {} +
# Compile once at build time: /opt isn't writable for users, so Python couldn't cache it later.
"$py" -m compileall -q -j 0 "$prefix/python/lib" >/dev/null || true
du -sh "$prefix"
du -sh "$site"/* | sort -h | tail -8

echo "==> commands"
cat > "$stage/usr/bin/transcribe" <<'EOF'
#!/bin/sh
exec /opt/ross-transcribe/python/bin/python3 -I -m ross_transcribe "$@"
EOF
cat > "$stage/usr/bin/transcribir" <<'EOF'
#!/bin/sh
# transcribe with the interface and the audio in Spanish by default; -l en / -l auto changes it.
TRANSCRIBE_UI_LANG="${TRANSCRIBE_UI_LANG:-es}" TRANSCRIBE_LANG="${TRANSCRIBE_LANG:-es}" exec /usr/bin/transcribe "$@"
EOF
install -m755 "$root/bin/record" "$stage/usr/bin/record"
chmod 755 "$stage/usr/bin/"*
install -Dm644 "$root/LICENSE" "$stage/usr/share/licenses/ross-transcribe/LICENSE"
install -Dm644 "$root/README.md" "$stage/usr/share/doc/ross-transcribe/README.md"

echo "==> packages"
for packager in deb rpm archlinux; do
  # Arch names prebuilt packages -bin.
  name=ross-transcribe
  [ "$packager" = archlinux ] && name=ross-transcribe-bin
  # nfpm doesn't expand variables in file paths: fill the config in first.
  VERSION="$version" STAGE="$stage" PKG_NAME="$name" \
    envsubst '${VERSION} ${STAGE} ${PKG_NAME}' < "$root/packaging/nfpm.yaml" > "$work/nfpm.yaml"
  nfpm package --config "$work/nfpm.yaml" --packager "$packager" --target "$out/"
done
ls -la "$out"
