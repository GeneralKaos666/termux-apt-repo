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

# Collect the built .deb into debs/. Search recursively: the harness may place
# the .deb under output/ directly, or in a nested directory for some packages.
mkdir -p "$repo_root/debs"

mapfile -t found < <(find "$tp" -type f -name "${pkg}_*.deb" 2>/dev/null)
if [ "${#found[@]}" -eq 0 ]; then
  mapfile -t found < <(find "$tp" -type f -name "*.deb" 2>/dev/null)
fi

if [ "${#found[@]}" -eq 0 ]; then
  echo "build-package.sh: no .deb produced for $pkg" >&2
  echo "build-package.sh: output dir contents:" >&2
  find "$tp/output" -maxdepth 3 2>/dev/null | sed 's/^/    /' >&2 || true
  exit 1
fi

for d in "${found[@]}"; do
  echo "build-package.sh: collected $d"
  cp "$d" "$repo_root/debs/"
done
