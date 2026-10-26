#!/bin/bash
# Build one package with the termux-packages harness and collect the .deb.
#
# Requires:
#   TERMUX_PACKAGES_DIR - path to a termux/termux-packages checkout (the build
#                         harness; its packages/<pkg>/ is overwritten with this
#                         repo's recipe).
#   TARGET_ARCH         - architecture to build (default: aarch64).
#
# Usage: build-package.sh <pkg>
set -euo pipefail

pkg="${1:?usage: build-package.sh <pkg>}"
tp="${TERMUX_PACKAGES_DIR:?TERMUX_PACKAGES_DIR is required}"
arch="${TARGET_ARCH:-aarch64}"

repo_root="$(cd "$(dirname "$0")/.." && pwd)"

# Overlay this repo's recipe (build.sh + vendored debscripts/files) into the
# harness, replacing any same-named recipe that may exist upstream.
rm -rf "$tp/packages/$pkg"
mkdir -p "$tp/packages/$pkg"
cp -R "$repo_root/packages/$pkg/." "$tp/packages/$pkg/"

# Build inside the official package-builder container.
(
  cd "$tp"
  ./scripts/run-docker.sh ./build-package.sh -a "$arch" "$pkg"
)

# Collect the built .deb into debs/.
mkdir -p "$repo_root/debs"
if ls "$tp/output/"*.deb >/dev/null 2>&1; then
  cp "$tp/output/"*.deb "$repo_root/debs/"
else
  echo "build-package.sh: no .deb produced for $pkg" >&2
  exit 1
fi
