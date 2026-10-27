#!/usr/bin/env python3
"""Detect and apply upstream package updates for the termux-apt-repo."""

import datetime
import functools
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

API = "https://api.github.com"


class HTTPError(Exception):
    def __init__(self, status):
        self.status = status
        super().__init__("HTTP %d" % status)


class FetchError(Exception):
    pass


def load_config(path="sync.json"):
    with open(path) as f:
        return json.load(f)


def _open_json(url, opener):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "termux-apt-repo-sync",
        },
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    resp = opener(req)
    try:
        return json.loads(resp.read().decode())
    finally:
        resp.close()


def fetch_json(url, opener=None):
    if opener is None:
        opener = urllib.request.urlopen
    last = None
    for attempt in (1, 2):
        try:
            return _open_json(url, opener)
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (403, 429) and attempt == 1:
                e.close()
                continue
            e.close()
            raise HTTPError(e.code)
        except urllib.error.URLError as e:
            raise FetchError(str(e))
    raise HTTPError(last.code if last is not None else 0)


def _find_asset(assets, pattern):
    for a in assets:
        m = re.search(pattern, a["name"])
        if m:
            return m
    return None


def fetch_latest(cfg, fetch=fetch_json):
    upstream = cfg["upstream"]
    name = cfg["name"]
    detect = cfg["detect"]

    if detect == "latest_release":
        try:
            rel = fetch("%s/repos/%s/releases/latest" % (API, upstream))
        except HTTPError as e:
            if e.status == 404:
                return None
            raise
        tag = rel.get("tag_name", "")
        assets = rel.get("assets", []) or []
        if name == "flutter":
            m = _find_asset(assets, r"flutter_([0-9][0-9A-Za-z.+-]*)_aarch64\.deb$")
            if not m:
                return None
            return {
                "new": m.group(1),
                "release_base": "https://github.com/%s/releases/download/%s" % (upstream, tag),
            }
        if name == "opencode2":
            m = re.match(r"v(\d+\.\d+\.\d+)-android-r(\d+)$", tag)
            if m:
                return {"new": "%s-%s" % (m.group(1), m.group(2)), "tag": tag}
            a = _find_asset(assets, r"opencode2_([0-9][0-9A-Za-z.+-]*)_aarch64\.deb$")
            if not a:
                raise ValueError(
                    "opencode2: unrecognized tag %r and no opencode2_*_aarch64.deb asset" % tag)
            return {"new": a.group(1), "tag": tag}
        raise ValueError("unknown latest_release package %r" % name)

    if detect == "latest_tag":
        tags = fetch("%s/repos/%s/tags?per_page=1" % (API, upstream))
        if not tags:
            return None
        tag = tags[0]["name"]
        if name == "termux-settings":
            return {"new": tag.lstrip("v"), "tag": tag}
        return {"new": tag, "tag": tag}

    if detect == "master_head":
        commit = fetch("%s/repos/%s/commits/master" % (API, upstream))
        contents = fetch("%s/repos/%s/contents/" % (API, upstream))
        deb_name = _newest_deb(contents)
        if deb_name is None:
            return None
        codename = _parse_codename(deb_name) or "master"
        epoch = _epoch_from(commit["commit"]["committer"]["date"])
        return {"new": "%s+%s" % (codename, epoch), "deb_name": deb_name}

    raise ValueError("unknown detect %r" % detect)


def _newest_deb(contents):
    debs = [c["name"] for c in contents if c["name"].lower().endswith(".deb")]
    best = None
    best_ver = -1
    for deb in debs:
        m = re.search(r"-v(\d+)-LTS-Codenamed-", deb)
        if m and int(m.group(1)) > best_ver:
            best_ver = int(m.group(1))
            best = deb
    if best is not None:
        return best
    return sorted(debs, reverse=True)[0] if debs else None


def _parse_codename(deb_name):
    m = re.search(r"-v(\d+)-LTS-Codenamed-([A-Za-z]+)\.deb$", deb_name)
    if m:
        return "%s-%s" % (m.group(1), m.group(2).lower())
    return None


def _epoch_from(date_str):
    dt = datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    return int(dt.timestamp())


def recipe_version(name):
    path = os.path.join("packages", name, "build.sh")
    with open(path) as f:
        for line in f:
            m = re.match(r'TERMUX_PKG_VERSION="([^"]+)"', line)
            if m:
                return m.group(1)
    raise ValueError("no TERMUX_PKG_VERSION in %s" % path)


