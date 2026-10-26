# termux-apt-repo

APT repository for my Termux packages, published on GitHub Pages.

| Package | Description | Architectures |
|---------|-------------|---------------|
| `opencode2` | OpenCode AI coding assistant for Android/Termux | `aarch64` |
| `termux-dm` | Termux display manager | `all` |
| `termux-settings` | Keyboard-driven TUI to change Termux colors, app theme, and fonts | `aarch64` |

## Install / update (Termux)

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

## Files

| Path | Purpose |
|------|---------|
| `dists/stable/InRelease` | signed Release file (APT entry point) |
| `dists/stable/main/binary-aarch64/Packages(.gz/.bz2)` | `aarch64` package metadata |
| `dists/stable/main/binary-aarch64/Release` | per-architecture Release file |
| `dists/stable/main/Contents-aarch64(.gz)` | file index |
| `pool/main/...` | hosted `.deb` files (Debian pool layout) |
| `key.gpg` | public key that signs `InRelease` |

## Repository maintainers

Rebuild and publish after a new `.deb` is dropped into `debs/` (GitHub Pages
serves this `docs/` directory of the `main` branch as the site root):

```sh
./termux-apt-repo debs docs stable main --sign
gpg --export 476FC230ECBBFDF0 > docs/key.gpg
# commit docs/ on the main branch and push.
# (Pages source config: branch main, path /docs)
```
