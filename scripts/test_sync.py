import io
import os
import sys
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, os.path.dirname(__file__))
import sync


def _release(tag, assets):
    return {"tag_name": tag, "assets": [{"name": n} for n in assets]}


def fake_fetch(url):
    if "flutter-for-termux/releases/latest" in url:
        return _release("3.47.8", [
            "build_evidence.json",
            "build_metadata.json",
            "flutter_3.47.8-6_aarch64.deb",
            "flutter_3.47.8-6_aarch64.deb.sha256",
            "flutter_3.47.8-6_aarch64.deb.size.txt",
            "inventory.txt",
        ])
    if "opencode-android/releases/latest" in url:
        return _release("v2.1.4-android-r2", [
            "opencode2-2.1.4-2-aarch64.pkg.tar.xz",
            "opencode2-2.1.4-android-aarch64.zip",
            "opencode2_2.1.4-2_aarch64.deb",
            "SHA256SUMS",
        ])
    if "termux-settings/tags" in url:
        return [{"name": "v1.1.1"}]
    if "termux-display-manager-repo/commits/master" in url:
        return {"sha": "abc123def456"}
    if "termux-display-manager-repo/contents/" in url:
        return [
            {"name": "TermuxDM-v6-LTS-Codenamed-Morano.deb"},
            {"name": "termux-dm_5.0-LTS-Support.deb"},
            {"name": "README.md"},
        ]
    raise AssertionError("unexpected URL " + url)


class TestFetchLatest(unittest.TestCase):
    def test_flutter_new_from_asset_name(self):
        info = sync.fetch_latest(
            {"name": "flutter", "detect": "latest_release",
             "upstream": "GeneralKaos666/flutter-for-termux"},
            fetch=fake_fetch)
        self.assertEqual(info["new"], "3.47.8-6")
        self.assertEqual(
            info["release_base"],
            "https://github.com/GeneralKaos666/flutter-for-termux/releases/download/3.47.8")

    def test_opencode2_new_from_tag(self):
        info = sync.fetch_latest(
            {"name": "opencode2", "detect": "latest_release",
             "upstream": "GeneralKaos666/opencode-android"},
            fetch=fake_fetch)
        self.assertEqual(info["new"], "2.1.4-2")
        self.assertEqual(info["tag"], "v2.1.4-android-r2")

    def test_settings_new_strips_v(self):
        info = sync.fetch_latest(
            {"name": "termux-settings", "detect": "latest_tag",
             "upstream": "GeneralKaos666/termux-settings"},
            fetch=fake_fetch)
        self.assertEqual(info["new"], "1.1.1")
        self.assertEqual(info["tag"], "v1.1.1")

    def test_tdm_master_head(self):
        info = sync.fetch_latest(
            {"name": "termux-dm", "detect": "master_head",
             "upstream": "GeneralKaos666/termux-display-manager-repo"},
            fetch=fake_fetch)
        self.assertEqual(info["new"], "6-morano")
        self.assertEqual(info["sha"], "abc123def456")

    def test_empty_release_no_change(self):
        info = sync.fetch_latest(
            {"name": "flutter", "detect": "latest_release", "upstream": "x/y"},
            fetch=lambda u: {"tag_name": "3.47.8", "assets": []})
        self.assertIsNone(info)

    def test_bad_tag_format_raises(self):
        def f(url):
            return {"tag_name": "weird", "assets": [{"name": "README.md"}]}
        with self.assertRaises(ValueError):
            sync.fetch_latest(
                {"name": "opencode2", "detect": "latest_release", "upstream": "x/y"},
                fetch=f)


class TestPublishedVersion(unittest.TestCase):
    def test_reads_from_packages_file(self):
        self.assertEqual(sync.published_version("flutter"), "3.47.8-6")
        self.assertEqual(sync.published_version("termux-settings"), "1.1.0")

    def test_recipe_version(self):
        self.assertEqual(sync.recipe_version("flutter"), "3.47.8-6")
        self.assertEqual(sync.recipe_version("opencode2"), "2.1.4-1")

    def test_falls_back_to_recipe(self):
        with mock.patch("sync.os.path.exists", return_value=False):
            self.assertEqual(sync.published_version("flutter"), "3.47.8-6")


class TestNeedsUpdate(unittest.TestCase):
    def test_newer_release(self):
        self.assertTrue(sync.needs_update(
            "termux-settings", {"new": "1.1.1", "tag": "v1.1.1"}, {}))

    def test_unchanged(self):
        self.assertFalse(sync.needs_update(
            "flutter", {"new": "3.47.8-6", "release_base": "x"}, {}))

    def test_tdm_by_sha(self):
        self.assertTrue(sync.needs_update(
            "termux-dm", {"new": "6-morano", "sha": "newsha"}, {}))
        self.assertFalse(sync.needs_update(
            "termux-dm", {"new": "6-morano", "sha": "newsha"},
            {"termux-dm": {"last_sha": "newsha"}}))

    def test_none_latest_no_change(self):
        self.assertFalse(sync.needs_update("flutter", None, {}))


class TestFetchJsonRetry(unittest.TestCase):
    def test_429_retries_once(self):
        calls = []

        class FakeResp:
            def __init__(self, data):
                self._d = data

            def read(self):
                return self._d

            def close(self):
                pass

        def opener(req):
            calls.append(req.full_url)
            if len(calls) == 1:
                raise urllib.error.HTTPError(req.full_url, 429, "Too Many", {}, io.BytesIO())
            return FakeResp(b'{"ok": true}')

        self.assertEqual(sync.fetch_json("http://x", opener=opener), {"ok": True})
        self.assertEqual(len(calls), 2)

    def test_429_raises_after_retry(self):
        calls = []

        def opener(req):
            calls.append(1)
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many", {}, io.BytesIO())

        with self.assertRaises(sync.HTTPError):
            sync.fetch_json("http://x", opener=opener)
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
