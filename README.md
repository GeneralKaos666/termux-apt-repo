# termux-apt-repo

A standalone APT repository for my Termux packages, published on GitHub Pages.

| Package | Description | Architectures |
|---------|-------------|---------------|
| `flutter` | Flutter SDK (stable) | `aarch64` |
| `opencode2` | OpenCode AI coding assistant for Android/Termux | `aarch64` |
| `termux-dm` | Termux display manager | `aarch64` |
| `termux-settings` | Keyboard-driven TUI to change Termux colors, app theme, and fonts | `aarch64` |

## Quick start (Termux)

```sh
# 1. trust the repository signing key
mkdir -p "$PREFIX/etc/apt/keyrings"
curl -fsSL https://generalkaos666.github.io/termux-apt-repo/key.gpg \
     -o "$PREFIX/etc/apt/keyrings/termux-apt-repo.gpg"

# 2. add the repository
echo "deb [signed-by=$PREFIX/etc/apt/keyrings/termux-apt-repo.gpg] https://generalkaos666.github.io/termux-apt-repo stable main" \
     > "$PREFIX/etc/apt/sources.list.d/termux-apt-repo.list"

# 3. update and install
apt update
apt install opencode2 termux-dm
```

## Verify the key

```
fingerprint: 1DED 0840 4574 B867 B058  A7BB 476F C230 ECBB FDF0
```

## Repository layout

| Path | Purpose |
|------|---------|
| `repo.json` | repository manifest (name, distribution, component, url) |
| `packages/<name>/build.sh` | Termux-style build recipe per package (reference copy) |
| `docs/` | GitHub Pages site root (served as the APT repo) |
| `docs/dists/stable/InRelease` | signed Release file (APT entry point) |
| `docs/dists/stable/main/binary-<arch>/Packages(.gz/.bz2)` | package metadata per architecture |
| `docs/dists/stable/main/binary-<arch>/Release` | per-architecture Release file |
| `docs/dists/stable/main/Contents-<arch>(.gz)` | file index per architecture |
| `docs/pool/main/...` | hosted `.deb` files (Debian pool layout) |
| `docs/key.gpg` | public key that signs `InRelease` |
| `debs/` | built `.deb` files used to build the repository (gitignored) |
| `termux-apt-repo` | CLI script that renders the repository tree |

## Building a package (automatic)

Packages are built and published automatically by the
`.github/workflows/sync.yml` workflow. Each package's recipe lives under
`packages/<name>/` and is the authoritative source. The workflow watches one
upstream repository per package; when a newer release/tag lands it bumps the
recipe, rebuilds the `.deb` with the termux-packages harness
(`ghcr.io/termux/package-builder`), re-signs, and pushes.

It runs on a schedule (hourly), on push to `packages/**` / `sync.json` /
`scripts/`, and manually (the `Sync packages` workflow in the Actions tab).

| Package | Upstream (source of "latest") | Detect via |
|---------|-------------------------------|------------|
| `flutter` | `GeneralKaos666/flutter-for-termux` | latest release (shim; pulls its payload) |
| `opencode2` | `GeneralKaos666/opencode-android` | latest release |
| `termux-dm` | `GeneralKaos666/termux-display-manager-repo` | latest `master` commit |
| `termux-settings` | `GeneralKaos666/termux-settings` | latest tag |

## Required secrets

Set these in **Settings → Secrets and variables → Actions**:

| Secret | Value |
|--------|-------|
| `GPG_PRIVATE_KEY` | `gpg --armor --export-secret-keys 476FC230ECBBFDF0` |
| `GPG_PASSPHRASE` | the key's passphrase |

The push-back to `main` uses the built-in `GITHUB_TOKEN` (no PAT required).

## Manual rebuild

Trigger the `Sync packages` workflow from the Actions tab (optionally pass a
space-separated package list). To change the build harness, override the
`termux_packages_ref` input (pinned to a known-good `termux/termux-packages`
commit; bump it when recipes need a newer harness).

To rebuild the apt metadata locally (e.g. after dropping a `.deb` in `debs/`):

```sh
# place the built .deb(s) into debs/ first, then:
./termux-apt-repo debs docs stable main --sign
gpg --export 476FC230ECBBFDF0 > docs/key.gpg
git add docs/
git commit -m "chore: rebuild apt repository"
git push
```

Notes:

- `.deb` files are copied into `docs/pool/` (Debian pool layout) and served
  directly by GitHub Pages, so the repository is self-contained.
- `--strip-debs` produces a metadata-only repository; combine it with
  `--base-url` to point `Filename` at an external host if you strip the debs.
- `--use-hard-links` does not work on Android; use it only on a real Linux
  filesystem.
- The `.deb` files must already be present in `debs/` before rebuilding.
