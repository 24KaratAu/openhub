import os
import sys
import io
import json
import shutil
import tarfile
import asyncio
import tempfile
import unittest
from unittest import mock

# Sandbox HOME and cwd before importing app modules, which resolve ~ and ./ at import/call time
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SANDBOX = tempfile.mkdtemp(prefix="openhub-test-")
os.environ["HOME"] = SANDBOX
os.chdir(SANDBOX)
sys.path.insert(0, PROJECT_ROOT)

import httpx
from app import cache
from app import local_skills
from app.client import GitHubProvider

SKILLS_DIR = os.path.join(SANDBOX, ".claude", "skills")


def skill_md(name, version, repo="https://github.com/acme/demo-skill"):
    lines = ["---", f"name: {name}", f'version: "{version}"', f'description: "Demo skill {version}"']
    if repo:
        lines.append(f"repository: {repo}")
    lines += ["metadata:", "  nested: value", "---", "", f"# {name} {version}", ""]
    return "\n".join(lines)


def write_skill(base, folder, name, version, repo="https://github.com/acme/demo-skill", extra=None):
    path = os.path.join(base, folder)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "SKILL.md"), "w") as f:
        f.write(skill_md(name, version, repo))
    for rel, content in (extra or {}).items():
        os.makedirs(os.path.dirname(os.path.join(path, rel)), exist_ok=True)
        with open(os.path.join(path, rel), "w") as f:
            f.write(content)
    return path