def published_version(name):
    pkg_path = os.path.join("docs", "dists", "stable", "main",
                            "binary-aarch64", "Packages")
    if os.path.exists(pkg_path):
        with open(pkg_path) as f:
            content = f.read()
        for block in content.split("\n\n"):
            pkg = re.search(r"^Package:\s*(.+)$", block, re.M)
            if pkg and pkg.group(1).strip() == name:
                ver = re.search(r"^Version:\s*(.+)$", block, re.M)
                if ver:
                    return ver.group(1).strip()
    return recipe_version(name)


def _version_lt(a, b):
    try:
        r = subprocess.run(
            ["dpkg", "--compare-versions", a, "lt", b],
            capture_output=True)
        return r.returncode == 0
    except FileNotFoundError:
        return _numeric_split_lt(a, b)


def _numeric_split_lt(a, b):
    def key(v):
        parts = re.split(r"[^0-9]+", v)
        return [int(x) if x.isdigit() else 0 for x in parts]
    return key(a) < key(b)


def needs_update(name, latest):
    if latest is None:
        return False
    return _version_lt(published_version(name), latest["new"])


def _dpkg_version_cmp(a, b):
    if subprocess.run(["dpkg", "--compare-versions", a, "lt", b],
                      capture_output=True).returncode == 0:
        return -1
    if subprocess.run(["dpkg", "--compare-versions", b, "lt", a],
                      capture_output=True).returncode == 0:
        return 1
    return 0


def _dedupe_latest(debs_dir):
    by_name = {}
    for deb in glob.glob(os.path.join(debs_dir, "*.deb")):
        base = os.path.basename(deb)
        m = re.match(r"(.+?)_([^_]+)_([^_]+)\.deb$", base)
        if not m:
            continue
        name, version = m.group(1), m.group(2)
        by_name.setdefault(name, []).append((version, deb))
    for entries in by_name.values():
        entries.sort(key=functools.cmp_to_key(
            lambda a, b: _dpkg_version_cmp(a[0], b[0])))
        for _version, deb in entries[:-1]:
            os.unlink(deb)


def stage_debs(root="."):
    """Merge existing pool .debs (unchanged packages) into debs/ (which already
    holds the freshly-built .debs), deduped to the newest version per package."""
    debs_dir = os.path.join(root, "debs")
    os.makedirs(debs_dir, exist_ok=True)

    pool = os.path.join(root, "docs", "pool")
    for deb in glob.glob(os.path.join(pool, "**", "*.deb"), recursive=True):
        shutil.copy2(deb, debs_dir)

    _dedupe_latest(debs_dir)


def _set_in_file(path, key, value):
    with open(path) as f:
        content = f.read()

    def repl(m):
        old = m.group(2)
        if old.startswith('"'):
            return m.group(1) + '"' + value + '"'
        return m.group(1) + value

    new, n = re.subn(
        r'(^%s=)("[^"]*"|[^\s"]*)' % re.escape(key),
        repl,
        content, count=1, flags=re.M)
    if n == 0:
        raise ValueError("field %r not found in %s" % (key, path))
    with open(path, "w") as f:
        f.write(new)


def _replace_termux_download(build, new_url):
    with open(build) as f:
        content = f.read()
    new, n = re.subn(
        r'termux_download\s+"[^"]*"\s+opencode2\.zip',
        'termux_download "%s" opencode2.zip' % new_url,
        content, count=1)
    if n == 0:
        raise ValueError("termux_download opencode2.zip not found in %s" % build)
    with open(build, "w") as f:
        f.write(new)


def _download_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": "termux-apt-repo-sync"})
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def _sha256_of_url(url, download=None):
    if download is None:
        download = _download_bytes
    return hashlib.sha256(download(url)).hexdigest()


def _find_file(root, name):
    matches = []
    for dirpath, _dirs, files in os.walk(root):
        if name in files:
            matches.append(os.path.join(dirpath, name))
    if not matches:
        return None
    for m in matches:
        if os.path.basename(os.path.dirname(m)) == "bin":
            return m
    return matches[0]


