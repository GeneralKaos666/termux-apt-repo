# termux-apt-repo

A standalone APT repository for my Termux packages, published on GitHub Pages.

| Package | Description | Architectures |
|---------|-------------|---------------|
| `opencode2` | OpenCode CLI for Termux | `aarch64` |
| `Termux-dm` / `termux-dm` / `tdm` | Termux display manager | `all` |

## Quick start (Termux)

```sh
# 1. trust the repository signing key
mkdir -p "$PREFIX/etc/apt/keyrings"
curl -fsSL https://generalkaos666.github.io/termux-apt-repo/key.gpg \
     -o "$PREFIX/etc/apt/keyrings/termux-apt-repo.gpg"

# 2. add the repository
echo "deb [signed-by=$PREFIX/etc/apt/keyrings/termux-apt-repo.gpg] https://generalkaos666.github.io/termux-apt-repo termux main" \
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
| `docs/dists/termux/InRelease` | signed Release file (APT entry point) |
| `docs/dists/termux/main/binary-*/Packages(.xz)` | package metadata per architecture |
| `docs/key.gpg` | public key that signs `InRelease` |
| `debs/` | source `.deb` files used to build the repository (gitignored) |
| `termux-apt-repo` | CLI script that renders the repository tree |

## Maintaining

Drop a new `.deb` into `debs/`, rebuild the metadata, re-export the key, and
push. GitHub Pages serves `docs/` from the `main` branch as the site root.

```sh
./termux-apt-repo debs docs termux main --sign --strip-debs
gpg --export 476FC230ECBBFDF0 > docs/key.gpg
git add docs/
git commit -m "chore: rebuild apt repository"
git push
```

Notes:

- `--strip-debs` keeps the `.deb` files out of the published tree (metadata
  only). Use it unless the packages are small enough to host directly.
- `--use-hard-links` does not work on Android; use it only on a real Linux
  filesystem.
- The `.deb` files must already be present in `debs/` before rebuilding.
