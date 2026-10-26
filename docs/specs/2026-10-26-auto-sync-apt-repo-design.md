# Auto-Sync APT Repository — Design

Date: 2026-10-26
Status: Draft (awaiting review)

## 1. Goal

Keep this APT repository's packages automatically up to date. When a new
release/tag lands in a package's upstream repository, this repo detects it,
bumps the recipe, rebuilds the `.deb`, re-signs the repo, and publishes — with
no manual download/copy/push. The user's Termux device then picks the update up
with a normal `apt update && apt install`.

## 2. Current state

- `docs/` is the GitHub Pages site root (served from `main`).
- `packages/<name>/build.sh` are Termux-style recipes (currently reference
  copies; they become authoritative under this design).
- `termux-apt-repo` (Python) rebuilds the APT metadata from `.deb` files in
  `debs/` into `docs/`, and can sign `InRelease` with GPG.
- Signing key fingerprint: `1DED 0840 4574 B867 B058 A7BB 476F C230 ECBB FDF0`.
- Today the maintainer downloads CI-built `.deb`s by hand, drops them in
  `debs/`, rebuilds, signs, and pushes.

## 3. Confirmed decisions

| Decision | Choice |
|---|---|
| Build location | In this repo's CI (GitHub Actions) |
| Recipes | Authoritative, live in `packages/<name>/build.sh` here |
| Trigger | Scheduled cron + `workflow_dispatch` + push to `packages/**` |
| Signing | GPG private key + passphrase stored as GitHub Actions secrets |
| Architectures | `aarch64` only |
| Flutter | Rebuild the **shim** only; never compile the SDK here |
| opencode2 | Leave the recipe description unchanged |

## 4. Architecture overview

One scheduled/sync workflow watches four upstream repositories, one per
package. For each package that has a newer version than what is published, it
updates that package's recipe, rebuilds it with the termux-packages build
harness, then regenerates + signs + publishes the APT metadata. Packages are
independent jobs, so a slow or failing package never blocks the others.

```
  upstream release/tag
        │ (GitHub API: latest release / latest tag)
        ▼
  compare vs published version
        │
        ├─ unchanged ───────────────▶ skip (no commit)
        │
        └─ newer ─▶ bump recipe ─▶ build .deb ─▶ rebuild metadata
                                              ─▶ sign InRelease ─▶ commit + push
```

## 5. Components

### 5.1 `sync.json` (config)

Declares, per package: the upstream repo, how to detect "latest"
(`latest-release` vs `latest-tag`), and the recipe fields that must be bumped
for a version change. Kept separate from `repo.json` (which describes the apt
repo itself).

### 5.2 `.github/workflows/sync.yml`

- Triggers: `schedule` (cron), `workflow_dispatch`, `push` with
  `paths: ['packages/**', 'sync.json']`.
- Permissions: `contents: write` (to commit `docs/` and updated recipes).
- A matrix job, one entry per package, each running the build harness
  (`ghcr.io/termux/package-builder`).
- A final "publish" job that runs only after at least one package changed,
  regenerates `docs/`, signs, and pushes.

### 5.3 `scripts/sync.sh`

The sync logic, called per package (and a collect step at the end):

