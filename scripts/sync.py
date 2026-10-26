#!/usr/bin/env python3
"""Detect and apply upstream package updates for the termux-apt-repo."""

import json
import os
import re
import subprocess
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


def read_state(path="sync-state.json"):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


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
        opener = urllib.request.build_opener()
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
        new = _tdm_version(contents)
        if new is None:
            return None
        return {"new": new, "sha": commit["sha"]}

    raise ValueError("unknown detect %r" % detect)


def _tdm_version(contents):
    debs = sorted(
        (c["name"] for c in contents
         if c["name"].lower().endswith(".deb")),
        reverse=True)
    for deb in debs:
        m = re.search(r"-v(\d+)-LTS-Codenamed-([A-Za-z]+)\.deb$", deb)
        if m:
            return "%s-%s" % (m.group(1), m.group(2).lower())
    return None


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


def needs_update(name, latest, state):
    if latest is None:
        return False
    if name == "termux-dm":
        return latest.get("sha") != state.get(name, {}).get("last_sha")
    return _version_lt(published_version(name), latest["new"])
