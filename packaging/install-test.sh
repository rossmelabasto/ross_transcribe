#!/usr/bin/env bash
# Install a built package on a clean system and use it for real: transcribe speech made with
# espeak-ng (the tiny model is downloaded from Hugging Face), and check record and transcribir.
# record comes from its own package, ross-record: its newest release is installed alongside.
# Runs as root inside the distro's container:
#   install-test.sh <deb|rpm|arch> <package-file> <version>
set -euo pipefail
kind=$1 pkg=$(realpath "$2") version=$3

# The newest ross-record package of the given type (deb, rpm or pkg.tar.zst), from its GitHub release.
# The version comes from the redirect of releases/latest (no API call: the API rate-limits shared CI runners).
fetch_record() {
  local tag v file
  tag=$(curl -fsSI https://github.com/rossmelabasto/ross_record/releases/latest | tr -d '\r' \
        | sed -n 's#^[Ll]ocation: .*/tag/\(v[0-9.]*\)$#\1#p' | tail -1)
  [ -n "$tag" ] || { echo "can't find the latest ross_record release" >&2; exit 1; }
  v=${tag#v}
  case "$1" in
    deb) file="ross-record_${v}-1_all.deb" ;;
    rpm) file="ross-record-${v}-1.noarch.rpm" ;;
    pkg.tar.zst) file="ross-record-${v}-1-any.pkg.tar.zst" ;;
  esac
  curl -fsSL -o "/tmp/$file" "https://github.com/rossmelabasto/ross_record/releases/download/$tag/$file"
  echo "/tmp/$file"
}

case "$kind" in
  deb)
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq espeak-ng curl ca-certificates >/dev/null
    rec=$(fetch_record deb)
    apt-get install -y -qq "$rec" "$pkg" >/dev/null
    ;;
  rpm)
    dnf install -y -q espeak-ng curl
    rec=$(fetch_record rpm)
    dnf install -y -q "$rec" "$pkg"
    ;;
  arch)
    pacman-key --init >/dev/null 2>&1
    pacman -Syu --noconfirm --needed espeak-ng curl >/dev/null
    rec=$(fetch_record pkg.tar.zst)
    pacman -U --noconfirm "$rec" "$pkg" >/dev/null
    ;;
esac

echo "--- versions"
transcribe --version | tee /tmp/version
grep -q "$version" /tmp/version
command -v ffmpeg sox record transcribir
record -V

echo "--- help in English and Spanish"
LANG=C.UTF-8 transcribe --help | head -3
transcribir --help | grep -qi 'transcrib'
record -h | head -2

echo "--- a real transcription"
espeak-ng -v en -s 140 -w /tmp/speech.wav "Hello world. This is a quick transcription test."
LANG=C.UTF-8 transcribe /tmp/speech.wav -m tiny -l en --device cpu | tee /tmp/out.txt
# The tiny model sometimes hears "Hello" as something else: check two words it always gets.
grep -qi 'world' /tmp/out.txt
grep -qi 'test' /tmp/out.txt

echo "Install test passed on $kind"