1. Query the upstream repo's latest release/tag via the GitHub API.
2. Compare to the currently-published version (read from
   `docs/dists/stable/main/binary-aarch64/Packages`, falling back to the
   recipe's `TERMUX_PKG_VERSION`).
3. If unchanged, exit without changes.
4. If newer, bump the recipe's version fields and download URLs, then build
   via `build-package.sh`.
5. Report the build output path back to the workflow.

### 5.4 Secrets

- `GPG_PRIVATE_KEY` — exported armored private key (ASCII).
- `GPG_PASSPHRASE` — key passphrase.
- Push-back uses the built-in `GITHUB_TOKEN` (its pushes do not re-trigger
  workflows, which prevents sync loops).

## 6. Data flow

1. Workflow fires (cron / manual / push).
2. Each package job runs `scripts/sync.sh`, which detects a newer upstream
   version, bumps the recipe, and builds the `.deb` into `debs/`.
3. If any package changed, the publish job runs
   `./termux-apt-repo debs docs stable main --sign`, then `gpg --export` to
   refresh `docs/key.gpg`, commits `docs/` and the updated recipes, and pushes.
4. GitHub Pages serves the updated `docs/`.

## 7. Per-package upstream mapping

| Package | Upstream repo | Detect via | What changes on bump |
|---|---|---|---|
| `flutter` | `GeneralKaos666/flutter-for-termux` | latest release | `build.sh` `TERMUX_PKG_VERSION`; `postinst`/`preinst`/`postrm` `VERSION`, `RELEASE_BASE`, `DEB` |
| `opencode2` | `GeneralKaos666/opencode-android` | latest release | `build.sh` `TERMUX_PKG_VERSION`, `TERMUX_PKG_SRCURL`, download URL in `termux_step_make_install` |
| `termux-dm` | `GeneralKaos666/termux-display-manager-repo` | latest release/tag (TBD — see risks) | `build.sh` `TERMUX_PKG_VERSION`; re-vendor `tdm`/`tdmpasswd` |
| `termux-settings` | `GeneralKaos666/termux-settings` | latest tag | `build.sh` `TERMUX_PKG_VERSION`, `TERMUX_PKG_SRCURL`, recomputed `TERMUX_PKG_SHA256` |

Details that need care:

- **flutter**: the shim version is `3.47.8-6` while the release tag is `3.47.8`.
  The sync must read the latest release's tag *and* its `.deb` asset name to
  derive the exact `X.Y.Z-N` deb version, then bake the tag into `RELEASE_BASE`
  and the version into `VERSION`/`DEB`. It must not hardcode either.
- **opencode2**: release tag (`v2.1.4-android-r2`) differs from the package
  version (`2.1.4-1`); the sync must map the release to the new version,
  source tarball URL, and binary zip URL.
- **termux-dm**: upstream ships prebuilt `.deb`s. The sync re-vendors the
  `tdm`/`tdmpasswd` scripts from the new release and rebuilds, keeping the
  existing recipe layout.
- **termux-settings**: `TERMUX_PKG_SHA256` is a real checksum and must be
  recomputed from the new source tarball during the bump (never `SKIP_CHECKSUM`
  silently).

## 8. Error handling

- A package build fails → its job fails; the publish job does not run for it;
  the last-good `docs/` stays served.
- No newer version → no recipe change, no commit (idempotent).
- GPG secret missing or signing fails → fail before publishing; never publish
  an unsigned/insecure repo.
- GitHub API rate limit → use `GITHUB_TOKEN` (1000 req/h) rather than
  unauthenticated calls; retry once on 403/429.

## 9. Security

- The GPG private key lives only as an encrypted Actions secret; it is imported
  into an ephemeral keyring and used only to sign `InRelease` within the
  runner. The signing step must supply the passphrase to `gpg` (the current
  `--pinentry-mode loopback` invocation relies on gpg-agent caching, which does
  not exist on a fresh runner — the workflow must pass the passphrase
  explicitly).
- `GITHUB_TOKEN` is scoped to this repo; its pushes cannot trigger other
  workflows (no loop), and it is never exposed outside the run.
- The upstream repos are all public read-only sources.

## 10. Testing / verification

1. Manual `workflow_dispatch` run to prove the happy path end-to-end.
2. Verify on device: `apt update && apt install <pkg>` after the first
   auto-publish, and confirm `InRelease` is signed (no `[trusted=yes]`).
3. Idempotency: run again with no upstream change and confirm zero commits.
4. Negative: force a version bump for one package and confirm only that
   package's job rebuilds while the others are skipped.

## 11. Risks / open questions

- **Build harness version drift**: recipes are written against a specific
  termux-packages `build-package.sh` / `termux_step_*` API. The workflow must
  pin the harness (e.g. a known-good `termux/termux-packages` ref) to avoid
  breakage when upstream changes.
- **flutter `-N` suffix**: the deb-version suffix (`-6`) is not derivable from
  the tag alone; it comes from the release asset name. Confirm the asset naming
  is stable.
- **termux-dm re-vendoring**: the recipe's `TERMUX_PKG_SRCURL` points at
  `master` (not a tag), while its version is `6-morano`. Confirm how "latest"
  is detected for this repo (release, tag, or branch) and that a new release's
  `.deb` exposes `tdm`/`tdmpasswd` at the same paths as the current vendored
  copies.
