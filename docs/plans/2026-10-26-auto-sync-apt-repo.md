# Auto-Sync APT Repository Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically detect new upstream releases/tags for the four hosted packages, bump their recipes, rebuild the `.deb`s with the termux-packages harness, re-sign, and publish to GitHub Pages — no manual steps.

**Architecture:** A Python driver (`scripts/sync.py`) detects the latest upstream version per package, compares it to the published version, and applies per-package recipe edits. A GitHub Actions workflow runs a `detect` job, a `build` matrix (one job per changed package) that rebuilds each `.deb`, and a `publish` job that regenerates + signs + commits `docs/`. A thin `scripts/build-package.sh` wraps the termux-packages Docker build so the workflow stays small.

**Tech Stack:** Python 3 (stdlib only: `argparse`, `json`, `re`, `urllib`, `subprocess`, `unittest`), GitHub Actions, bash, termux-packages build harness (`ghcr.io/termux/package-builder`, `build-package.sh`), GPG.

**Spec:** `docs/specs/2026-10-26-auto-sync-apt-repo-design.md`

## Global Constraints

- Architectures: `aarch64` only.
- Never publish unsigned: sign `InRelease` before any commit; fail the run if GPG is unavailable.
- Never `SKIP_CHECKSUM` silently for `termux-settings`; recompute a real `TERMUX_PKG_SHA256`.
- Leave `opencode2`'s `TERMUX_PKG_DESCRIPTION` unchanged.
- Idempotent: no upstream change → no recipe change, no commit.
- Packages are independent: a failing package job must not block the others (`fail-fast: false`).
- Recipes are termux-packages format; pin the build harness to a known-good `termux/termux-packages` ref.
- `flutter` is a shim: rebuild the stub only; never build the SDK here.

## Review Focus

1. **Upstream returns no release/tag/assets** (empty list or 404) → treat as "no change", never crash or emit a bogus version. (Task 1)
2. **GitHub API rate limit / 403/429** → retry once; on failure, fail safe (skip, do not mark changed). (Task 1)
3. **Upstream tag format doesn't match the expected regex** (e.g. `opencode2` tag not `v<ver>-android-r<rev>`) → fail loudly with a clear message, never silently skip or write a wrong version. (Task 1)
4. **`dpkg --compare-versions` unavailable** on the runtime → fall back to a numeric-safe string compare, or fail clearly; never report a wrong ordering. (Task 1)
5. **One package build fails while others succeed** → publish job must still publish the successful packages' `docs/`, never a half-written tree; a failed package leaves its last-good version served. (Task 4 / Task 5)

---

### Task 1: Config + version detection

**Files:**
- Create: `sync.json`
- Create: `scripts/sync.py`
- Create: `scripts/test_sync.py`

**Interfaces:**
- Produces (consumed by Tasks 2–3):
  - `load_config(path="sync.json") -> dict`
  - `read_state(path="sync-state.json") -> dict`
  - `fetch_json(url: str) -> dict` — GET with `Authorization: Bearer $GITHUB_TOKEN` when set, `User-Agent: termux-apt-repo-sync`, raises on non-200 after one retry on 403/429.
  - `fetch_latest(cfg: dict, fetch: Callable = fetch_json) -> dict` — returns the package's `info` dict (keys below).
  - `recipe_version(name: str) -> str` — parse `TERMUX_PKG_VERSION` from `packages/<name>/build.sh`.
  - `published_version(name: str) -> str` — parse `Version:` from the `Package: <name>` block in `docs/dists/stable/main/binary-aarch64/Packages`; fall back to `recipe_version(name)`.
  - `needs_update(name: str, latest: dict, state: dict) -> bool`

`sync.json` (exact shape):

```json
{
  "packages": [
    { "name": "flutter",        "upstream": "GeneralKaos666/flutter-for-termux",           "detect": "latest_release" },
    { "name": "opencode2",      "upstream": "GeneralKaos666/opencode-android",             "detect": "latest_release" },
    { "name": "termux-dm",      "upstream": "GeneralKaos666/termux-display-manager-repo",  "detect": "master_head" },
    { "name": "termux-settings","upstream": "GeneralKaos666/termux-settings",              "detect": "latest_tag" }
  ]
}
```

`fetch_latest` `info` keys, by package (the decisions the rest of the plan relies on):