def make_tarball(files: dict) -> bytes:
    """Builds a GitHub-style tarball (single top-level folder) from {relative_path: content}."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for rel, content in files.items():
            data = content.encode()
            info = tarfile.TarInfo(f"acme-demo-skill-abc123/{rel}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def patch_httpx(handler):
    """Routes every httpx.AsyncClient created inside the block through handler."""
    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real(*args, **kwargs)
    return mock.patch("httpx.AsyncClient", factory)


def run(coro):
    return asyncio.run(coro)


async def collect(gen):
    return [line async for line in gen]


class LocalSkillsTestBase(unittest.TestCase):
    def setUp(self):
        for d in (os.path.join(SANDBOX, ".claude"), os.path.join(SANDBOX, ".cache")):
            shutil.rmtree(d, ignore_errors=True)
        os.makedirs(SKILLS_DIR)
        cache.init_db()


class TestParsing(LocalSkillsTestBase):
    def test_frontmatter_and_repo_slug(self):
        path = write_skill(SKILLS_DIR, "demo", "demo", "3.24.0")
        meta = local_skills.parse_frontmatter(os.path.join(path, "SKILL.md"))
        self.assertEqual(meta["version"], "3.24.0")
        self.assertEqual(meta["name"], "demo")
        self.assertNotIn("nested", meta)
        self.assertEqual(local_skills.extract_repo_slug(meta), "acme/demo-skill")
        self.assertEqual(local_skills.extract_repo_slug({"homepage": "git@github.com:a/b.git"}), "a/b")
        self.assertIsNone(local_skills.extract_repo_slug({"homepage": "https://example.com"}))

    def test_version_compare(self):
        self.assertTrue(local_skills.is_newer("v3.25.0", "3.24.0"))
        self.assertTrue(local_skills.is_newer("3.10", "3.9.9"))
        self.assertFalse(local_skills.is_newer("3.24.0", "3.24"))
        self.assertFalse(local_skills.is_newer("v3.24.0", "3.25.0"))
        self.assertIsNone(local_skills.is_newer("nightly", "3.24.0"))
        self.assertIsNone(local_skills.is_newer("3.25.0", None))


class TestDiskScan(LocalSkillsTestBase):
    def test_scan_skips_non_skills_and_backups(self):
        write_skill(SKILLS_DIR, "demo", "demo", "3.24.0")
        write_skill(SKILLS_DIR, "demo.bak-v3.18.4-20260911084512", "demo", "3.18.4")
        write_skill(os.path.join(SKILLS_DIR, "synced", "uuid"), "docx", "docx", "1.0")
        write_skill(os.path.join(SKILLS_DIR, "nested-repo", "skills"), "inner", "inner", "0.2.0", repo=None)
        skills = local_skills.scan_local_skills()
        self.assertEqual(sorted(skills), ["demo", "nested-repo"])
        self.assertEqual(skills["demo"]["repo_slug"], "acme/demo-skill")
        self.assertEqual(skills["nested-repo"]["version"], "0.2.0")
        self.assertIsNone(skills["nested-repo"]["repo_slug"])
        self.assertEqual(skills["nested-repo"]["paths"], [os.path.join(SKILLS_DIR, "nested-repo", "skills", "inner")])

    def test_multiple_copies_report_oldest_version(self):
        write_skill(SKILLS_DIR, "demo", "demo", "3.24.0")
        write_skill(os.path.join(SANDBOX, ".agents", "skills"), "demo", "demo", "3.18.4")
        skills = local_skills.scan_local_skills()
        self.assertEqual(skills["demo"]["version"], "3.18.4")
        self.assertEqual(len(skills["demo"]["paths"]), 2)
        shutil.rmtree(os.path.join(SANDBOX, ".agents"))

    def test_sync_records_version_and_keeps_install_date(self):
        write_skill(SKILLS_DIR, "demo", "demo", "3.24.0")
        # Rows left behind by the old scanner, which also registered non-skill folders
        cache.add_installed_package("synced", "1.0.0", "INSTALLED", "Skills")
        cache.add_installed_package("demo.bak-v3.18.4-20260911084512", "1.0.0", "INSTALLED", "Skills")

        first = {p["package_slug"]: p for p in cache.get_installed_packages()}
        self.assertEqual(list(first), ["demo"])
        self.assertEqual(first["demo"]["version"], "3.24.0")
        self.assertEqual(first["demo"]["repo_slug"], "acme/demo-skill")
        self.assertEqual(first["demo"]["local_paths"], [os.path.join(SKILLS_DIR, "demo")])

        # Rescanning after the files change on disk must not reset the install date
        os.utime(os.path.join(SKILLS_DIR, "demo", "SKILL.md"), (4102444800, 4102444800))
        cache.get_installed_packages()
        self.assertEqual(cache.get_installed_package("demo")["installed_at"], first["demo"]["installed_at"])

        shutil.rmtree(os.path.join(SKILLS_DIR, "demo"))
        self.assertEqual(cache.get_installed_packages(), [])

    def test_lookup_by_repo(self):
        write_skill(SKILLS_DIR, "demo", "demo", "3.24.0")
        cache.get_installed_packages()
        self.assertEqual(cache.get_installed_by_repo("ACME/demo-skill")["package_slug"], "demo")
        self.assertIsNone(cache.get_installed_by_repo("acme/other"))


class TestLatestVersion(unittest.TestCase):
    def provider(self, handler):
        p = GitHubProvider()
        p.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        return p

    def test_release_tag(self):
        p = self.provider(lambda r: httpx.Response(200, json={"tag_name": "v3.25.0"}))
        self.assertEqual(run(p.fetch_latest_version("acme/demo-skill", "demo")),
                         {"version": "3.25.0", "ref": "v3.25.0", "error": None})

    def test_no_release_reads_skill_md(self):
        def handler(req):
            if req.url.path.endswith("/releases/latest"):
                return httpx.Response(404)
            if "/git/trees/" in req.url.path:
                return httpx.Response(200, json={"tree": [{"path": "other/SKILL.md"}, {"path": "skills/demo/SKILL.md"}]})
            if req.url.path.endswith("skills/demo/SKILL.md"):
                return httpx.Response(200, text=skill_md("demo", "4.0.1"))
            return httpx.Response(500)
        p = self.provider(handler)
        self.assertEqual(run(p.fetch_latest_version("acme/demo-skill", "demo")),
                         {"version": "4.0.1", "ref": None, "error": None})

    def test_rate_limit(self):
        p = self.provider(lambda r: httpx.Response(403))
        self.assertIn("rate limit", run(p.fetch_latest_version("acme/demo-skill", "demo"))["error"])


class TestUpdateSkill(LocalSkillsTestBase):
    TARBALL_FILES = {
        "README.md": "repo readme",
        "tests/SKILL.md": skill_md("demo", "0.0.0-test"),
        ".agents/skills/demo/SKILL.md": skill_md("demo", "0.0.0-hidden"),
        "skills/demo/SKILL.md": skill_md("demo", "3.25.0"),
        "skills/demo/scripts/run.py": "print('new')",
    }

    def setUp(self):
        super().setUp()
        self.path = write_skill(SKILLS_DIR, "demo", "demo", "3.24.0", extra={"scripts/old.py": "print('old')"})
        cache.get_installed_packages()
        self.requested = []

    def handler(self, status=200, files=None):
        body = make_tarball(files or self.TARBALL_FILES)

        def handle(req):
            self.requested.append(str(req.url))
            return httpx.Response(status, content=body if status == 200 else b"")
        return handle

    def update(self, handler):
        with patch_httpx(handler):
            return run(collect(local_skills.update_skill("demo", [self.path], "acme/demo-skill", "v3.25.0", "3.24.0")))

    def installed_version(self):
        return local_skills.parse_frontmatter(os.path.join(self.path, "SKILL.md"))["version"]

    def test_successful_update(self):
        lines = self.update(self.handler())
        self.assertEqual(self.requested, ["https://api.github.com/repos/acme/demo-skill/tarball/v3.25.0"])
        self.assertTrue(lines[-3].startswith("[SUCCESS] Updated demo: 3.24.0 -> 3.25.0"), lines)
        self.assertEqual(self.installed_version(), "3.25.0")
        self.assertTrue(os.path.exists(os.path.join(self.path, "scripts", "run.py")))
        self.assertFalse(os.path.exists(os.path.join(self.path, "scripts", "old.py")))
        self.assertFalse(os.path.exists(os.path.join(self.path, "README.md")))

        backups = os.listdir(local_skills.BACKUP_DIR)
        self.assertEqual(len(backups), 1)
        self.assertTrue(backups[0].startswith("demo-"))
        self.assertEqual(os.listdir(os.path.join(local_skills.BACKUP_DIR, backups[0])), ["0-v3.24.0"])
        # Backups live outside skill folders so agents don't load them as duplicate skills
        self.assertEqual([p["package_slug"] for p in cache.get_installed_packages()], ["demo"])
        self.assertEqual(cache.get_installed_package("demo")["version"], "3.25.0")
        self.assertEqual(cache.get_history_logs()[0]["action"], "updated")

    def test_download_failure_changes_nothing(self):
        lines = self.update(self.handler(status=404))
        self.assertTrue(lines[-1].startswith("[FAIL] Download failed: GitHub returned HTTP 404"), lines)
        self.assertEqual(self.installed_version(), "3.24.0")
        self.assertFalse(os.path.exists(local_skills.BACKUP_DIR))

    def test_missing_skill_changes_nothing(self):
        lines = self.update(self.handler(files={"skills/other/SKILL.md": skill_md("other", "1.0"),
                                                "skills/another/SKILL.md": skill_md("another", "1.0")}))
        self.assertIn("Could not find a SKILL.md for 'demo'", lines[-1])
        self.assertEqual(self.installed_version(), "3.24.0")

    def test_failed_copy_rolls_back(self):
        with mock.patch("app.local_skills.shutil.copytree", side_effect=OSError("disk full")):
            lines = self.update(self.handler())
        self.assertIn("[FAIL] Update failed: disk full. Restored the previous version.", lines[-1])
        self.assertEqual(self.installed_version(), "3.24.0")
        self.assertTrue(os.path.exists(os.path.join(self.path, "scripts", "old.py")))
        self.assertEqual(cache.get_history_logs()[0]["action"], "failed")

    def test_rejects_path_traversal(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            info = tarfile.TarInfo("../../evil.txt")
            info.size = 1
            tar.addfile(info, io.BytesIO(b"x"))
        with patch_httpx(lambda r: httpx.Response(200, content=buf.getvalue())):
            lines = run(collect(local_skills.update_skill("demo", [self.path], "acme/demo-skill", None, "3.24.0")))
        self.assertIn("Unsafe path", lines[-1])
        self.assertEqual(self.installed_version(), "3.24.0")


class TestUpdateStatus(unittest.TestCase):
    def test_labels(self):
        base = {"version": "3.24.0", "repo_slug": "a/b", "checked_at": "2026-09-27 00:00:00"}
        self.assertIn("update available: v3.24.0 -> v3.25.0",
                      local_skills.update_status({**base, "latest_version": "3.25.0"})[0])
        self.assertIn("up to date", local_skills.update_status({**base, "latest_version": "3.24.0"})[0])
        self.assertIn("no source repo", local_skills.update_status({**base, "repo_slug": None})[0])
        self.assertIn("couldn't determine", local_skills.update_status({**base, "latest_version": None})[0])


class TestInstaller(LocalSkillsTestBase):
    def test_no_simulated_success(self):
        from app.installer import AsyncInstallRunner
        with mock.patch("shutil.which", return_value=None):
            lines = run(collect(AsyncInstallRunner.run_install("acme/demo-skill")))
        self.assertTrue(any(l.startswith("[FAIL]") for l in lines), lines)
        self.assertFalse(any("SUCCESS" in l for l in lines), lines)
        self.assertIsNone(cache.get_installed_package("acme/demo-skill"))


if __name__ == "__main__":
    try:
        unittest.main()
    finally:
        shutil.rmtree(SANDBOX, ignore_errors=True)