def _revendor_tdm(pkg_dir, deb_path):
    tmp = tempfile.mkdtemp()
    try:
        subprocess.run(["dpkg-deb", "-x", deb_path, tmp],
                       check=True, capture_output=True)
        for f in ("tdm", "tdmpasswd"):
            src = _find_file(tmp, f)
            if src is None:
                raise ValueError("deb missing %s" % f)
            shutil.copy2(src, os.path.join(pkg_dir, f))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def bump(name, latest, root=".", download=None):
    pkg_dir = os.path.join(root, "packages", name)

    if name == "flutter":
        _set_in_file(os.path.join(pkg_dir, "build.sh"),
                     "TERMUX_PKG_VERSION", latest["new"])
        for f in ("postinst", "preinst", "postrm"):
            _set_in_file(os.path.join(pkg_dir, f), "VERSION", latest["new"])
        _set_in_file(os.path.join(pkg_dir, "postinst"),
                     "RELEASE_BASE", latest["release_base"])

    elif name == "opencode2":
        build = os.path.join(pkg_dir, "build.sh")
        _set_in_file(build, "TERMUX_PKG_VERSION", latest["new"])
        _set_in_file(build, "TERMUX_PKG_SRCURL",
                     "https://github.com/GeneralKaos666/opencode-android/"
                     "archive/refs/tags/%s.tar.gz" % latest["tag"])
        m = re.match(r"v(\d+\.\d+\.\d+)-android-r\d+", latest["tag"])
        if not m:
            raise ValueError("opencode2: unrecognized tag %r" % latest["tag"])
        zip_url = ("https://github.com/GeneralKaos666/opencode-android/"
                   "releases/download/%s/opencode2-%s-android-aarch64.zip"
                   % (latest["tag"], m.group(1)))
        _replace_termux_download(build, zip_url)

    elif name == "termux-dm":
        build = os.path.join(pkg_dir, "build.sh")
        _set_in_file(build, "TERMUX_PKG_VERSION", latest["new"])
        if download is None:
            download = _download_bytes
        deb_bytes = download(
            "https://raw.githubusercontent.com/GeneralKaos666/"
            "termux-display-manager-repo/master/%s" % latest["deb_name"])
        with tempfile.NamedTemporaryFile(suffix=".deb", delete=False) as f:
            f.write(deb_bytes)
            deb_path = f.name
        try:
            _revendor_tdm(pkg_dir, deb_path)
        finally:
            os.unlink(deb_path)

    elif name == "termux-settings":
        build = os.path.join(pkg_dir, "build.sh")
        src_url = ("https://github.com/GeneralKaos666/termux-settings/"
                   "archive/refs/tags/%s.tar.gz" % latest["tag"])
        sha = latest.get("sha256") or _sha256_of_url(src_url, download)
        _set_in_file(build, "TERMUX_PKG_VERSION", latest["new"])
        _set_in_file(build, "TERMUX_PKG_SRCURL", src_url)
        _set_in_file(build, "TERMUX_PKG_SHA256", sha)

    else:
        raise ValueError("unknown package %r" % name)


def _config_for(name):
    cfg = load_config()
    for pkg in cfg["packages"]:
        if pkg["name"] == name:
            return pkg
    raise ValueError("unknown package %r" % name)


def detect(name):
    cfg = _config_for(name)
    latest = fetch_latest(cfg)
    current = published_version(name)
    changed = needs_update(name, latest)
    return {
        "name": name,
        "current": current,
        "new": latest["new"] if latest else None,
        "changed": changed,
    }


def detect_all():
    cfg = load_config()
    out = []
    for pkg in cfg["packages"]:
        name = pkg["name"]
        try:
            latest = fetch_latest(pkg)
            out.append({
                "name": name,
                "current": published_version(name),
                "new": latest["new"] if latest else None,
                "changed": needs_update(name, latest),
            })
        except Exception as e:
            out.append({
                "name": name,
                "current": None,
                "new": None,
                "changed": False,
                "error": str(e),
            })
    return out


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(prog="sync")
    sub = parser.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("detect")
    d.add_argument("name")

    sub.add_parser("detect-all")

    b = sub.add_parser("bump")
    b.add_argument("name")
    b.add_argument("--force", action="store_true")

    sd = sub.add_parser("stage-debs")

    args = parser.parse_args(argv)

    if args.cmd == "detect":
        print(json.dumps(detect(args.name)))
        return 0

    if args.cmd == "detect-all":
        print(json.dumps(detect_all()))
        return 0

    if args.cmd == "bump":
        cfg = _config_for(args.name)
        latest = fetch_latest(cfg)
        if not args.force and not needs_update(args.name, latest):
            return 2
        bump(args.name, latest)
        return 0

    if args.cmd == "stage-debs":
        stage_debs()
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