- `flutter`: `{"new": "3.47.8-6", "release_base": "https://github.com/GeneralKaos666/flutter-for-termux/releases/download/3.47.8"}` — `new` is the `flutter_*_aarch64.deb` asset name with the `flutter_` prefix and `_aarch64.deb` suffix stripped; `release_base` is `.../releases/download/<tag_name>`.
- `opencode2`: `{"new": "2.1.4-2", "tag": "v2.1.4-android-r2"}` — `new` is `<ver>-<rev>` parsed from `tag_name` = `v<ver>-android-r<rev>`; fall back to the `opencode2_*_aarch64.deb` asset version when the tag does not match.
- `termux-dm`: `{"new": "6-morano", "sha": "<master HEAD sha>"}` — `new` is parsed from the newest `.deb` filename at the repo root (codenamed scheme `TermuxDM-v6-LTS-Codenamed-Morano.deb` → `6-morano`).
- `termux-settings`: `{"new": "1.1.1", "tag": "v1.1.1"}` — `new` is the latest tag with a leading `v` stripped.

`needs_update` rule: true when `published_version(name)` is older than `info["new"]` using `dpkg --compare-versions <current> lt <new>`; for `termux-dm` (codenamed, non-numeric) true when `info["sha"] != state.get(name, {}).get("last_sha")`.

- [ ] **Step 1: Write failing tests** in `scripts/test_sync.py`

```python
import os, sys, unittest
sys.path.insert(0, os.path.dirname(__file__))
import sync

class TestFetchLatest(unittest.TestCase):
    def fake(self, url):
        # return canned JSON keyed by URL substring
        raise NotImplementedError

    def test_flutter_new_from_asset_name(self):
        info = sync.fetch_latest({"name":"flutter","detect":"latest_release","upstream":"x/y"}, self.fake)
        self.assertEqual(info["new"], "3.47.8-6")
        self.assertEqual(info["release_base"], ".../releases/download/3.47.8")

    def test_opencode2_new_from_tag(self):
        info = sync.fetch_latest({"name":"opencode2","detect":"latest_release","upstream":"x/y"}, self.fake)
        self.assertEqual(info["new"], "2.1.4-2")

    def test_settings_new_strips_v(self):
        info = sync.fetch_latest({"name":"termux-settings","detect":"latest_tag","upstream":"x/y"}, self.fake)
        self.assertEqual(info["new"], "1.1.1")

class TestPublishedVersion(unittest.TestCase):
    def test_reads_from_packages_file(self): ...
    def test_falls_back_to_recipe(self): ...

class TestNeedsUpdate(unittest.TestCase):
    def test_newer_release(self): ...
    def test_unchanged(self): ...
    def test_tdm_by_sha(self): ...
    def test_empty_release_no_change(self): ...
    def test_429_raises_after_retry(self): ...
    def test_bad_tag_format_raises(self): ...        # opencode2 tag not v<ver>-android-r<rev> -> fail loudly
    def test_no_dpkg_falls_back_to_numeric_compare(self): ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 scripts/test_sync.py -v`
Expected: FAIL — `No module named 'sync'` (or the test helpers are stubs).

- [ ] **Step 3: Implement the detection functions in `scripts/sync.py`**

