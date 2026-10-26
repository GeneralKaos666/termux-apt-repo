# termux-apt-repo

A standalone APT repository for my Termux packages, published on GitHub Pages.

| Package | Description | Architectures |
|---------|-------------|---------------|
| `opencode2` | OpenCode AI coding assistant for Android/Termux | `aarch64` |
| `termux-dm` | Termux display manager | `all` |
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
| `docs/` | GitHub Pages site root (served as the APT repo) |
| `docs/dists/stable/InRelease` | signed Release file (APT entry point) |
| `docs/dists/stable/main/binary-<arch>/Packages(.gz/.bz2)` | package metadata per architecture |
| `docs/dists/stable/main/binary-<arch>/Release` | per-architecture Release file |
| `docs/dists/stable/main/Contents-<arch>(.gz)` | file index per architecture |
| `docs/pool/main/...` | hosted `.deb` files (Debian pool layout) |
| `docs/key.gpg` | public key that signs `InRelease` |
| `debs/` | source `.deb` files used to build the repository (gitignored) |
| `termux-apt-repo` | CLI script that renders the repository tree |

## Maintaining

Drop a new `.deb` into `debs/`, rebuild the metadata, re-export the key, and
push. GitHub Pages serves `docs/` from the `main` branch as the site root.

```sh
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
