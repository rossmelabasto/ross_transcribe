#!/usr/bin/env bash
# Install a built package on a clean system and use it for real: transcribe speech made with
# espeak-ng (the tiny model is downloaded from Hugging Face), and check record and transcribir.
# Runs as root inside the distro's container:
#   install-test.sh <deb|rpm|arch> <package-file> <version>
set -euo pipefail
kind=$1 pkg=$(realpath "$2") version=$3

case "$kind" in
  deb)
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq espeak-ng >/dev/null
    apt-get install -y -qq "$pkg" >/dev/null
    ;;
  rpm)
    dnf install -y -q espeak-ng
    dnf install -y -q "$pkg"
    ;;
  arch)
    pacman-key --init >/dev/null 2>&1
    pacman -Syu --noconfirm --needed espeak-ng >/dev/null
    pacman -U --noconfirm "$pkg" >/dev/null
    ;;
esac

echo "--- versions"
transcribe --version | tee /tmp/version
grep -q "$version" /tmp/version
command -v ffmpeg sox record transcribir

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