Signatures above. `fetch_latest` dispatches on `cfg["detect"]`: `latest_release` → `GET /repos/<upstream>/releases/latest`; `latest_tag` → `GET /repos/<upstream>/tags?per_page=1`; `master_head` → `GET /repos/<upstream>/commits/master` (for `sha`) plus `GET /repos/<upstream>/contents/` (for the `.deb` filename). Handle empty/404 as "no change". Implement `_version_lt(a, b)` via `subprocess.run(["dpkg","--compare-versions", a, "lt", b])`, falling back to a numeric-aware split compare if `dpkg` is absent.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 scripts/test_sync.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sync.json scripts/sync.py scripts/test_sync.py
git commit -S -m "feat(sync): add config and version detection"
```

---

### Task 2: Per-package recipe bump

**Files:**
- Modify: `scripts/sync.py`
- Modify: `scripts/test_sync.py`
- Create: `sync-state.json` (committed state; starts `{}`)

**Interfaces:**
- Consumes: `fetch_latest`, `needs_update` (Task 1).
- Produces: `bump(name: str, latest: dict) -> None` — edits recipe files in place; `write_state(state: dict, path="sync-state.json") -> None`.

`bump` edits, by package (exact rules):

- `flutter`: set `TERMUX_PKG_VERSION="<new>"` in `packages/flutter/build.sh`; set `VERSION="<new>"` in `packages/flutter/postinst`, `preinst`, `postrm`; set `RELEASE_BASE="<release_base>"` in `postinst`.
- `opencode2`: set `TERMUX_PKG_VERSION="<new>"`, `TERMUX_PKG_SRCURL="https://github.com/GeneralKaos666/opencode-android/archive/refs/tags/<tag>.tar.gz"`, and the `termux_download` URL in `termux_step_make_install` to `https://github.com/GeneralKaos666/opencode-android/releases/download/<tag>/opencode2-<ver>-android-aarch64.zip`. Do not touch `TERMUX_PKG_DESCRIPTION`.
- `termux-dm`: set `TERMUX_PKG_VERSION="<new>"`; re-vendor `packages/termux-dm/tdm` and `packages/termux-dm/tdmpasswd` by downloading the newest `.deb` from the repo root and extracting `usr/bin/tdm` / `usr/bin/tdmpasswd` (`dpkg-deb -x`); record `state["termux-dm"]["last_sha"] = latest["sha"]` via `write_state`.
- `termux-settings`: set `TERMUX_PKG_VERSION="<new>"`, `TERMUX_PKG_SRCURL="https://github.com/GeneralKaos666/termux-settings/archive/refs/tags/<tag>.tar.gz"`, and `TERMUX_PKG_SHA256` = sha256 of that tarball (download and hash, never `SKIP_CHECKSUM`).

- [ ] **Step 1: Write failing tests** using a `tempfile.TemporaryDirectory` with fixture recipe files copied from the real `packages/<name>/`, assert the edited bytes and that unrelated lines (e.g. `opencode2` description) are untouched.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 scripts/test_sync.py -v`
Expected: FAIL — `bump` is not defined.

- [ ] **Step 3: Implement `bump(name, latest)` and `write_state` in `scripts/sync.py`**

One helper `_set_in_file(path, pattern, replacement)` for the regex field swaps; termux-dm's re-vendor uses `subprocess` + `dpkg-deb -x`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 scripts/test_sync.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/sync.py scripts/test_sync.py sync-state.json
git commit -S -m "feat(sync): add per-package recipe bump"
```

---

### Task 3: CLI driver

**Files:**
- Modify: `scripts/sync.py`
- Modify: `scripts/test_sync.py`

**Interfaces:**
- Produces: `detect(name: str) -> dict` → `{"name","current","new","changed"}`; `detect_all() -> list[dict]`; `main(argv=None) -> int`.

CLI (argparse):
- `python3 scripts/sync.py detect <name>` → prints one JSON object to stdout.
- `python3 scripts/sync.py detect-all` → prints a JSON array of `{"name","current","new","changed"}` for every package.
- `python3 scripts/sync.py bump <name>` → runs `fetch_latest` + `bump`; exits `0` on success, `2` when `needs_update` is false (no change), non-zero on error.

- [ ] **Step 1: Write failing tests** for arg parsing, JSON output shape, and exit code `2` on no-change (using a stubbed `fetch_latest`).

- [ ] **Step 2: Run tests to verify they fail** — `main` / `detect` undefined.

