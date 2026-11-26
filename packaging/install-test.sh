#!/usr/bin/env bash
# Install a built package on a clean system and use it for real: transcribe speech made with
# espeak-ng (the tiny model is downloaded from Hugging Face), and check record and transcribir.
# record comes from its own package, ross-record: its newest release is installed alongside.
# Runs as root inside the distro's container:
#   install-test.sh <deb|rpm|arch> <package-file> <version>
set -euo pipefail
kind=$1 pkg=$(realpath "$2") version=$3

# The newest ross-record package of the given type (deb, rpm or pkg.tar.zst), from its GitHub release.
fetch_record() {
  local url
  url=$(curl -fsSL https://api.github.com/repos/rossmelabasto/ross_record/releases/latest \
        | grep -o '"browser_download_url": *"[^"]*\.'"$1"'"' | sed 's/.*"\(http[^"]*\)"$/\1/' | head -1)
  [ -n "$url" ] || { echo "no ross-record .$1 in its latest release" >&2; exit 1; }
  curl -fsSL -o "/tmp/ross-record.$1" "$url"
  echo "/tmp/ross-record.$1"
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
grep -qi 'hello' /tmp/out.txt
grep -qi 'test' /tmp/out.txt

echo "Install test passed on $kind"