- [ ] **Step 3: Implement `detect`, `detect_all`, `main`** (wire `fetch_latest` + `needs_update` + `bump`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 scripts/test_sync.py -v`
Expected: PASS.

- [ ] **Step 5: Smoke test against real GitHub API**

Run: `python3 scripts/sync.py detect termux-settings`
Expected: JSON with `"changed": true, "new": "1.1.1"` (upstream `v1.1.1` is newer than published `1.1.0`).

- [ ] **Step 6: Commit**

```bash
git add scripts/sync.py scripts/test_sync.py
git commit -S -m "feat(sync): add CLI driver"
```

---

### Task 4: Build wrapper + harness integration

**Files:**
- Create: `scripts/build-package.sh`

**Interfaces:**
- Produces: `scripts/build-package.sh <pkg>` — expects `TERMUX_PACKAGES_DIR` (path to a `termux/termux-packages` checkout) and `TERMUX_PACKAGES_REF` (pinned ref); copies `packages/<pkg>/` → `$TERMUX_PACKAGES_DIR/packages/<pkg>/`, runs `$TERMUX_PACKAGES_DIR/scripts/run-docker.sh -d $TERMUX_PACKAGES_DIR/build-package.sh -a aarch64 <pkg>`, then copies `$TERMUX_PACKAGES_DIR/output/*.deb` into `debs/`.

- [ ] **Step 1: Pin the harness ref** — determine a known-good `termux/termux-packages` commit (the one the recipes were last built against) and record it as the default value of a workflow input `TERMUX_PACKAGES_REF`. Validate the recipes still lint/build against it (Step 4).

- [ ] **Step 2: Write `scripts/build-package.sh`** — the overlay + `run-docker.sh` + collect sequence above, with `set -euo pipefail`.

- [ ] **Step 3: Validate one build end-to-end** — run a `workflow_dispatch` (or a scratch job) that checks out `termux/termux-packages@<ref>`, overlays `termux-settings`, and builds it; confirm a `termux-settings_*.deb` lands in `output/` and then `debs/`.

- [ ] **Step 4: Confirm a changed-package build produces a `.deb`** and that a failed build leaves `debs/` empty (nothing to publish). Document the exact `run-docker.sh` flags actually used, in a comment at the top of `build-package.sh`.

- [ ] **Step 5: Commit**

```bash
git add scripts/build-package.sh
git commit -S -m "feat(sync): add termux-packages build wrapper"
```

---

### Task 5: GitHub Actions workflow + signing

**Files:**
- Create: `.github/workflows/sync.yml`
- Modify: `termux-apt-repo` (sign invocation)

**Interfaces:**
- Consumes: `scripts/sync.py detect-all`, `scripts/sync.py bump <pkg>`, `scripts/build-package.sh <pkg>`, `termux-apt-repo` (existing).

Workflow structure:

- `on`: `schedule` (cron `0 * * * *`), `workflow_dispatch` (input `packages`, space-separated, default all), `push` with `paths: ['packages/**', 'sync.json', 'sync-state.json', 'scripts/sync.py']`.
- `permissions: contents: write`.
- **`detect`** job (`ubuntu-latest`): checkout → `python3 scripts/sync.py detect-all` → filter to `changed: true` → expose the package-name JSON array as a job output.
- **`build`** job (matrix over the changed names, `fail-fast: false`): checkout self → `python3 scripts/sync.py bump <pkg>` → checkout `termux/termux-packages@${{ inputs.TERMUX_PACKAGES_REF }}` → `scripts/build-package.sh <pkg>` → upload `debs/*.deb` and a tarball of `packages/<pkg>/` as artifacts.
- **`publish`** job (`needs: build`, `if: always()` with success check): download artifacts → overlay the bumped recipe tarballs → import `GPG_PRIVATE_KEY` into a fresh `GNUPGHOME` → `./termux-apt-repo debs docs stable main --sign` → `gpg --export 476FC230ECBBFDF0 > docs/key.gpg` → `git add docs/ packages/ sync-state.json` → commit → push.

- [ ] **Step 1: Patch `termux-apt-repo` signing** — make the `--sign` branch read `GPG_PASSPHRASE` from the environment and add `--passphrase "$GPG_PASSPHRASE"` (loopback) so a fresh runner can sign without a cached agent; leave behavior identical when the env var is unset.

- [ ] **Step 2: Write `.github/workflows/sync.yml`** with the three-job structure above and secrets `GPG_PRIVATE_KEY`, `GPG_PASSPHRASE`.

- [ ] **Step 3: Validate the workflow** — a `workflow_dispatch` run must, for the changed packages: bump recipes, build, regenerate + sign `docs/`, and push one signed commit. Confirm `InRelease` verifies with the public key (no `[trusted=yes]`).

- [ ] **Step 4: Verify idempotency** — a second run with no upstream change produces zero commits.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/sync.yml termux-apt-repo
git commit -S -m "feat(sync): add sync workflow and CI signing"
```

---

### Task 6: Documentation + secrets runbook

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document the auto-sync** — replace the manual "Maintaining" section with: the automatic trigger (hourly schedule + push + manual), the two secrets to add (`GPG_PRIVATE_KEY`, `GPG_PASSPHRASE` — how to export the key: `gpg --armor --export-secret-keys 476FC230ECBBFDF0`), and that `GITHUB_TOKEN` is used for the push-back (no PAT needed).

- [ ] **Step 2: Note the per-package upstream mapping** and the `TERMUX_PACKAGES_REF` input (how to bump the harness pin).

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -S -m "docs: document auto-sync and required secrets"
```
